import os
from app.connectors.api_base import APIConnector

# ─── PIPEDRIVE CONNECTOR | Panohayan™ ───────────────────────────────────────
#
# Extrae deals, persons y organizations de Pipedrive via API v1.
# Usa API Token (query parameter).
# ─────────────────────────────────────────────────────────────────────────────


class PipedriveConnector(APIConnector):

    CONNECTOR_NAME = "pipedrive"

    def __init__(self, api_token: str = None, domain: str = None,
                 objetos: list = None):
        super().__init__()
        self.api_token = api_token or os.getenv("PIPEDRIVE_API_TOKEN", "")
        self.domain = domain or os.getenv("PIPEDRIVE_DOMAIN", "")
        self.BASE_URL = f"https://{self.domain}.pipedrive.com/api/v1" if self.domain else ""
        self.objetos = objetos or ["deals", "persons", "organizations"]

    def autenticar(self) -> bool:
        if not self.api_token or not self.domain:
            print("  [Pipedrive] Error: PIPEDRIVE_API_TOKEN o PIPEDRIVE_DOMAIN no configurado")
            return False

        try:
            response = self.session.get(
                f"{self.BASE_URL}/users/me",
                params={"api_token": self.api_token},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            nombre = data.get("data", {}).get("name", "Usuario")
            print(f"  [Pipedrive] Autenticado: {nombre}")
            return True
        except Exception as e:
            print(f"  [Pipedrive] Error de autenticación: {e}")
            return False

    def _get(self, url: str, params: dict = None) -> dict:
        """Override: Pipedrive usa api_token como query param."""
        if not self._autenticado:
            if not self.autenticar():
                raise ConnectionError("No se pudo autenticar con Pipedrive")
            self._autenticado = True

        params = params or {}
        params["api_token"] = self.api_token

        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def _extraer_objeto(self, tipo: str, limite: int = 100) -> list:
        """Extrae registros de un tipo de objeto."""
        registros = []

        try:
            start = 0
            while len(registros) < limite:
                data = self._get(
                    f"{self.BASE_URL}/{tipo}",
                    params={
                        "start": start,
                        "limit": min(100, limite - len(registros))
                    }
                )

                items = data.get("data") or []
                for item in items:
                    registros.append(item)

                info = data.get("additional_data", {}).get("pagination", {})
                if info.get("more_items_in_collection"):
                    start = info.get("next_start", start + 100)
                else:
                    break

        except Exception as e:
            print(f"  [Pipedrive] Error extrayendo {tipo}: {e}")

        print(f"  [Pipedrive] {len(registros)} {tipo} obtenidos")
        return registros

    def extraer_datos(self) -> dict:
        datos = {}
        for obj in self.objetos:
            registros = self._extraer_objeto(obj)
            if registros:
                datos[obj] = registros
        return datos
