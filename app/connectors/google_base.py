import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()


# ─── GOOGLE BASE CONNECTOR | Panohayan™ ─────────────────────────────────────
#
# Autenticación compartida para conectores Google (Gmail, Meet).
# Reutiliza el patrón de Service Account de google_drive.py.
# ─────────────────────────────────────────────────────────────────────────────


class GoogleBaseConnector:
    """
    Base para conectores Google API.
    Maneja autenticación con Service Account y construye el servicio.
    """

    SERVICE_NAME: str = ""
    SERVICE_VERSION: str = ""
    SCOPES: list = []
    CONNECTOR_NAME: str = "google"

    def __init__(self):
        self.service = None
        self.credentials = None

    def autenticar_google(self) -> bool:
        """
        Autentica con Google via Service Account.
        El archivo de credenciales se configura en GOOGLE_SERVICE_ACCOUNT_FILE.
        """
        sa_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        if not sa_file or not os.path.exists(sa_file):
            print(f"  [{self.CONNECTOR_NAME}] Error: GOOGLE_SERVICE_ACCOUNT_FILE no configurado")
            return False

        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                sa_file, scopes=self.SCOPES
            )
            self.service = build(
                self.SERVICE_NAME, self.SERVICE_VERSION,
                credentials=self.credentials
            )
            print(f"  [{self.CONNECTOR_NAME}] Autenticado con Service Account")
            return True

        except Exception as e:
            print(f"  [{self.CONNECTOR_NAME}] Error de autenticación: {e}")
            return False
