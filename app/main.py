import os
import sys
from dotenv import load_dotenv

load_dotenv()

# ─── PANOHAYAN™ ORCHESTRATOR ──────────────────────────────────────────────────
#
# Punto de entrada principal de Delfa Bridge.
# Coordina el pipeline completo:
# DII → EDB → GRG → TM
# Con Intent-A y Intent-B integrados en cada componente.
# ─────────────────────────────────────────────────────────────────────────────

from app.core.dii import DigestInputIntelligence
from app.core.edb import EntityDataBrain
from app.core.grg import GovernanceGuardrails
from app.core.matrix import TraceabilityMatrix


class PanohayanOrchestrator:
    """
    Orquestador principal de Panohayan™.
    Ejecuta el pipeline completo para un conjunto de documentos.
    """

    def __init__(self):
        self.org_id = os.getenv("ORG_ID", "default")
        self.dii = DigestInputIntelligence()
        self.edb = EntityDataBrain()
        self.grg = GovernanceGuardrails()
        self.tm = TraceabilityMatrix()

    def procesar_documentos(self, aplicar_grg: bool = True) -> dict:
        """
        Pipeline completo — procesa todos los documentos en data/.

        Flujo:
        1. DII — extrae entidades con Intent-A + LangExtract/LlamaIndex
        2. EDB — genera embeddings automáticamente (integrado en DII)
        3. GRG — evalúa gobernanza si aplicar_grg=True
        4. TM  — registra resumen del pipeline
        """
        print("=" * 60)
        print("  PANOHAYAN™ | Delfa Bridge")
        print(f"  Organización: {self.org_id}")
        print("=" * 60)

        resultados = {
            "org_id": self.org_id,
            "documentos_procesados": 0,
            "entidades_extraidas": 0,
            "entidades_aprobadas": 0,
            "entidades_cuarentena": 0,
            "entidades_marcadas": 0,
            "errores": []
        }

        # ── Paso 1: DII — extracción + embeddings ────────────────────────────
        print("\n  ── Paso 1: DII + EDB ──")
        try:
            entidades = self.dii.run_dii_pipeline()
            resultados["entidades_extraidas"] = len(entidades)

            # Contar documentos procesados
            docs = self.tm.supabase.table("documents").select(
                "id", count="exact"
            ).eq("org_id", self.org_id).eq(
                "status", "processed"
            ).execute()
            resultados["documentos_procesados"] = docs.count

        except Exception as e:
            error = f"DII Error: {e}"
            resultados["errores"].append(error)
            print(f"  [ERROR] {error}")
            return resultados

        # ── Paso 2: GRG — gobernanza ─────────────────────────────────────────
        if aplicar_grg:
            print("\n  ── Paso 2: GRG ──")
            try:
                docs_procesados = self.tm.supabase.table("documents").select(
                    "id"
                ).eq("org_id", self.org_id).eq(
                    "status", "processed"
                ).execute()

                for doc in docs_procesados.data:
                    resumen_grg = self.grg.evaluar_documento(doc["id"])
                    resultados["entidades_aprobadas"] += resumen_grg.get("aprobadas", 0)
                    resultados["entidades_cuarentena"] += resumen_grg.get("cuarentena", 0)
                    resultados["entidades_marcadas"] += resumen_grg.get("marcadas", 0)

            except Exception as e:
                error = f"GRG Error: {e}"
                resultados["errores"].append(error)
                print(f"  [ERROR] {error}")

        # ── Paso 3: TM — resumen final ───────────────────────────────────────
        print("\n  ── Paso 3: TM ──")
        self.tm.log(
            component="TM",
            action="pipeline_completed",
            detail=resultados
        )

        return resultados

    def buscar(self, query: str, limit: int = 5) -> list:
        """
        Búsqueda semántica con Intent-B integrado.
        Punto de entrada para consultas en lenguaje natural.
        """
        print("\n" + "=" * 60)
        print(f"  BÚSQUEDA: '{query}'")
        print("=" * 60)

        resultados = self.edb.search_semantic(query, limit=limit)

        # Log en TM
        self.tm.log(
            component="TM",
            action="searched",
            detail={
                "query": query,
                "resultados": len(resultados)
            }
        )

        return resultados

    def resumen(self) -> dict:
        """Estado actual del EDB para esta organización."""
        return self.edb.get_summary()


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    orquestador = PanohayanOrchestrator()

    # Modo: procesar o buscar
    if len(sys.argv) > 1 and sys.argv[1] == "buscar":
        # Uso: python3 -m app.main buscar "quién firma el contrato"
        if len(sys.argv) > 2:
            query = " ".join(sys.argv[2:])
            resultados = orquestador.buscar(query)
            print("\n  RESULTADOS:")
            for r in resultados:
                print(f"    → [{r['entity_class']}] {r['entity_value']} "
                      f"(score: {r['similarity']:.2f})")
        else:
            print("  Uso: python3 -m app.main buscar 'tu consulta aquí'")

    else:
        # Modo por defecto: procesar documentos
        resultados = orquestador.procesar_documentos(aplicar_grg=True)

        print("\n" + "=" * 60)
        print("  RESUMEN FINAL PANOHAYAN™")
        print("=" * 60)
        print(f"  Documentos procesados : {resultados['documentos_procesados']}")
        print(f"  Entidades extraídas   : {resultados['entidades_extraidas']}")
        print(f"  Entidades aprobadas   : {resultados['entidades_aprobadas']}")
        print(f"  En cuarentena         : {resultados['entidades_cuarentena']}")
        print(f"  Marcadas              : {resultados['entidades_marcadas']}")

        if resultados["errores"]:
            print(f"\n  Errores: {resultados['errores']}")

        # Resumen EDB
        print("\n  ESTADO EDB LITE:")
        summary = orquestador.resumen()
        print(f"  Documentos en EDB : {summary['total_documentos']}")
        print(f"  Entidades en EDB  : {summary['total_entidades']}")