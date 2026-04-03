import os
from dotenv import load_dotenv
from app.core.matrix import TraceabilityMatrix

load_dotenv()

# ─── SQL CONNECTOR | Panohayan™ ───────────────────────────────────────────────
#
# Conector SQL genérico para Panohayan™.
# Conecta a cualquier base de datos SQL del cliente.
# Soporta: MySQL, PostgreSQL, SQL Server, SQLite
# ─────────────────────────────────────────────────────────────────────────────

DRIVERS = {
    "mysql": "mysql+pymysql",
    "postgresql": "postgresql+psycopg2",
    "postgres": "postgresql+psycopg2",
    "mssql": "mssql+pyodbc",
    "sqlite": "sqlite"
}


class SQLConnector:
    """
    Conector SQL genérico para Panohayan™.
    Ejecuta queries configurables y procesa resultados via DII.
    """

    def __init__(self, db_type: str = None, host: str = None,
                 port: int = None, database: str = None,
                 username: str = None, password: str = None,
                 connection_string: str = None):
        self.db_type = db_type or os.getenv("SQL_DB_TYPE", "mysql")
        self.host = host or os.getenv("SQL_HOST", "localhost")
        self.port = port or int(os.getenv("SQL_PORT", "3306"))
        self.database = database or os.getenv("SQL_DATABASE", "")
        self.username = username or os.getenv("SQL_USER", "")
        self.password = password or int(os.getenv("SQL_PASSWORD", ""))
        self.connection_string = connection_string or os.getenv("SQL_CONNECTION_STRING")
        self.engine = None

    def conectar(self) -> bool:
        """Establece conexión a la base de datos."""
        try:
            from sqlalchemy import create_engine, text

            if self.connection_string:
                url = self.connection_string
            else:
                driver = DRIVERS.get(self.db_type, "mysql+pymysql")

                if self.db_type == "sqlite":
                    url = f"sqlite:///{self.database}"
                elif self.db_type in ["mssql"]:
                    url = (
                        f"{driver}://{self.username}:{self.password}"
                        f"@{self.host}:{self.port}/{self.database}"
                        f"?driver=ODBC+Driver+17+for+SQL+Server"
                    )
                else:
                    url = (
                        f"{driver}://{self.username}:{self.password}"
                        f"@{self.host}:{self.port}/{self.database}"
                    )

            self.engine = create_engine(url, pool_pre_ping=True)

            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            print(f"  [SQL] Conectado: {self.db_type}://{self.host}/{self.database}")
            return True

        except Exception as e:
            print(f"  [SQL] Error de conexión: {e}")
            return False

    def ejecutar_query(self, sql: str, params: dict = None) -> list:
        """Ejecuta una query personalizada."""
        try:
            from sqlalchemy import text
            with self.engine.connect() as conn:
                result = conn.execute(text(sql), params or {})
                columns = list(result.keys())
                return [dict(zip(columns, row)) for row in result.fetchall()]
        except Exception as e:
            print(f"  [SQL] Error en query: {e}")
            return []

    def listar_tablas(self) -> list:
        """Lista tablas disponibles."""
        try:
            from sqlalchemy import inspect
            inspector = inspect(self.engine)
            tablas = inspector.get_table_names()
            print(f"  [SQL] {len(tablas)} tablas encontradas")
            return tablas
        except Exception as e:
            print(f"  [SQL] Error listando tablas: {e}")
            return []

    def describir_tabla(self, tabla: str) -> list:
        """Describe las columnas de una tabla."""
        try:
            from sqlalchemy import inspect
            inspector = inspect(self.engine)
            columnas = inspector.get_columns(tabla)
            return [{"nombre": c["name"], "tipo": str(c["type"])} for c in columnas]
        except Exception as e:
            print(f"  [SQL] Error describiendo tabla: {e}")
            return []

    def procesar_tabla(self, tabla: str, limite: int = 100,
                       columnas: list = None, org_id: str = None) -> dict:
        """
        Procesa una tabla específica a través del pipeline Panohayan™.
        """
        import tempfile
        import shutil
        from app.core.dii import DigestInputIntelligence

        _org_id = org_id or os.getenv("ORG_ID", "default")

        if not self.engine and not self.conectar():
            return {"error": "No se pudo conectar a la BD"}

        # Query con columnas específicas o todas
        cols = ", ".join(columnas) if columnas else "*"
        datos = self.ejecutar_query(
            f"SELECT {cols} FROM {tabla} LIMIT {limite}"
            if self.db_type != "mssql"
            else f"SELECT TOP {limite} {cols} FROM {tabla}"
        )

        if not datos:
            return {"tabla": tabla, "registros": 0, "entidades": 0}

        # Convertir a texto estructurado
        lineas = [f"=== TABLA: {tabla.upper()} ===\n"]
        for row in datos:
            lineas.append("---")
            for key, value in row.items():
                if value is not None and str(value).strip():
                    lineas.append(f"{key}: {value}")
        texto = "\n".join(lineas)

        tmp_dir = tempfile.mkdtemp()
        tmp_file = os.path.join(tmp_dir, f"sql_{tabla}.txt")
        with open(tmp_file, "w", encoding="utf-8") as f:
            f.write(texto)

        try:
            dii = DigestInputIntelligence(org_id=_org_id)
            dii.data_path = tmp_dir
            entidades = dii.run_dii_pipeline()

            tm = TraceabilityMatrix(org_id=_org_id)
            tm.log(
                component="DII",
                action="sql_table_processed",
                detail={"tabla": tabla, "registros": len(datos),
                        "entidades": len(entidades)}
            )

            return {
                "tabla": tabla,
                "registros": len(datos),
                "entidades": len(entidades)
            }

        except Exception as e:
            return {"tabla": tabla, "error": str(e)}
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def procesar_base_completa(self, tablas: list = None,
                               limite_por_tabla: int = 100,
                               org_id: str = None) -> dict:
        """
        Procesa múltiples tablas o toda la base de datos.
        Si tablas=None, procesa todas las tablas disponibles.
        """
        if not self.conectar():
            return {"error": "No se pudo conectar"}

        tablas_a_procesar = tablas or self.listar_tablas()
        print(f"\n  [SQL] Procesando {len(tablas_a_procesar)} tablas")

        resumen = {
            "base_datos": self.database,
            "tablas_procesadas": 0,
            "entidades_totales": 0,
            "detalle": []
        }

        for tabla in tablas_a_procesar:
            print(f"\n  [SQL] → {tabla}")
            resultado = self.procesar_tabla(
                tabla=tabla,
                limite=limite_por_tabla,
                org_id=org_id
            )
            if "error" not in resultado:
                resumen["tablas_procesadas"] += 1
                resumen["entidades_totales"] += resultado.get("entidades", 0)
            resumen["detalle"].append(resultado)

        print(f"\n  [SQL] Resumen: {resumen}")
        return resumen


if __name__ == "__main__":
    print("=" * 60)
    print("  SQL Connector | Panohayan™")
    print("=" * 60)
    print("\n  Configura en .env:")
    print("  SQL_DB_TYPE=mysql | postgresql | mssql | sqlite")
    print("  SQL_HOST=localhost")
    print("  SQL_PORT=3306")
    print("  SQL_DATABASE=nombre_bd")
    print("  SQL_USER=usuario")
    print("  SQL_PASSWORD=password")
    print("  O bien:")
    print("  SQL_CONNECTION_STRING=dialect+driver://user:pass@host/db")
    