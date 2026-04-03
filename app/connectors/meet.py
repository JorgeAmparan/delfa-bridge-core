import os
import io
import tempfile
import shutil
from app.connectors.google_base import GoogleBaseConnector
from app.core.matrix import TraceabilityMatrix
from dotenv import load_dotenv

load_dotenv()


# ─── GOOGLE MEET CONNECTOR | Panohayan™ ─────────────────────────────────────
#
# Extrae grabaciones y transcripciones de Google Meet.
# Usa Google Drive API para acceder a grabaciones (Meet guarda en Drive).
# ─────────────────────────────────────────────────────────────────────────────


class MeetConnector(GoogleBaseConnector):

    SERVICE_NAME = "drive"
    SERVICE_VERSION = "v3"
    SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
    CONNECTOR_NAME = "meet"

    # Meet guarda grabaciones con este MIME type en Drive
    MEET_RECORDING_QUERY = (
        "mimeType='video/mp4' and "
        "fullText contains 'meet' and "
        "trashed=false"
    )

    # Transcripciones generadas por Meet (Google Docs)
    MEET_TRANSCRIPT_QUERY = (
        "(mimeType='application/vnd.google-apps.document' or "
        "mimeType='text/plain' or "
        "mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document') and "
        "fullText contains 'transcript' and "
        "trashed=false"
    )

    def __init__(self, folder_id: str = None, max_results: int = 20,
                 days_back: int = 7):
        super().__init__()
        self.folder_id = folder_id
        self.max_results = max_results
        self.days_back = days_back

    def _listar_transcripciones(self) -> list:
        """Lista transcripciones de Meet en Drive."""
        query = self.MEET_TRANSCRIPT_QUERY
        if self.folder_id:
            query = f"'{self.folder_id}' in parents and {query}"

        try:
            result = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType, createdTime, modifiedTime)",
                pageSize=self.max_results,
                orderBy="modifiedTime desc"
            ).execute()

            archivos = result.get("files", [])
            print(f"  [Meet] {len(archivos)} transcripciones encontradas")
            return archivos

        except Exception as e:
            print(f"  [Meet] Error listando transcripciones: {e}")
            return []

    def _descargar_archivo(self, file_id: str, filename: str,
                           mime_type: str, tmp_dir: str) -> str:
        """Descarga archivo de Drive a directorio temporal."""
        from googleapiclient.http import MediaIoBaseDownload

        # Google Docs nativos requieren exportación
        export_mimes = {
            "application/vnd.google-apps.document":
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }

        if mime_type in export_mimes:
            request = self.service.files().export_media(
                fileId=file_id, mimeType=export_mimes[mime_type]
            )
            extension = ".docx"
        else:
            request = self.service.files().get_media(fileId=file_id)
            extension = os.path.splitext(filename)[1] or ".txt"

        ruta = os.path.join(tmp_dir, f"{os.path.splitext(filename)[0]}{extension}")

        with io.FileIO(ruta, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

        print(f"  [Meet] Descargado: {filename}")
        return ruta

    def sincronizar(self, org_id: str = None) -> dict:
        """Extrae transcripciones de Meet y las procesa via DII."""
        from app.core.dii import DigestInputIntelligence
        from app.core.grg import GovernanceGuardrails

        _org_id = org_id or os.getenv("ORG_ID", "default")
        tm = TraceabilityMatrix(org_id=_org_id)

        if not self.autenticar_google():
            return {"error": "No se pudo autenticar con Google"}

        resumen = {
            "conector": "meet",
            "transcripciones_procesadas": 0,
            "entidades_totales": 0,
            "errores": []
        }

        transcripciones = self._listar_transcripciones()

        for archivo in transcripciones:
            tmp_dir = tempfile.mkdtemp()

            try:
                self._descargar_archivo(
                    file_id=archivo["id"],
                    filename=archivo["name"],
                    mime_type=archivo["mimeType"],
                    tmp_dir=tmp_dir
                )

                dii = DigestInputIntelligence(org_id=_org_id)
                dii.data_path = tmp_dir
                entidades = dii.run_dii_pipeline()

                # GRG
                from supabase import create_client
                supabase = create_client(
                    os.getenv("SUPABASE_URL"),
                    os.getenv("SUPABASE_KEY")
                )
                doc = supabase.table("documents").select("id").eq(
                    "org_id", _org_id
                ).order("created_at", desc=True).limit(1).execute()

                if doc.data:
                    grg = GovernanceGuardrails(org_id=_org_id)
                    grg.evaluar_documento(doc.data[0]["id"])

                resumen["transcripciones_procesadas"] += 1
                resumen["entidades_totales"] += len(entidades)

                tm.log(
                    component="DII",
                    action="meet_transcript_processed",
                    detail={
                        "file_id": archivo["id"],
                        "name": archivo["name"],
                        "entidades": len(entidades)
                    }
                )

            except Exception as e:
                resumen["errores"].append(f"{archivo['name']}: {str(e)}")
                print(f"  [Meet] Error: {e}")

            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        print(f"  [Meet] Resumen: {resumen}")
        return resumen
