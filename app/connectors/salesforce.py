import os
from app.connectors.api_base import APIConnector
from dotenv import load_dotenv

load_dotenv()


# ─── SALESFORCE CONNECTOR | Panohayan™ ──────────────────────────────────────
#
# Extrae datos de Salesforce via REST API con simple-salesforce.
# Soporta objetos estándar (Account, Contact, Lead, Opportunity)
# y queries SOQL personalizadas.
# ─────────────────────────────────────────────────────────────────────────────


class SalesforceConnector(APIConnector):

    CONNECTOR_NAME = "salesforce"
    BASE_URL = ""  # Se configura dinámicamente tras login

    def __init__(self, username: str = None, password: str = None,
                 security_token: str = None, domain: str = None,
                 objetos: list = None, queries: dict = None):
        super().__init__()
        self.username = username or os.getenv("SALESFORCE_USERNAME", "")
        self.password = password or os.getenv("SALESFORCE_PASSWORD", "")
        self.security_token = security_token or os.getenv("SALESFORCE_TOKEN", "")
        self.domain = domain or os.getenv("SALESFORCE_DOMAIN", "login")
        self.objetos = objetos or ["Account", "Contact", "Lead", "Opportunity"]
        self.queries = queries or {}
        self.sf = None

    def autenticar(self) -> bool:
        if not all([self.username, self.password]):
            print("  [Salesforce] Error: SALESFORCE_USERNAME o SALESFORCE_PASSWORD no configurados")
            return False

        try:
            from simple_salesforce import Salesforce

            self.sf = Salesforce(
                username=self.username,
                password=self.password,
                security_token=self.security_token,
                domain=self.domain
            )

            print(f"  [Salesforce] Autenticado: {self.sf.sf_instance}")
            return True

        except ImportError:
            print("  [Salesforce] Error: pip install simple-salesforce")
            return False
        except Exception as e:
            print(f"  [Salesforce] Error de autenticación: {e}")
            return False

    def _query_soql(self, soql: str) -> list:
        """Ejecuta query SOQL y retorna registros."""
        try:
            result = self.sf.query_all(soql)
            registros = result.get("records", [])
            # Limpiar atributos internos de Salesforce
            for r in registros:
                r.pop("attributes", None)
            return registros
        except Exception as e:
            print(f"  [Salesforce] Error SOQL: {e}")
            return []

    def _extraer_objeto(self, objeto: str, limite: int = 200) -> list:
        """Extrae registros de un objeto estándar de Salesforce."""
        try:
            # Obtener campos del objeto
            desc = getattr(self.sf, objeto).describe()
            campos = [
                f["name"] for f in desc["fields"]
                if f["type"] not in ("base64", "address", "location")
            ]
            # Limitar campos para no exceder límites de SOQL
            campos_seleccion = campos[:30]

            soql = f"SELECT {', '.join(campos_seleccion)} FROM {objeto} ORDER BY LastModifiedDate DESC LIMIT {limite}"
            registros = self._query_soql(soql)

            print(f"  [Salesforce] {len(registros)} {objeto} obtenidos")
            return registros

        except Exception as e:
            print(f"  [Salesforce] Error extrayendo {objeto}: {e}")
            return []

    def extraer_datos(self) -> dict:
        datos = {}

        # Queries SOQL personalizadas
        for nombre, soql in self.queries.items():
            registros = self._query_soql(soql)
            if registros:
                datos[nombre] = registros

        # Objetos estándar
        for obj in self.objetos:
            if obj not in self.queries:
                registros = self._extraer_objeto(obj)
                if registros:
                    datos[obj] = registros

        return datos

    def ejecutar_query(self, soql: str, org_id: str = None) -> dict:
        """Ejecuta una query SOQL puntual y la procesa via DII."""
        if not self.sf:
            if not self.autenticar():
                return {"error": "No se pudo autenticar con Salesforce"}

        registros = self._query_soql(soql)
        if not registros:
            return {"registros": 0, "entidades": 0}

        # Procesar via el flujo estándar de APIConnector
        self._autenticado = True
        self.queries = {"custom_query": soql}
        self.objetos = []
        return self.sincronizar(org_id=org_id)
