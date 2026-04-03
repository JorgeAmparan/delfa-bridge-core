import os
import requests
from app.connectors.api_base import APIConnector
from dotenv import load_dotenv

load_dotenv()


# ─── MICROSOFT GRAPH BASE CONNECTOR | Panohayan™ ────────────────────────────
#
# Autenticación Azure AD compartida para conectores Microsoft Graph.
# OneDrive, Outlook y Teams (Fase 3) heredan de aquí.
# Usa msal para Client Credentials flow (app-only, sin usuario interactivo).
# ─────────────────────────────────────────────────────────────────────────────


class MSGraphConnector(APIConnector):
    """
    Base para conectores Microsoft Graph.
    Maneja autenticación Azure AD con msal + Client Credentials.
    Subclases implementan: extraer_datos().
    """

    CONNECTOR_NAME = "msgraph"
    BASE_URL = "https://graph.microsoft.com/v1.0"

    # Subclases pueden agregar scopes específicos
    GRAPH_SCOPES = ["https://graph.microsoft.com/.default"]

    def __init__(self, client_id: str = None, client_secret: str = None,
                 tenant_id: str = None):
        super().__init__()
        self.client_id = client_id or os.getenv("AZURE_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("AZURE_CLIENT_SECRET", "")
        self.tenant_id = tenant_id or os.getenv("AZURE_TENANT_ID", "")
        self._token = None

    def autenticar(self) -> bool:
        """Autentica con Azure AD usando msal Client Credentials."""
        if not all([self.client_id, self.client_secret, self.tenant_id]):
            print(f"  [{self.CONNECTOR_NAME}] Error: AZURE_CLIENT_ID, AZURE_CLIENT_SECRET o AZURE_TENANT_ID no configurados")
            return False

        try:
            import msal

            app = msal.ConfidentialClientApplication(
                self.client_id,
                authority=f"https://login.microsoftonline.com/{self.tenant_id}",
                client_credential=self.client_secret
            )

            result = app.acquire_token_for_client(scopes=self.GRAPH_SCOPES)

            if "access_token" not in result:
                error = result.get("error_description", "Unknown error")
                print(f"  [{self.CONNECTOR_NAME}] Error Azure AD: {error}")
                return False

            self._token = result["access_token"]
            self.session.headers.update({
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json"
            })

            print(f"  [{self.CONNECTOR_NAME}] Autenticado con Azure AD")
            return True

        except ImportError:
            print(f"  [{self.CONNECTOR_NAME}] Error: pip install msal")
            return False
        except Exception as e:
            print(f"  [{self.CONNECTOR_NAME}] Error de autenticación: {e}")
            return False

    def _graph_get(self, endpoint: str, params: dict = None) -> dict:
        """GET contra Microsoft Graph API."""
        url = endpoint if endpoint.startswith("http") else f"{self.BASE_URL}{endpoint}"
        return self._get(url, params=params)

    def _graph_get_all(self, endpoint: str, params: dict = None,
                       limite: int = 200) -> list:
        """GET con paginación automática (@odata.nextLink)."""
        resultados = []
        url = f"{self.BASE_URL}{endpoint}"

        while url and len(resultados) < limite:
            data = self._get(url, params=params)
            resultados.extend(data.get("value", []))
            url = data.get("@odata.nextLink")
            params = None  # nextLink ya incluye params

        return resultados[:limite]
