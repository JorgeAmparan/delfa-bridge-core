import os
import tempfile
import shutil
from abc import ABC, abstractmethod
from dotenv import load_dotenv
from app.core.matrix import TraceabilityMatrix

load_dotenv()


# ─── ERP MEXICANO BASE | Panohayan™ ─────────────────────────────────────────
#
# Clase base para ERPs mexicanos con patrón dual:
#   Opción A — Conexión directa a BD (ODBC/SQLAlchemy)
#   Opción B — Archivos exportados (XML CFDI, CSV, PDF)
#
# Usado por: MicroSip (existente), CONTPAQi, Aspel
# ─────────────────────────────────────────────────────────────────────────────


class ERPMexicanoDBBase(ABC):
    """
    Base para conexión directa a BD de ERPs mexicanos.
    Subclases definen: ERP_NAME, ENV_PREFIX, QUERIES.
    """

    ERP_NAME: str = "erp"
    ENV_PREFIX: str = "ERP"

    # Subclases definen queries por tipo de dato.
    # Cada key es el tipo (facturas, clientes, etc.)
    # Cada value es lista de queries a intentar (fallback por versión de BD)
    QUERIES: dict = {}

    def __init__(self, dsn: str = None, db_type: str = None,
                 host: str = None, port: int = None,
                 database: str = None, username: str = None,
                 password: str = None):
        prefix = self.ENV_PREFIX
        self.dsn = dsn or os.getenv(f"{prefix}_ODBC_DSN", "")
        self.db_type = db_type or os.getenv(f"{prefix}_DB_TYPE", "mssql")
        self.host = host or os.getenv(f"{prefix}_DB_HOST", "localhost")
        self.port = port or int(os.getenv(f"{prefix}_DB_PORT", "1433"))
        self.database = database or os.getenv(f"{prefix}_DB_NAME", "")
        self.username = username or os.getenv(f"{prefix}_USER", "")
        self.password = password or os.getenv(f"{prefix}_PASSWORD", "")
        self.engine = None

    def conectar(self) -> bool:
        """Conecta via ODBC DSN o SQLAlchemy connection string."""
        name = self.ERP_NAME

        try:
            # Opción 1: DSN directo (pyodbc)
            if self.dsn:
                import pyodbc
                conn_str = f"DSN={self.dsn};UID={self.username};PWD={self.password}"
                conn = pyodbc.connect(conn_str, timeout=10)
                conn.close()

                from sqlalchemy import create_engine
                self.engine = create_engine(
                    f"mssql+pyodbc:///?odbc_connect={conn_str}",
                    pool_pre_ping=True
                )
                print(f"  [{name}-DB] Conectado via DSN: {self.dsn}")
                return True

            # Opción 2: SQLAlchemy directo
            from sqlalchemy import create_engine, text

            if self.db_type == "mssql":
                url = (
                    f"mssql+pyodbc://{self.username}:{self.password}"
                    f"@{self.host}:{self.port}/{self.database}"
                    f"?driver=ODBC+Driver+17+for+SQL+Server"
                )
            elif self.db_type == "mysql":
                url = (
                    f"mysql+pymysql://{self.username}:{self.password}"
                    f"@{self.host}:{self.port}/{self.database}"
                    f"?charset=utf8mb4"
                )
            elif self.db_type == "firebird":
                url = (
                    f"firebird+fdb://{self.username}:{self.password}"
                    f"@{self.host}:{self.port}/{self.database}"
                )
            else:
                url = (
                    f"{self.db_type}://{self.username}:{self.password}"
                    f"@{self.host}:{self.port}/{self.database}"
                )

            self.engine = create_engine(url, pool_pre_ping=True)

            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            print(f"  [{name}-DB] Conectado a {self.db_type}://{self.host}/{self.database}")
            return True

        except Exception as e:
            print(f"  [{name}-DB] Error de conexión: {e}")
            return False

    def _query(self, sql: str, params: dict = None) -> list:
        """Ejecuta query y retorna lista de dicts."""
        from sqlalchemy import text
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            columns = list(result.keys())
            return [dict(zip(columns, row)) for row in result.fetchall()]

    def _intentar_queries(self, queries: list, tipo: str,
                          params: dict = None) -> list:
        """Intenta múltiples queries (fallback por versión de BD)."""
        for query in queries:
            try:
                datos = self._query(query, params)
                if datos:
                    print(f"  [{self.ERP_NAME}-DB] {len(datos)} {tipo} obtenidos")
                    return datos
            except Exception:
                continue
        return []

    def listar_tablas(self) -> list:
        """Lista tablas disponibles para diagnóstico."""
        try:
            from sqlalchemy import inspect
            inspector = inspect(self.engine)
            tablas = inspector.get_table_names()
            print(f"  [{self.ERP_NAME}-DB] {len(tablas)} tablas encontradas")
            return tablas
        except Exception as e:
            print(f"  [{self.ERP_NAME}-DB] Error listando tablas: {e}")
            return []

    @abstractmethod
    def extraer_datos(self) -> dict:
        """
        Extrae datos de la BD del ERP.
        Retorna dict {tipo: [registros]}.
        """
        pass

    def procesar_bd(self, org_id: str = None) -> dict:
        """Pipeline: conectar → extraer datos → DII → GRG → TM."""
        from app.core.dii import DigestInputIntelligence
        from app.core.grg import GovernanceGuardrails

        _org_id = org_id or os.getenv("ORG_ID", "default")
        name = self.ERP_NAME
        tm = TraceabilityMatrix(org_id=_org_id)

        if not self.conectar():
            return {"error": f"No se pudo conectar a {name}"}

        print(f"\n  [{name}-DB] Iniciando extracción")

        resumen = {
            "conector": f"{name}_db",
            "fuente": f"{self.db_type}://{self.host}/{self.database}",
            "entidades_totales": 0,
            "tipos_procesados": [],
            "errores": []
        }

        try:
            datos_por_tipo = self.extraer_datos()
        except Exception as e:
            return {"error": f"Error extrayendo datos: {str(e)}"}

        for tipo, datos in datos_por_tipo.items():
            if not datos:
                continue

            lineas = [f"=== {tipo.upper()} — {name.upper()} ===\n"]
            for item in datos:
                lineas.append("---")
                for key, value in item.items():
                    if value is not None and str(value).strip():
                        lineas.append(f"{key}: {value}")
            texto = "\n".join(lineas)

            tmp_dir = tempfile.mkdtemp()

            try:
                tmp_file = os.path.join(tmp_dir, f"{name}_{tipo}.txt")
                with open(tmp_file, "w", encoding="utf-8") as f:
                    f.write(texto)

                dii = DigestInputIntelligence(org_id=_org_id)
                dii.data_path = tmp_dir
                entidades = dii.run_dii_pipeline()

                from supabase import create_client
                supabase = create_client(
                    os.getenv("SUPABASE_URL"),
                    os.getenv("SUPABASE_KEY")
                )
                doc = supabase.table("documents").select("id").eq(
                    "org_id", _org_id
                ).eq("name", f"{name}_{tipo}.txt").order(
                    "created_at", desc=True
                ).limit(1).execute()

                if doc.data:
                    grg = GovernanceGuardrails(org_id=_org_id)
                    grg.evaluar_documento(doc.data[0]["id"])

                resumen["entidades_totales"] += len(entidades)
                resumen["tipos_procesados"].append({
                    "tipo": tipo,
                    "registros": len(datos),
                    "entidades": len(entidades)
                })

                tm.log(
                    component="DII",
                    action=f"{name}_db_processed",
                    detail={"tipo": tipo, "registros": len(datos)}
                )

            except Exception as e:
                resumen["errores"].append(f"{tipo}: {str(e)}")
                print(f"  [{name}-DB] Error procesando {tipo}: {e}")

            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        print(f"  [{name}-DB] Resumen: {resumen}")
        return resumen


