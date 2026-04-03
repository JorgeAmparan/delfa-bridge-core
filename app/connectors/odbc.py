import os
import tempfile
import shutil
from app.core.matrix import TraceabilityMatrix
from dotenv import load_dotenv

load_dotenv()


# ─── ODBC CONNECTOR | Panohayan™ ────────────────────────────────────────────
#
# Conector ODBC genérico para bases de datos legacy.
# Soporta cualquier BD con driver ODBC instalado.
# Complementa sql.py (que usa SQLAlchemy) para casos donde solo hay ODBC.
# ─────────────────────────────────────────────────────────────────────────────


class ODBCConnector:

    CONNECTOR_NAME = "odbc"

    def __init__(self, connection_string: str = None,
                 dsn: str = None, username: str = None,
                 password: str = None):
        self.connection_string = connection_string or os.getenv("ODBC_CONNECTION_STRING", "")
        self.dsn = dsn
        self.username = username
        self.password = password
        self.conn = None

    def conectar(self) -> bool:
        """Establece conexión ODBC."""
        try:
            import pyodbc

            if self.connection_string:
                self.conn = pyodbc.connect(self.connection_string, timeout=10)
            elif self.dsn:
                self.conn = pyodbc.connect(
                    f"DSN={self.dsn};UID={self.username or ''};PWD={self.password or ''}",
                    timeout=10
                )
            else:
                print("  [ODBC] Error: ODBC_CONNECTION_STRING o DSN no configurado")
                return False

            # Verificar conexión
            cursor = self.conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()

            print("  [ODBC] Conectado exitosamente")
            return True

        except ImportError:
            print("  [ODBC] Error: pip install pyodbc")
            return False
        except Exception as e:
            print(f"  [ODBC] Error de conexión: {e}")
            return False

    def ejecutar_query(self, sql: str, params: tuple = None) -> list:
        """Ejecuta query y retorna lista de dicts."""
        cursor = self.conn.cursor()
        cursor.execute(sql, params or ())
        columnas = [desc[0] for desc in cursor.description]
        registros = [dict(zip(columnas, row)) for row in cursor.fetchall()]
        cursor.close()
        return registros

    def listar_tablas(self) -> list:
        """Lista tablas disponibles."""
        try:
            cursor = self.conn.cursor()
            tablas = [
                row.table_name
                for row in cursor.tables(tableType="TABLE")
            ]
            cursor.close()
            print(f"  [ODBC] {len(tablas)} tablas encontradas")
            return tablas
        except Exception as e:
            print(f"  [ODBC] Error listando tablas: {e}")
            return []

    def procesar_query(self, sql: str, nombre: str = "query",
                       org_id: str = None) -> dict:
        """Ejecuta una query y procesa el resultado via DII."""
        from app.core.dii import DigestInputIntelligence
        from app.core.grg import GovernanceGuardrails

        _org_id = org_id or os.getenv("ORG_ID", "default")
        tm = TraceabilityMatrix(org_id=_org_id)

        if not self.conn and not self.conectar():
            return {"error": "No se pudo conectar via ODBC"}

        try:
            datos = self.ejecutar_query(sql)
        except Exception as e:
            return {"error": f"Error ejecutando query: {str(e)}"}

        if not datos:
            return {"nombre": nombre, "registros": 0, "entidades": 0}

        # Convertir a texto
        lineas = [f"=== {nombre.upper()} — ODBC ===\n"]
        for row in datos:
            lineas.append("---")
            for key, value in row.items():
                if value is not None and str(value).strip():
                    lineas.append(f"{key}: {value}")
        texto = "\n".join(lineas)

        tmp_dir = tempfile.mkdtemp()

        try:
            tmp_file = os.path.join(tmp_dir, f"odbc_{nombre}.txt")
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
            ).order("created_at", desc=True).limit(1).execute()

            if doc.data:
                grg = GovernanceGuardrails(org_id=_org_id)
                grg.evaluar_documento(doc.data[0]["id"])

            tm.log(
                component="DII",
                action="odbc_query_processed",
                detail={"nombre": nombre, "registros": len(datos)}
            )

            return {
                "nombre": nombre,
                "registros": len(datos),
                "entidades": len(entidades)
            }

        except Exception as e:
            return {"error": str(e)}
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def procesar_tablas(self, tablas: list = None, limite: int = 100,
                        org_id: str = None) -> dict:
        """Procesa múltiples tablas via DII."""
        if not self.conn and not self.conectar():
            return {"error": "No se pudo conectar"}

        tablas_a_procesar = tablas or self.listar_tablas()
        resumen = {
            "conector": "odbc",
            "tablas_procesadas": 0,
            "entidades_totales": 0,
            "detalle": []
        }

        for tabla in tablas_a_procesar:
            try:
                resultado = self.procesar_query(
                    f"SELECT TOP {limite} * FROM [{tabla}]",
                    nombre=tabla,
                    org_id=org_id
                )
            except Exception:
                # Fallback para BDs que no soportan TOP
                try:
                    resultado = self.procesar_query(
                        f"SELECT * FROM [{tabla}] LIMIT {limite}",
                        nombre=tabla,
                        org_id=org_id
                    )
                except Exception as e:
                    resultado = {"tabla": tabla, "error": str(e)}

            if "error" not in resultado:
                resumen["tablas_procesadas"] += 1
                resumen["entidades_totales"] += resultado.get("entidades", 0)
            resumen["detalle"].append(resultado)

        return resumen
