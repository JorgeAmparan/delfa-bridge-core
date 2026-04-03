import os
from app.connectors.api_base import APIConnector

# ─── HUBSPOT CONNECTOR | Panohayan™ ─────────────────────────────────────────
#
# Extrae contactos, deals y companies de HubSpot via API v3.
# Usa Private App Token (API Key).
# ─────────────────────────────────────────────────────────────────────────────


class HubSpotConnector(APIConnector):

    CONNECTOR_NAME = "hubspot"
    BASE_URL = "https://api.hubapi.com"

    def __init__(self, api_key: str = None, objetos: list = None):
        super().__init__()
        self.api_key = api_key or os.getenv("HUBSPOT_API_KEY", "")
        self.objetos = objetos or ["contacts", "deals", "companies"]

    def autenticar(self) -> bool:
        if not self.api_key:
            print("  [HubSpot] Error: HUBSPOT_API_KEY no configurado")
            return False

        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })

        try:
            response = self.session.get(
                f"{self.BASE_URL}/crm/v3/objects/contacts",
                params={"limit": 1},
                timeout=10
            )
            response.raise_for_status()
            print("  [HubSpot] Autenticado correctamente")
            return True
        except Exception as e:
            print(f"  [HubSpot] Error de autenticación: {e}")
            return False

    def _extraer_objeto(self, tipo: str, limite: int = 100) -> list:
        """Extrae registros de un tipo de objeto CRM."""
        registros = []

        try:
            after = None
            while len(registros) < limite:
                params = {"limit": min(100, limite - len(registros))}
                if after:
                    params["after"] = after

                data = self._get(
                    f"{self.BASE_URL}/crm/v3/objects/{tipo}",
                    params=params
                )

                for resultado in data.get("results", []):
                    props = resultado.get("properties", {})
                    props["hubspot_id"] = resultado.get("id")
                    registros.append(props)

                paging = data.get("paging", {}).get("next")
                if paging:
                    after = paging.get("after")
                else:
                    break

        except Exception as e:
            print(f"  [HubSpot] Error extrayendo {tipo}: {e}")

        print(f"  [HubSpot] {len(registros)} {tipo} obtenidos")
        return registros

    def extraer_datos(self) -> dict:
        datos = {}
        for obj in self.objetos:
            registros = self._extraer_objeto(obj)
            if registros:
                datos[obj] = registros
        return datos