class ERPMexicanoFileBase(ABC):
    """
    Base para procesamiento de archivos exportados de ERPs mexicanos.
    Soporta: XML (CFDI), CSV (reportes), PDF/DOCX/XLSX (directos a DII).
    """

    ERP_NAME: str = "erp"
    ENV_PREFIX: str = "ERP"

    def __init__(self, directorio: str = None):
        self.directorio = directorio or os.getenv(
            f"{self.ENV_PREFIX}_EXPORT_DIR",
            f"./data/{self.ERP_NAME.lower()}"
        )

    def _procesar_xml_cfdi(self, ruta: str) -> str:
        """Extrae datos de un XML CFDI estándar SAT."""
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(ruta)
            root = tree.getroot()

            ns = {
                "cfdi": "http://www.sat.gob.mx/cfd/4",
                "cfdi3": "http://www.sat.gob.mx/cfd/3"
            }

            lineas = [f"=== CFDI — {self.ERP_NAME.upper()} ===\n"]

            # Atributos del comprobante
            for campo in ["Folio", "Serie", "Fecha", "SubTotal", "Total",
                          "TipoDeComprobante", "Moneda", "FormaPago",
                          "MetodoPago", "LugarExpedicion"]:
                if campo in root.attrib:
                    lineas.append(f"{campo}: {root.attrib[campo]}")

            # Emisor
            for ns_key in ["cfdi", "cfdi3"]:
                emisor = root.find(f"{ns_key}:Emisor", ns)
                if emisor is not None:
                    lineas.append(f"\nEmisor RFC: {emisor.get('Rfc', '')}")
                    lineas.append(f"Emisor Nombre: {emisor.get('Nombre', '')}")
                    break

            # Receptor
            for ns_key in ["cfdi", "cfdi3"]:
                receptor = root.find(f"{ns_key}:Receptor", ns)
                if receptor is not None:
                    lineas.append(f"\nReceptor RFC: {receptor.get('Rfc', '')}")
                    lineas.append(f"Receptor Nombre: {receptor.get('Nombre', '')}")
                    break

            # Conceptos
            for ns_key in ["cfdi", "cfdi3"]:
                conceptos = root.findall(f".//{ns_key}:Concepto", ns)
                if conceptos:
                    lineas.append("\n--- CONCEPTOS ---")
                    for c in conceptos:
                        lineas.append(
                            f"Descripción: {c.get('Descripcion', '')} | "
                            f"Cantidad: {c.get('Cantidad', '')} | "
                            f"Importe: {c.get('Importe', '')}"
                        )
                    break

            return "\n".join(lineas)

        except Exception as e:
            print(f"  [{self.ERP_NAME}-File] Error procesando XML: {e}")
            return ""

    def _procesar_csv(self, ruta: str) -> str:
        """Extrae datos de un CSV exportado."""
        try:
            import csv
            lineas = [f"=== CSV — {self.ERP_NAME.upper()}: {os.path.basename(ruta)} ===\n"]

            with open(ruta, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    if i >= 200:
                        break
                    lineas.append("---")
                    for key, value in row.items():
                        if value and value.strip():
                            lineas.append(f"{key}: {value}")

            return "\n".join(lineas)

        except Exception as e:
            print(f"  [{self.ERP_NAME}-File] Error procesando CSV: {e}")
            return ""

    def procesar_directorio(self, org_id: str = None) -> dict:
        """Procesa todos los archivos exportados del ERP."""
        from app.core.dii import DigestInputIntelligence
        from app.core.grg import GovernanceGuardrails

        _org_id = org_id or os.getenv("ORG_ID", "default")
        name = self.ERP_NAME
        tm = TraceabilityMatrix(org_id=_org_id)

        if not os.path.exists(self.directorio):
            os.makedirs(self.directorio, exist_ok=True)
            return {
                "error": f"Directorio creado: {self.directorio}. "
                         f"Coloca los archivos exportados de {name} aquí."
            }

        print(f"\n  [{name}-File] Procesando: {self.directorio}")

        resumen = {
            "conector": f"{name}_files",
            "directorio": self.directorio,
            "archivos_procesados": 0,
            "entidades_totales": 0,
            "errores": []
        }

        for archivo in os.listdir(self.directorio):
            ruta = os.path.join(self.directorio, archivo)
            if not os.path.isfile(ruta):
                continue

            extension = archivo.rsplit(".", 1)[-1].lower() if "." in archivo else ""
            texto = ""

            if extension == "xml":
                texto = self._procesar_xml_cfdi(ruta)
            elif extension == "csv":
                texto = self._procesar_csv(ruta)
            elif extension in ("pdf", "docx", "doc", "xlsx", "xls", "pptx", "txt"):
                # DII con Docling maneja estos directamente
                tmp_dir = tempfile.mkdtemp()
                shutil.copy2(ruta, tmp_dir)
                try:
                    dii = DigestInputIntelligence(org_id=_org_id)
                    dii.data_path = tmp_dir
                    entidades = dii.run_dii_pipeline()
                    resumen["archivos_procesados"] += 1
                    resumen["entidades_totales"] += len(entidades)
                    tm.log(component="DII", action=f"{name}_file_processed",
                           detail={"archivo": archivo, "entidades": len(entidades)})
                except Exception as e:
                    resumen["errores"].append(f"{archivo}: {str(e)}")
                finally:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                continue
            else:
                continue

            if not texto:
                continue

            tmp_dir = tempfile.mkdtemp()
            tmp_file = os.path.join(tmp_dir, f"{archivo}.txt")
            with open(tmp_file, "w", encoding="utf-8") as f:
                f.write(texto)

            try:
                dii = DigestInputIntelligence(org_id=_org_id)
                dii.data_path = tmp_dir
                entidades = dii.run_dii_pipeline()

                from supabase import create_client
                supabase = create_client(
                    os.getenv("SUPABASE_URL"),
                    os.getenv("SUPABASE_KEY")
                )
                doc = supabase.table("documents").select("id").eq(
                    "org_id", _org_id
                ).order("created_at", desc=True).limit(1).execute()

                if doc.data:
                    grg = GovernanceGuardrails(org_id=_org_id)
                    grg.evaluar_documento(doc.data[0]["id"])

                resumen["archivos_procesados"] += 1
                resumen["entidades_totales"] += len(entidades)

                tm.log(component="DII", action=f"{name}_file_processed",
                       detail={"archivo": archivo, "entidades": len(entidades)})

            except Exception as e:
                resumen["errores"].append(f"{archivo}: {str(e)}")
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        print(f"  [{name}-File] Resumen: {resumen}")
        return resumen
