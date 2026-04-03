import os
import hashlib
from datetime import datetime, timezone
import langextract as lx
from dotenv import load_dotenv
from langextract import data as lx_data
from supabase import create_client, Client
from docling.document_converter import DocumentConverter
from app.core.intent import DocumentIntentAnalyzer
from app.core.mr import model_router
from app.core.matrix import TraceabilityMatrix

load_dotenv()


# ─── CLASIFICADOR DE CONTENIDO ───────────────────────────────────────────────

def clasificar_documento(texto: str, source_type: str) -> dict:
    tiene_tablas = (
        "|" in texto and "\n" in texto and
        texto.count("|") > 10
    ) or source_type in ["xlsx", "csv"]

    es_narrativo = len(texto) > 500 and texto.count(".") > 10

    return {
        "tiene_tablas": tiene_tablas,
        "es_narrativo": es_narrativo,
        "usar_llamaindex": tiene_tablas,
        "usar_langextract": es_narrativo or not tiene_tablas,
        "chars": len(texto)
    }


# ─── DII — DIGEST INPUT INTELLIGENCE ─────────────────────────────────────────

class DigestInputIntelligence:
    def __init__(self, org_id: str = None):
        self.data_path = os.getenv("DATA_DIR", "./data")
        self.org_id = org_id or os.getenv("ORG_ID", "default")

        if not os.getenv("LANGEXTRACT_API_KEY") and os.getenv("GOOGLE_API_KEY"):
            os.environ["LANGEXTRACT_API_KEY"] = os.getenv("GOOGLE_API_KEY")

        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        self.converter = DocumentConverter()
        self.intent_analyzer = DocumentIntentAnalyzer()
        self.tm = TraceabilityMatrix(org_id=self.org_id)

    # ── Utilidades ──────────────────────────────────────────────────────────

    def _calcular_hash(self, texto: str) -> str:
        return hashlib.sha256(texto.encode()).hexdigest()

    # ── Supabase: documentos ─────────────────────────────────────────────────

    def _registrar_documento(self, nombre: str, source_type: str,
                              doc_hash: str, modelo_info: dict,
                              doc_type: str) -> str:
        resultado = self.supabase.table("documents").insert({
            "org_id": self.org_id,
            "name": nombre,
            "source_type": source_type,
            "source_path": self.data_path,
            "status": "processing",
            "doc_hash": doc_hash,
            "metadata": {
                "model_router": modelo_info,
                "document_type": doc_type
            }
        }).execute()
        return resultado.data[0]["id"]

    def _actualizar_estado_documento(self, document_id: str, status: str):
        self.supabase.table("documents").update({
            "status": status,
            "processed_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", document_id).execute()

    # ── Supabase: entidades ──────────────────────────────────────────────────

    def _entidad_existe(self, hash_entidad: str) -> bool:
        resultado = self.supabase.table("entities").select("id").eq(
            "hash", hash_entidad
        ).eq("org_id", self.org_id).execute()
        return len(resultado.data) > 0

    def _guardar_entidad(self, document_id: str,
                         entidad: str, valor: str) -> str | None:
        hash_entidad = self._calcular_hash(f"{entidad}:{valor.strip()}")

        if self._entidad_existe(hash_entidad):
            print(f"  [IHS] Duplicado ignorado: {entidad} = {valor[:40]}")
            return None

        resultado = self.supabase.table("entities").insert({
            "document_id": document_id,
            "org_id": self.org_id,
            "entity_class": entidad,
            "entity_value": valor,
            "normalized_value": valor.strip(),
            "hash": hash_entidad,
            "confidence": 1.0,
            "status": "active"
        }).execute()

        return resultado.data[0]["id"]

    # ── Docling: conversión ──────────────────────────────────────────────────

    def _convertir_con_docling(self, ruta: str) -> str:
        result = self.converter.convert(ruta)
        return result.document.export_to_markdown()

    # ── LangExtract: extracción semántica ────────────────────────────────────

    def _extraer_con_langextract(self, texto: str,
                                  prompt_extra: str = "") -> list:
        prompt_description = (
            "Extrae todas las entidades relevantes ÚNICAMENTE del documento proporcionado. "
            "Pueden ser nombres de personas o empresas, montos, fechas, cláusulas, "
            "productos, cantidades, lugares o cualquier dato significativo. "
            "NO uses los ejemplos como fuente de datos. "
            "Los ejemplos solo muestran el formato de extracción esperado. "
            "Usa el texto exacto del documento sin parafrasear ni interpretar. "
            f"{prompt_extra}"
        )

        examples = [
            lx_data.ExampleData(
                text="Empresa ABC S.A. de C.V. adquiere servicios de Soluciones XYZ "
                     "por $80,000 MXN con pagos mensuales de $8,000 MXN "
                     "a partir del 1 de enero de 2025.",
                extractions=[
                    lx_data.Extraction(extraction_class="entidad_nombre",
                                       extraction_text="Empresa ABC S.A. de C.V."),
                    lx_data.Extraction(extraction_class="entidad_nombre",
                                       extraction_text="Soluciones XYZ"),
                    lx_data.Extraction(extraction_class="monto_total",
                                       extraction_text="$80,000 MXN"),
                    lx_data.Extraction(extraction_class="pago_periodico",
                                       extraction_text="$8,000 MXN"),
                    lx_data.Extraction(extraction_class="fecha",
                                       extraction_text="1 de enero de 2025"),
                ]
            )
        ]

        print("  [LangExtract] Extrayendo entidades semánticas...")
        resultado = lx.extract(
            text_or_documents=texto,
            prompt_description=prompt_description,
            examples=examples,
        )

        entidades = []
        vistos = set()
        extractions = resultado.extractions if hasattr(resultado, 'extractions') else []
        for ext in extractions:
            clave = (ext.extraction_class, ext.extraction_text)
            if clave not in vistos:
                vistos.add(clave)
                entidades.append({
                    "entidad": ext.extraction_class,
                    "valor": ext.extraction_text,
                    "fuente": "langextract"
                })
        return entidades

    # ── LlamaIndex: extracción tabular ───────────────────────────────────────

    def _extraer_con_llamaindex(self, texto: str) -> list:
        print("  [LlamaIndex] Extrayendo datos tabulares...")
        entidades = []
        headers = []
        for linea in texto.split("\n"):
            if "|" in linea and "---" not in linea:
                celdas = [c.strip() for c in linea.split("|") if c.strip()]
                if not headers:
                    headers = celdas
                else:
                    for j, celda in enumerate(celdas):
                        if j < len(headers) and celda:
                            entidades.append({
                                "entidad": f"tabla_{headers[j].lower().replace(' ', '_')}",
                                "valor": celda,
                                "fuente": "llamaindex"
                            })
        return entidades

    # ── EDB: embeddings automáticos ──────────────────────────────────────────

    def _generar_embeddings_documento(self, document_id: str):
        """Llama a EDB para generar embeddings de todas las entidades del documento."""
        try:
            from app.core.edb import EntityDataBrain
            edb = EntityDataBrain()
            count = edb.store_document_embeddings(document_id)
            print(f"  [EDB] {count} embeddings generados automáticamente")
        except Exception as e:
            print(f"  [EDB] Error generando embeddings: {e}")

    # ── Pipeline principal ───────────────────────────────────────────────────

    def run_dii_pipeline(self) -> list:
        print("=" * 60)
        print("  DII — Digest Input Intelligence | Panohayan™")
        print("=" * 60)

        archivos = [
            f for f in os.listdir(self.data_path)
            if not f.startswith(".")
        ]

        if not archivos:
            print("  [DII] No se encontraron documentos.")
            return []

        todos_resultados = []

        for archivo in archivos:
            ruta = os.path.join(self.data_path, archivo)
            source_type = archivo.split(".")[-1].lower()
            print(f"\n  [Docling] Procesando: {archivo}")

            # 1. Docling — conversión universal
            try:
                texto = self._convertir_con_docling(ruta)
                print(f"  [Docling] {len(texto)} chars extraídos")
            except Exception as e:
                print(f"  [Docling] Error: {e}")
                continue

            if not texto.strip():
                doc_hash = self._calcular_hash(archivo)
                document_id = self._registrar_documento(
                    nombre=archivo,
                    source_type=source_type,
                    doc_hash=doc_hash,
                    modelo_info={"tier": 0, "modelo": "none", "descripcion": "Documento vacío"},
                    doc_type="unknown"
                )
                self._actualizar_estado_documento(document_id, "failed")
                self.tm.log(component="DII", action="document_failed",
                            document_id=document_id, detail={
                                "reason": "empty_text_after_docling",
                                "file": archivo
                            })
                print(f"  [Docling] Documento vacío — omitiendo: {archivo}")
                continue

            # 2. Intent-A — analizar tipo de documento
            intent_config = self.intent_analyzer.analizar(texto)
            doc_type = intent_config["tipo"]
            prompt_extra = intent_config["prompt_extra"]

            # 3. Clasificador de contenido
            clasificacion = clasificar_documento(texto, source_type)
            print(f"  [Clasificador] tablas={clasificacion['tiene_tablas']} "
                  f"narrativo={clasificacion['es_narrativo']}")

            # 4. Model Router
            modelo_info = model_router.seleccionar(
                chars=clasificacion["chars"],
                tiene_tablas=clasificacion["tiene_tablas"],
                source_type=source_type,
                doc_type=doc_type
                )
            model_router.log_seleccion(modelo_info)

            # 5. Registrar documento en Supabase
            doc_hash = self._calcular_hash(texto)

            doc_existente = self.supabase.table("documents").select("id").eq(
                "doc_hash", doc_hash
            ).eq("org_id", self.org_id).execute()

            if doc_existente.data:
                self.tm.log(component="DII", action="document_duplicate",
                            document_id=doc_existente.data[0]["id"], detail={
                                "reason": "duplicate_hash",
                                "file": archivo,
                                "existing_id": doc_existente.data[0]["id"]
                            })
                print(f"  [IHS] Documento duplicado ignorado: {archivo}")
                continue

            document_id = self._registrar_documento(
                nombre=archivo,
                source_type=source_type,
                doc_hash=doc_hash,
                modelo_info=modelo_info,
                doc_type=doc_type
            )
            print(f"  [DII] Documento registrado: {document_id}")
            self.tm.log(component="DII", action="document_registered",
                        document_id=document_id, detail={
                            "doc_hash": doc_hash,
                            "chars": clasificacion["chars"],
                            "model_router": modelo_info,
                            "document_type": doc_type
                        })

            # 6. Extracción — ramas según clasificación
            entidades_raw = []

            if clasificacion["usar_langextract"]:
                entidades_raw += self._extraer_con_langextract(
                    texto, prompt_extra
                )

            if clasificacion["usar_llamaindex"]:
                entidades_raw += self._extraer_con_llamaindex(texto)

            # 7. Model Router — enriquecimiento LLM
            entidades_enriquecidas = entidades_raw

            # 8. Persistir en Supabase con IHS
            datos_finales = []
            for item in entidades_enriquecidas:
                entity_id = self._guardar_entidad(
                    document_id=document_id,
                    entidad=item["entidad"],
                    valor=item["valor"]
                )
                if entity_id:
                    self.tm.log(component="DII", action="extracted",
                                document_id=document_id, entity_id=entity_id,
                                detail={
                                    "entity_class": item["entidad"],
                                    "entity_value": item["valor"],
                                    "fuente": item.get("fuente", "unknown")
                                })
                datos_finales.append(item)

            # 9. Actualizar estado
            self._actualizar_estado_documento(document_id, "processed")
            self.tm.log(component="DII", action="document_processed",
                        document_id=document_id, detail={
                            "total_entities": len(datos_finales)
                        })

            print(f"  [DII] ✓ {len(datos_finales)} entidades procesadas")

            # 10. EDB — generar embeddings automáticamente
            self._generar_embeddings_documento(document_id)

            todos_resultados.extend(datos_finales)

        return todos_resultados


if __name__ == "__main__":
    dii = DigestInputIntelligence()
    resultado = dii.run_dii_pipeline()
    print("\n" + "=" * 60)
    print("  RESULTADO DII")
    print("=" * 60)
    for item in resultado:
        print(f"  [{item.get('fuente','?')}] "
              f"{item['entidad']}: {item['valor']}")