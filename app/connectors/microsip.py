import os
import requests
from dotenv import load_dotenv
from app.core.matrix import TraceabilityMatrix

load_dotenv()

# ─── MICROSIP CONNECTOR | Panohayan™ ─────────────────────────────────────────
#
# Conecta Delfa Bridge a MicroSip ERP via API REST local.
# Autenticación por sesión: POST /login → token → consultas
# ─────────────────────────────────────────────────────────────────────────────

class MicroSipConnector:
    """
    Conector MicroSip ERP para Panohayan™.
    Se conecta al servidor MicroSip del cliente via API REST.
    Extrae facturas, clientes, proveedores y movimientos.
    """

    def __init__(self, base_url: str = None, username: str = None,
                 password: str = None, selected_db: str = None):
        self.base_url = (base_url or os.getenv("MICROSIP_URL", "")).rstrip("/")
        self.username = username or os.getenv("MICROSIP_USER", "")
        self.password = password or os.getenv("MICROSIP_PASSWORD", "")
        self.selected_db = selected_db or os.getenv("MICROSIP_DB", "")
        self.session_token = None
        self.session = requests.Session()

    # ── Autenticación ─────────────────────────────────────────────────────────

    def login(self) -> bool:
        """
        Autentica con MicroSip y obtiene token de sesión.
        POST /login — body: {username, password, selected_db}
        """
        try:
            response = self.session.post(
                f"{self.base_url}/login",
                json={
                    "username": self.username,
                    "password": self.password,
                    "selected_db": self.selected_db
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            # MicroSip puede retornar token en diferentes campos
            self.session_token = (
                data.get("token") or
                data.get("access_token") or
                data.get("session") or
                data.get("jwt")
            )

            if self.session_token:
                self.session.headers.update({
                    "Authorization": f"Bearer {self.session_token}",
                    "Content-Type": "application/json"
                })

            print(f"  [MicroSip] Login exitoso — DB: {self.selected_db}")
            return True

        except requests.exceptions.ConnectionError:
            print(f"  [MicroSip] Error: No se puede conectar a {self.base_url}")
            return False
        except Exception as e:
            print(f"  [MicroSip] Error en login: {e}")
            return False

    def _get(self, endpoint: str, params: dict = None) -> dict:
        """Ejecuta GET autenticado contra MicroSip API."""
        if not self.session_token:
            if not self.login():
                raise ConnectionError("No se pudo autenticar con MicroSip")

        response = self.session.get(
            f"{self.base_url}/{endpoint.lstrip('/')}",
            params=params,
            timeout=30
        )
        response.raise_for_status()
        return response.json()

    # ── Extracción de datos ───────────────────────────────────────────────────

    def obtener_facturas(self, limite: int = 100,
                         fecha_desde: str = None) -> list:
        """Obtiene facturas de MicroSip."""
        params = {"limit": limite}
        if fecha_desde:
            params["fecha_desde"] = fecha_desde

        try:
            # Intentar endpoints comunes de MicroSip
            for endpoint in ["/facturas", "/invoices", "/ventas", "/cfdi"]:
                try:
                    data = self._get(endpoint, params)
                    facturas = data if isinstance(data, list) else data.get("data", [])
                    print(f"  [MicroSip] {len(facturas)} facturas obtenidas")
                    return facturas
                except Exception:
                    continue
            return []
        except Exception as e:
            print(f"  [MicroSip] Error obteniendo facturas: {e}")
            return []

    def obtener_clientes(self, limite: int = 100) -> list:
        """Obtiene catálogo de clientes."""
        try:
            for endpoint in ["/clientes", "/customers", "/contactos"]:
                try:
                    data = self._get(endpoint, {"limit": limite})
                    clientes = data if isinstance(data, list) else data.get("data", [])
                    print(f"  [MicroSip] {len(clientes)} clientes obtenidos")
                    return clientes
                except Exception:
                    continue
            return []
        except Exception as e:
            print(f"  [MicroSip] Error obteniendo clientes: {e}")
            return []

    def obtener_proveedores(self, limite: int = 100) -> list:
        """Obtiene catálogo de proveedores."""
        try:
            for endpoint in ["/proveedores", "/suppliers", "/vendors"]:
                try:
                    data = self._get(endpoint, {"limit": limite})
                    proveedores = data if isinstance(data, list) else data.get("data", [])
                    print(f"  [MicroSip] {len(proveedores)} proveedores obtenidos")
                    return proveedores
                except Exception:
                    continue
            return []
        except Exception as e:
            print(f"  [MicroSip] Error obteniendo proveedores: {e}")
            return []

    def obtener_movimientos(self, limite: int = 100,
                            fecha_desde: str = None) -> list:
        """Obtiene movimientos contables."""
        params = {"limit": limite}
        if fecha_desde:
            params["fecha_desde"] = fecha_desde

        try:
            for endpoint in ["/movimientos", "/transactions", "/contabilidad"]:
                try:
                    data = self._get(endpoint, params)
                    movimientos = data if isinstance(data, list) else data.get("data", [])
                    print(f"  [MicroSip] {len(movimientos)} movimientos obtenidos")
                    return movimientos
                except Exception:
                    continue
            return []
        except Exception as e:
            print(f"  [MicroSip] Error obteniendo movimientos: {e}")
            return []

    # ── Procesamiento Panohayan ───────────────────────────────────────────────

    def _datos_a_texto(self, datos: list, tipo: str) -> str:
        """Convierte datos JSON de MicroSip a texto estructurado para DII."""
        if not datos:
            return ""

        lineas = [f"=== {tipo.upper()} DE MICROSIP ERP ===\n"]

        for item in datos:
            lineas.append("---")
            for key, value in item.items():
                if value is not None and str(value).strip():
                    lineas.append(f"{key}: {value}")

        return "\n".join(lineas)

    def procesar_erp(self, org_id: str = None) -> dict:
        """
        Extrae datos de MicroSip y los procesa a través del pipeline Panohayan™.
        Convierte datos ERP en entidades estructuradas en EDB Lite.
        """
        import tempfile
        from app.core.dii import DigestInputIntelligence
        from app.core.grg import GovernanceGuardrails

        if org_id:
            os.environ["ORG_ID"] = org_id

        if not self.login():
            return {"error": "No se pudo conectar a MicroSip"}

        print(f"\n  [MicroSip] Iniciando extracción ERP completa")
        tm = TraceabilityMatrix()

        resumen = {
            "fuente": self.base_url,
            "db": self.selected_db,
            "entidades_totales": 0,
            "tipos_procesados": []
        }

        # Extraer cada tipo de dato
        tipos = {
            "facturas": self.obtener_facturas(),
            "clientes": self.obtener_clientes(),
            "proveedores": self.obtener_proveedores(),
            "movimientos": self.obtener_movimientos()
        }

        for tipo, datos in tipos.items():
            if not datos:
                continue

            # Convertir a texto estructurado
            texto = self._datos_a_texto(datos, tipo)
            if not texto:
                continue

            # Guardar como archivo temporal para DII
            tmp_dir = tempfile.mkdtemp()
            tmp_file = os.path.join(tmp_dir, f"microsip_{tipo}.txt")
            with open(tmp_file, "w", encoding="utf-8") as f:
                f.write(texto)

            # Pipeline DII
            try:
                dii = DigestInputIntelligence()
                dii.data_path = tmp_dir
                entidades = dii.run_dii_pipeline()

                # GRG
                from supabase import create_client
                supabase = create_client(
                    os.getenv("SUPABASE_URL"),
                    os.getenv("SUPABASE_KEY")
                )
                doc = supabase.table("documents").select("id").eq(
                    "org_id", os.getenv("ORG_ID", "default")
                ).eq("name", f"microsip_{tipo}.txt").order(
                    "created_at", desc=True
                ).limit(1).execute()

                if doc.data:
                    grg = GovernanceGuardrails()
                    grg.evaluar_documento(doc.data[0]["id"])

                resumen["entidades_totales"] += len(entidades)
                resumen["tipos_procesados"].append({
                    "tipo": tipo,
                    "registros": len(datos),
                    "entidades": len(entidades)
                })

                tm.log(
                    component="DII",
                    action="microsip_processed",
                    detail={"tipo": tipo, "registros": len(datos)}
                )

            except Exception as e:
                print(f"  [MicroSip] Error procesando {tipo}: {e}")
            finally:
                import shutil
                shutil.rmtree(tmp_dir, ignore_errors=True)

        print(f"\n  [MicroSip] Resumen: {resumen}")
        return resumen


if __name__ == "__main__":
    print("=" * 60)
    print("  MicroSip Connector | Panohayan™")
    print("=" * 60)
    print("\n  Configura en .env:")
    print("  MICROSIP_URL=http://18.222.120.251:5000")
    print("  MICROSIP_USER=tu_usuario")
    print("  MICROSIP_PASSWORD=tu_password")
    print("  MICROSIP_DB=189.206.114.34:/microsip datos/DELFA BOS.fdb")

# ─── OPCIÓN A — CONEXIÓN DIRECTA A BASE DE DATOS ─────────────────────────────

class MicroSipDBConnector:
    """
    Opción A — Conexión directa a la base de datos de MicroSip.
    Soporta SQL Server (pyodbc) y MySQL (pymysql).
    Para clientes con acceso privilegiado a la BD.
    """

    def __init__(self, db_type: str = None, host: str = None,
                 port: int = None, database: str = None,
                 username: str = None, password: str = None):
        self.db_type = db_type or os.getenv("MICROSIP_DB_TYPE", "mysql")
        self.host = host or os.getenv("MICROSIP_DB_HOST", "localhost")
        self.port = port or int(os.getenv("MICROSIP_DB_PORT", "3306"))
        self.database = database or os.getenv("MICROSIP_DB_NAME", "microsip")
        self.username = username or os.getenv("MICROSIP_DB_USER", "")
        self.password = password or os.getenv("MICROSIP_DB_PASSWORD", "")
        self.engine = None

    def conectar(self) -> bool:
        """Establece conexión a la base de datos."""
        try:
            from sqlalchemy import create_engine, text

            if self.db_type == "mysql":
                url = (
                    f"mysql+pymysql://{self.username}:{self.password}"
                    f"@{self.host}:{self.port}/{self.database}"
                    f"?charset=utf8mb4"
                )
            elif self.db_type == "mssql":
                url = (
                    f"mssql+pyodbc://{self.username}:{self.password}"
                    f"@{self.host}:{self.port}/{self.database}"
                    f"?driver=ODBC+Driver+17+for+SQL+Server"
                )
            else:
                raise ValueError(f"Tipo de BD no soportado: {self.db_type}")

            self.engine = create_engine(url, pool_pre_ping=True)

            # Verificar conexión
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            print(f"  [MicroSip-DB] Conectado a {self.db_type}://{self.host}/{self.database}")
            return True

        except Exception as e:
            print(f"  [MicroSip-DB] Error de conexión: {e}")
            return False

    def _query(self, sql: str, params: dict = None) -> list:
        """Ejecuta una query y retorna lista de dicts."""
        from sqlalchemy import text
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]

    def obtener_facturas(self, limite: int = 100,
                         fecha_desde: str = None) -> list:
        """Obtiene facturas directamente de la BD de MicroSip."""
        try:
            # Tablas comunes en MicroSip según versión
            queries = [
                # MicroSip versión moderna
                f"""
                SELECT TOP {limite} f.serie, f.folio, f.fecha,
                       c.nombre as cliente, f.subtotal, f.iva, f.total,
                       f.uuid, f.estatus
                FROM facturas f
                LEFT JOIN clientes c ON f.id_cliente = c.id
                {"WHERE f.fecha >= :fecha_desde" if fecha_desde else ""}
                ORDER BY f.fecha DESC
                """,
                # MicroSip versión alternativa
                f"""
                SELECT * FROM documentos_venta
                LIMIT {limite}
                """
            ]

            for query in queries:
                try:
                    params = {"fecha_desde": fecha_desde} if fecha_desde else {}
                    datos = self._query(query, params)
                    if datos:
                        print(f"  [MicroSip-DB] {len(datos)} facturas obtenidas")
                        return datos
                except Exception:
                    continue
            return []

        except Exception as e:
            print(f"  [MicroSip-DB] Error obteniendo facturas: {e}")
            return []

    def obtener_clientes(self, limite: int = 100) -> list:
        """Obtiene catálogo de clientes de la BD."""
        try:
            queries = [
                f"SELECT TOP {limite} * FROM clientes ORDER BY nombre",
                f"SELECT * FROM clientes LIMIT {limite}",
                f"SELECT * FROM cat_clientes LIMIT {limite}"
            ]
            for query in queries:
                try:
                    datos = self._query(query)
                    if datos:
                        print(f"  [MicroSip-DB] {len(datos)} clientes obtenidos")
                        return datos
                except Exception:
                    continue
            return []
        except Exception as e:
            print(f"  [MicroSip-DB] Error obteniendo clientes: {e}")
            return []

    def obtener_proveedores(self, limite: int = 100) -> list:
        """Obtiene catálogo de proveedores de la BD."""
        try:
            queries = [
                f"SELECT TOP {limite} * FROM proveedores ORDER BY nombre",
                f"SELECT * FROM proveedores LIMIT {limite}",
                f"SELECT * FROM cat_proveedores LIMIT {limite}"
            ]
            for query in queries:
                try:
                    datos = self._query(query)
                    if datos:
                        print(f"  [MicroSip-DB] {len(datos)} proveedores obtenidos")
                        return datos
                except Exception:
                    continue
            return []
        except Exception as e:
            print(f"  [MicroSip-DB] Error obteniendo proveedores: {e}")
            return []

    def obtener_cuentas_por_cobrar(self, limite: int = 100) -> list:
        """Obtiene cuentas por cobrar — muy relevante para PYMEs."""
        try:
            queries = [
                f"""
                SELECT TOP {limite} cxc.*, c.nombre as cliente
                FROM cuentas_x_cobrar cxc
                LEFT JOIN clientes c ON cxc.id_cliente = c.id
                WHERE cxc.saldo > 0
                ORDER BY cxc.fecha_vencimiento
                """,
                f"""
                SELECT * FROM cxc WHERE saldo > 0 LIMIT {limite}
                """
            ]
            for query in queries:
                try:
                    datos = self._query(query)
                    if datos:
                        print(f"  [MicroSip-DB] {len(datos)} CxC obtenidas")
                        return datos
                except Exception:
                    continue
            return []
        except Exception as e:
            print(f"  [MicroSip-DB] Error obteniendo CxC: {e}")
            return []

    def listar_tablas(self) -> list:
        """Lista todas las tablas disponibles — útil para diagnóstico."""
        try:
            if self.db_type == "mysql":
                datos = self._query("SHOW TABLES")
            else:
                datos = self._query(
                    "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                    "WHERE TABLE_TYPE='BASE TABLE'"
                )
            tablas = [list(d.values())[0] for d in datos]
            print(f"  [MicroSip-DB] {len(tablas)} tablas encontradas")
            return tablas
        except Exception as e:
            print(f"  [MicroSip-DB] Error listando tablas: {e}")
            return []

    def procesar_erp_db(self, org_id: str = None) -> dict:
        """
        Extrae datos directamente de la BD de MicroSip
        y los procesa a través del pipeline Panohayan™.
        """
        import tempfile
        import shutil
        from app.core.dii import DigestInputIntelligence
        from app.core.grg import GovernanceGuardrails

        if org_id:
            os.environ["ORG_ID"] = org_id

        if not self.conectar():
            return {"error": "No se pudo conectar a la BD de MicroSip"}

        print(f"\n  [MicroSip-DB] Iniciando extracción BD completa")
        tm = TraceabilityMatrix()

        resumen = {
            "fuente": f"{self.db_type}://{self.host}/{self.database}",
            "entidades_totales": 0,
            "tipos_procesados": []
        }

        tipos = {
            "facturas": self.obtener_facturas(),
            "clientes": self.obtener_clientes(),
            "proveedores": self.obtener_proveedores(),
            "cuentas_por_cobrar": self.obtener_cuentas_por_cobrar()
        }

        for tipo, datos in tipos.items():
            if not datos:
                continue

            # Convertir a texto estructurado
            lineas = [f"=== {tipo.upper()} — MICROSIP BD ===\n"]
            for item in datos:
                lineas.append("---")
                for key, value in item.items():
                    if value is not None and str(value).strip():
                        lineas.append(f"{key}: {value}")
            texto = "\n".join(lineas)

            tmp_dir = tempfile.mkdtemp()
            tmp_file = os.path.join(tmp_dir, f"microsip_db_{tipo}.txt")
            with open(tmp_file, "w", encoding="utf-8") as f:
                f.write(texto)

            try:
                dii = DigestInputIntelligence()
                dii.data_path = tmp_dir
                entidades = dii.run_dii_pipeline()

                resumen["entidades_totales"] += len(entidades)
                resumen["tipos_procesados"].append({
                    "tipo": tipo,
                    "registros": len(datos),
                    "entidades": len(entidades)
                })

                tm.log(
                    component="DII",
                    action="microsip_db_processed",
                    detail={"tipo": tipo, "registros": len(datos)}
                )

            except Exception as e:
                print(f"  [MicroSip-DB] Error procesando {tipo}: {e}")
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        print(f"\n  [MicroSip-DB] Resumen: {resumen}")
        return resumen


# ─── OPCIÓN B — ARCHIVOS EXPORTADOS ──────────────────────────────────────────

class MicroSipFileConnector:
    """
    Opción B — Procesamiento de archivos exportados de MicroSip.
    Soporta: XML (CFDI/facturas), CSV (reportes), PDF (estados de cuenta).
    Para clientes sin API ni acceso directo a BD.
    """

    def __init__(self, directorio: str = None):
        self.directorio = directorio or os.getenv("MICROSIP_EXPORT_DIR", "./data/microsip")

    def _procesar_xml_cfdi(self, ruta: str) -> str:
        """Extrae datos de un XML CFDI de MicroSip."""
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(ruta)
            root = tree.getroot()

            # Namespaces comunes en CFDI México
            ns = {
                "cfdi": "http://www.sat.gob.mx/cfd/4",
                "cfdi3": "http://www.sat.gob.mx/cfd/3"
            }

            lineas = ["=== CFDI / FACTURA ELECTRÓNICA ===\n"]

            # Atributos principales del comprobante
            attribs = root.attrib
            campos_clave = [
                "Folio", "Serie", "Fecha", "SubTotal", "IVA",
                "Total", "TipoDeComprobante", "UUID", "Moneda",
                "FormaPago", "MetodoPago", "LugarExpedicion"
            ]
            for campo in campos_clave:
                if campo in attribs:
                    lineas.append(f"{campo}: {attribs[campo]}")

            # Emisor
            for ns_key in ["cfdi", "cfdi3"]:
                emisor = root.find(f"{ns_key}:Emisor", ns)
                if emisor is not None:
                    lineas.append(f"\n--- EMISOR ---")
                    lineas.append(f"RFC Emisor: {emisor.get('Rfc', '')}")
                    lineas.append(f"Nombre Emisor: {emisor.get('Nombre', '')}")
                    break

            # Receptor
            for ns_key in ["cfdi", "cfdi3"]:
                receptor = root.find(f"{ns_key}:Receptor", ns)
                if receptor is not None:
                    lineas.append(f"\n--- RECEPTOR ---")
                    lineas.append(f"RFC Receptor: {receptor.get('Rfc', '')}")
                    lineas.append(f"Nombre Receptor: {receptor.get('Nombre', '')}")
                    break

            # Conceptos
            for ns_key in ["cfdi", "cfdi3"]:
                conceptos = root.findall(f".//{ns_key}:Concepto", ns)
                if conceptos:
                    lineas.append(f"\n--- CONCEPTOS ---")
                    for concepto in conceptos:
                        lineas.append(
                            f"Descripción: {concepto.get('Descripcion', '')} | "
                            f"Cantidad: {concepto.get('Cantidad', '')} | "
                            f"Importe: {concepto.get('Importe', '')}"
                        )
                    break

            return "\n".join(lineas)

        except Exception as e:
            print(f"  [MicroSip-File] Error procesando XML: {e}")
            return ""

    def _procesar_csv_microsip(self, ruta: str) -> str:
        """Extrae datos de un CSV exportado de MicroSip."""
        try:
            import csv
            lineas = [f"=== REPORTE CSV MICROSIP: {os.path.basename(ruta)} ===\n"]

            with open(ruta, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    if i >= 200:  # Límite para no saturar DII
                        break
                    lineas.append("---")
                    for key, value in row.items():
                        if value and value.strip():
                            lineas.append(f"{key}: {value}")

            return "\n".join(lineas)

        except Exception as e:
            print(f"  [MicroSip-File] Error procesando CSV: {e}")
            return ""

    def procesar_directorio(self, org_id: str = None) -> dict:
        """
        Procesa todos los archivos exportados de MicroSip en el directorio.
        Soporta XML (CFDI), CSV y PDF.
        """
        import tempfile
        import shutil
        from app.core.dii import DigestInputIntelligence
        from app.core.grg import GovernanceGuardrails

        if org_id:
            os.environ["ORG_ID"] = org_id

        if not os.path.exists(self.directorio):
            os.makedirs(self.directorio, exist_ok=True)
            return {
                "error": f"Directorio creado: {self.directorio}. "
                         f"Coloca los archivos exportados de MicroSip aquí."
            }

        print(f"\n  [MicroSip-File] Procesando: {self.directorio}")
        tm = TraceabilityMatrix()

        resumen = {
            "directorio": self.directorio,
            "archivos_procesados": 0,
            "entidades_totales": 0,
            "errores": []
        }

        # Procesar por tipo de archivo
        for archivo in os.listdir(self.directorio):
            ruta = os.path.join(self.directorio, archivo)
            extension = archivo.lower().split(".")[-1]

            texto = ""

            if extension == "xml":
                texto = self._procesar_xml_cfdi(ruta)
            elif extension == "csv":
                texto = self._procesar_csv_microsip(ruta)
            elif extension in ["pdf", "docx", "xlsx"]:
                # DII con Docling maneja estos directamente
                tmp_dir = tempfile.mkdtemp()
                import shutil as sh
                sh.copy2(ruta, tmp_dir)
                try:
                    dii = DigestInputIntelligence()
                    dii.data_path = tmp_dir
                    entidades = dii.run_dii_pipeline()
                    resumen["archivos_procesados"] += 1
                    resumen["entidades_totales"] += len(entidades)
                    tm.log(component="DII", action="microsip_file_processed",
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

            # Procesar texto via DII
            tmp_dir = tempfile.mkdtemp()
            tmp_file = os.path.join(tmp_dir, f"{archivo}.txt")
            with open(tmp_file, "w", encoding="utf-8") as f:
                f.write(texto)

            try:
                dii = DigestInputIntelligence()
                dii.data_path = tmp_dir
                entidades = dii.run_dii_pipeline()

                resumen["archivos_procesados"] += 1
                resumen["entidades_totales"] += len(entidades)

                tm.log(component="DII", action="microsip_file_processed",
                       detail={"archivo": archivo, "entidades": len(entidades)})

            except Exception as e:
                resumen["errores"].append(f"{archivo}: {str(e)}")
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        print(f"\n  [MicroSip-File] Resumen: {resumen}")
        return resumen    
