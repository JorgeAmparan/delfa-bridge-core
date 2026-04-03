import os
import requests
from app.connectors.api_base import APIConnector
from dotenv import load_dotenv

load_dotenv()


# ─── ZOHO CRM CONNECTOR | Panohayan™ ────────────────────────────────────────
#
# Extrae datos de Zoho CRM via REST API v2.
# Usa OAuth2 Self-Client (refresh token).
# Soporta módulos configurables: Leads, Contacts, Accounts, Deals, etc.
# ─────────────────────────────────────────────────────────────────────────────


class ZohoConnector(APIConnector):

    CONNECTOR_NAME = "zoho"
    BASE_URL = "https://www.zohoapis.com/crm/v2"
    TOKEN_URL = "https://accounts.zoho.com/oauth/v2/token"

    def __init__(self, client_id: str = None, client_secret: str = None,
                 refresh_token: str = None, modulos: list = None):
        super().__init__()
        self.client_id = client_id or os.getenv("ZOHO_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("ZOHO_CLIENT_SECRET", "")
        self.refresh_token = refresh_token or os.getenv("ZOHO_REFRESH_TOKEN", "")
        self.modulos = modulos or ["Leads", "Contacts", "Accounts", "Deals"]

    def autenticar(self) -> bool:
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            print("  [Zoho] Error: ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET o ZOHO_REFRESH_TOKEN no configurados")
            return False

        try:
            response = requests.post(
                self.TOKEN_URL,
                params={
                    "refresh_token": self.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "refresh_token"
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            token = data.get("access_token")
            if not token:
                print(f"  [Zoho] Error: {data.get('error', 'no access_token')}")
                return False

            self.session.headers.update({
                "Authorization": f"Zoho-oauthtoken {token}",
                "Content-Type": "application/json"
            })

            print("  [Zoho] Autenticado con OAuth2 refresh token")
            return True

        except Exception as e:
            print(f"  [Zoho] Error de autenticación: {e}")
            return False

    def _extraer_modulo(self, modulo: str, limite: int = 200) -> list:
        """Extrae registros de un módulo de Zoho CRM."""
        registros = []
        page = 1

        try:
            while len(registros) < limite:
                data = self._get(
                    f"{self.BASE_URL}/{modulo}",
                    params={
                        "page": page,
                        "per_page": min(200, limite - len(registros))
                    }
                )

                items = data.get("data", [])
                if not items:
                    break

                registros.extend(items)
                info = data.get("info", {})
                if not info.get("more_records"):
                    break

                page += 1

        except Exception as e:
            print(f"  [Zoho] Error extrayendo {modulo}: {e}")

        print(f"  [Zoho] {len(registros)} {modulo} obtenidos")
        return registros

    def extraer_datos(self) -> dict:
        datos = {}
        for modulo in self.modulos:
            registros = self._extraer_modulo(modulo)
            if registros:
                datos[modulo] = registros
        return datos
