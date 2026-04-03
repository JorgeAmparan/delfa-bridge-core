import os
from app.connectors.api_base import APIConnector
from dotenv import load_dotenv

load_dotenv()


# ─── SAP BUSINESS ONE CONNECTOR | Panohayan™ ────────────────────────────────
#
# Extrae datos de SAP Business One via Service Layer REST API.
# Autenticación session-based: POST /Login → cookie de sesión.
# Objetos principales: BusinessPartners, Invoices, Items, Orders, etc.
# ─────────────────────────────────────────────────────────────────────────────


class SAPB1Connector(APIConnector):

    CONNECTOR_NAME = "sapb1"

    # Objetos más comunes de SAP B1
    DEFAULT_OBJECTS = {
        "BusinessPartners": {
            "select": "CardCode,CardName,CardType,Phone1,EmailAddress,FederalTaxID,CurrentAccountBalance",
            "label": "socios_negocio"
        },
        "Invoices": {
            "select": "DocEntry,DocNum,DocDate,CardCode,CardName,DocTotal,DocCurrency,DocumentStatus",
            "label": "facturas",
            "orderby": "DocDate desc"
        },
        "Items": {
            "select": "ItemCode,ItemName,ItemType,QuantityOnStock,AvgPrice,SalesUnit",
            "label": "articulos"
        },
        "Orders": {
            "select": "DocEntry,DocNum,DocDate,CardCode,CardName,DocTotal,DocumentStatus",
            "label": "ordenes_venta",
            "orderby": "DocDate desc"
        },
        "PurchaseOrders": {
            "select": "DocEntry,DocNum,DocDate,CardCode,CardName,DocTotal,DocumentStatus",
            "label": "ordenes_compra",
            "orderby": "DocDate desc"
        },
    }

    def __init__(self, base_url: str = None, username: str = None,
                 password: str = None, company: str = None,
                 objetos: dict = None):
        super().__init__()
        self.BASE_URL = (
            base_url or os.getenv("SAPB1_URL", "")
        ).rstrip("/")
        self.username = username or os.getenv("SAPB1_USER", "")
        self.password = password or os.getenv("SAPB1_PASSWORD", "")
        self.company = company or os.getenv("SAPB1_COMPANY", "")
        self.objetos = objetos or self.DEFAULT_OBJECTS

        # SAP B1 Service Layer usa cookies de sesión
        self.session.verify = False  # SAP B1 frecuentemente usa cert self-signed

    def autenticar(self) -> bool:
        """Autentica con SAP B1 Service Layer (session-based)."""
        if not all([self.BASE_URL, self.username, self.password, self.company]):
            print("  [SAP B1] Error: SAPB1_URL, SAPB1_USER, SAPB1_PASSWORD o SAPB1_COMPANY no configurados")
            return False

        try:
            response = self.session.post(
                f"{self.BASE_URL}/Login",
                json={
                    "CompanyDB": self.company,
                    "UserName": self.username,
                    "Password": self.password
                },
                timeout=15
            )
            response.raise_for_status()

            # SAP B1 retorna SessionId en la respuesta y como cookie
            data = response.json()
            session_id = data.get("SessionId", "")

            if session_id:
                self.session.cookies.set("B1SESSION", session_id)

            print(f"  [SAP B1] Autenticado en empresa: {self.company}")
            return True

        except Exception as e:
            print(f"  [SAP B1] Error de autenticación: {e}")
            return False

    def _extraer_objeto(self, endpoint: str, config: dict,
                        limite: int = 200) -> list:
        """Extrae registros de un endpoint de Service Layer."""
        registros = []
        skip = 0
        select = config.get("select", "")
        orderby = config.get("orderby", "")

        try:
            while len(registros) < limite:
                params = {"$top": min(50, limite - len(registros)), "$skip": skip}
                if select:
                    params["$select"] = select
                if orderby:
                    params["$orderby"] = orderby

                data = self._get(
                    f"{self.BASE_URL}/{endpoint}",
                    params=params
                )

                items = data.get("value", [])
                if not items:
                    break

                registros.extend(items)
                skip += len(items)

                if len(items) < 50:
                    break

        except Exception as e:
            print(f"  [SAP B1] Error extrayendo {endpoint}: {e}")

        label = config.get("label", endpoint)
        print(f"  [SAP B1] {len(registros)} {label} obtenidos")
        return registros

    def extraer_datos(self) -> dict:
        datos = {}
        for endpoint, config in self.objetos.items():
            label = config.get("label", endpoint)
            registros = self._extraer_objeto(endpoint, config)
            if registros:
                datos[label] = registros
        return datos

    def ejecutar_query(self, query: str, org_id: str = None) -> dict:
        """
        Ejecuta una query SQL directa en SAP B1 via Service Layer.
        POST /SQLQueries('sql')/List con CrossJoinWithFilter.
        """
        if not self._autenticado:
            if not self.autenticar():
                return {"error": "No se pudo autenticar"}
            self._autenticado = True

        try:
            response = self.session.post(
                f"{self.BASE_URL}/SQLQueries('sql')/List",
                json={"SqlText": query},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            registros = data.get("value", [])
            if not registros:
                return {"registros": 0, "entidades": 0}

            # Procesar via flujo estándar
            self.objetos = {}
            return self.sincronizar(org_id=org_id)

        except Exception as e:
            return {"error": f"Error ejecutando query: {str(e)}"}

    def _logout(self):
        """Cierra sesión con SAP B1."""
        try:
            self.session.post(f"{self.BASE_URL}/Logout", timeout=5)
        except Exception:
            pass
