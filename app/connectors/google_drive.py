import os
import io
import tempfile
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

load_dotenv()

# ─── GOOGLE DRIVE CONNECTOR | Panohayan™ ─────────────────────────────────────
#
# Conecta Delfa Bridge a Google Drive.
# Descarga documentos y los procesa a través del pipeline DII.
# Soporta: PDF, DOCX, XLSX, Google Docs (exportados)
# ─────────────────────────────────────────────────────────────────────────────

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly"
]

MIME_TYPES_SOPORTADOS = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.google-apps.document": ".docx",        # Google Docs → DOCX
    "application/vnd.google-apps.spreadsheet": ".xlsx",     # Google Sheets → XLSX
}

EXPORT_MIME_TYPES = {
    "application/vnd.google-apps.document": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.google-apps.spreadsheet": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class GoogleDriveConnector:
    """
    Conector Google Drive para Panohayan™.
    Descarga y procesa documentos desde carpetas de Drive.
    """

    def __init__(self):
        self.service = self._autenticar()

    def _autenticar(self):
        """
        Autentica con Google Drive.
        Soporta Service Account (producción) y credenciales OAuth (desarrollo).
        """
        # Opción 1: Service Account (recomendado para producción)
        service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        if service_account_file and os.path.exists(service_account_file):
            credentials = service_account.Credentials.from_service_account_file(
                service_account_file,
                scopes=SCOPES
            )
            print("  [Drive] Autenticado con Service Account")
            return build("drive", "v3", credentials=credentials)

        # Opción 2: Credenciales OAuth desde .env
        credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE")
        if credentials_file and os.path.exists(credentials_file):
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            import pickle

            token_file = "token.pickle"
            credentials = None

            if os.path.exists(token_file):
                with open(token_file, "rb") as token:
                    credentials = pickle.load(token)

            if not credentials or not credentials.valid:
                if credentials and credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_file, SCOPES
                    )
                    credentials = flow.run_local_server(port=0)

                with open(token_file, "wb") as token:
                    pickle.dump(credentials, token)

            print("  [Drive] Autenticado con OAuth")
            return build("drive", "v3", credentials=credentials)

        raise ValueError(
            "No se encontraron credenciales de Google Drive. "
            "Configura GOOGLE_SERVICE_ACCOUNT_FILE o GOOGLE_CREDENTIALS_FILE en .env"
        )

    def listar_archivos(self, folder_id: str = None,
                        query: str = None) -> list:
        """
        Lista archivos en Drive.
        Si folder_id es None, lista en la raíz accesible.
        """
        q_parts = []

        if folder_id:
            q_parts.append(f"'{folder_id}' in parents")

        if query:
            q_parts.append(query)

        # Solo tipos soportados
        mime_conditions = " or ".join([
            f"mimeType='{mime}'"
            for mime in MIME_TYPES_SOPORTADOS.keys()
        ])
        q_parts.append(f"({mime_conditions})")
        q_parts.append("trashed=false")

        q = " and ".join(q_parts)

        resultado = self.service.files().list(
            q=q,
            fields="files(id, name, mimeType, size, modifiedTime)",
            pageSize=50
        ).execute()

        archivos = resultado.get("files", [])
        print(f"  [Drive] {len(archivos)} archivos encontrados")
        return archivos

    def descargar_archivo(self, file_id: str,
                          file_name: str,
                          mime_type: str) -> str:
        """
        Descarga un archivo de Drive a un directorio temporal.
        Retorna la ruta del archivo descargado.
        """
        extension = MIME_TYPES_SOPORTADOS.get(mime_type, ".pdf")
        tmp_dir = tempfile.mkdtemp()
        tmp_path = os.path.join(tmp_dir, f"{file_name}{extension}")

        # Google Docs nativos requieren exportación
        if mime_type in EXPORT_MIME_TYPES:
            export_mime = EXPORT_MIME_TYPES[mime_type]
            request = self.service.files().export_media(
                fileId=file_id,
                mimeType=export_mime
            )
        else:
            request = self.service.files().get_media(fileId=file_id)

        with io.FileIO(tmp_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

        print(f"  [Drive] Descargado: {file_name}{extension}")
        return tmp_path

    def procesar_carpeta(self, folder_id: str,
                         org_id: str = None) -> dict:
        """
        Procesa todos los documentos de una carpeta de Drive
        a través del pipeline Panohayan™ completo.
        """
        from app.core.dii import DigestInputIntelligence
        from app.core.grg import GovernanceGuardrails
        from app.core.matrix import TraceabilityMatrix

        if org_id:
            os.environ["ORG_ID"] = org_id

        print(f"\n  [Drive] Procesando carpeta: {folder_id}")
        archivos = self.listar_archivos(folder_id=folder_id)

        resumen = {
            "carpeta": folder_id,
            "archivos_encontrados": len(archivos),
            "archivos_procesados": 0,
            "entidades_totales": 0,
            "errores": []
        }

        tm = TraceabilityMatrix()

        for archivo in archivos:
            try:
                print(f"\n  [Drive] → {archivo['name']}")

                # Descargar a directorio temporal
                tmp_path = self.descargar_archivo(
                    file_id=archivo["id"],
                    file_name=os.path.splitext(archivo["name"])[0],
                    mime_type=archivo["mimeType"]
                )

                # Configurar DII para usar el archivo descargado
                tmp_dir = os.path.dirname(tmp_path)
                dii = DigestInputIntelligence()
                dii.data_path = tmp_dir

                # Pipeline DII completo
                entidades = dii.run_dii_pipeline()

                # GRG
                from supabase import create_client
                supabase = create_client(
                    os.getenv("SUPABASE_URL"),
                    os.getenv("SUPABASE_KEY")
                )
                doc = supabase.table("documents").select("id").eq(
                    "org_id", os.getenv("ORG_ID", "default")
                ).eq(
                    "name", os.path.basename(tmp_path)
                ).order("created_at", desc=True).limit(1).execute()

                if doc.data:
                    grg = GovernanceGuardrails()
                    grg.evaluar_documento(doc.data[0]["id"])

                resumen["archivos_procesados"] += 1
                resumen["entidades_totales"] += len(entidades)

                # Log en TM
                tm.log(
                    component="DII",
                    action="drive_file_processed",
                    detail={
                        "drive_file_id": archivo["id"],
                        "file_name": archivo["name"],
                        "entidades": len(entidades)
                    }
                )

                # Limpiar temporal
                import shutil
                shutil.rmtree(tmp_dir, ignore_errors=True)

            except Exception as e:
                error = f"{archivo['name']}: {str(e)}"
                resumen["errores"].append(error)
                print(f"  [Drive] Error: {error}")

        print(f"\n  [Drive] Resumen: {resumen}")
        return resumen


if __name__ == "__main__":
    print("=" * 60)
    print("  Google Drive Connector | Panohayan™")
    print("=" * 60)
    print("\n  Para usar este conector necesitas configurar:")
    print("  GOOGLE_SERVICE_ACCOUNT_FILE=ruta/al/service_account.json")
    print("  O bien:")
    print("  GOOGLE_CREDENTIALS_FILE=ruta/al/credentials.json")
    print("\n  Luego ejecuta:")
    print("  connector = GoogleDriveConnector()")
    print("  connector.procesar_carpeta('tu_folder_id')")
    