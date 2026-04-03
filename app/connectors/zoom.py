import os
import tempfile
import shutil
from app.connectors.api_base import APIConnector
from app.core.matrix import TraceabilityMatrix
from dotenv import load_dotenv

load_dotenv()


# ─── ZOOM CONNECTOR | Panohayan™ ────────────────────────────────────────────
#
# Extrae grabaciones y transcripciones de Zoom via Server-to-Server OAuth.
# Procesa transcripciones (VTT/texto) a través del pipeline DII.
# ─────────────────────────────────────────────────────────────────────────────


class ZoomConnector(APIConnector):

    CONNECTOR_NAME = "zoom"
    BASE_URL = "https://api.zoom.us/v2"
    TOKEN_URL = "https://zoom.us/oauth/token"

    def __init__(self, account_id: str = None, client_id: str = None,
                 client_secret: str = None, user_id: str = "me",
                 days_back: int = 7):
        super().__init__()
        self.account_id = account_id or os.getenv("ZOOM_ACCOUNT_ID", "")
        self.client_id = client_id or os.getenv("ZOOM_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("ZOOM_CLIENT_SECRET", "")
        self.user_id = user_id
        self.days_back = days_back

    def autenticar(self) -> bool:
        """Autentica con Zoom Server-to-Server OAuth."""
        if not all([self.account_id, self.client_id, self.client_secret]):
            print("  [Zoom] Error: ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID o ZOOM_CLIENT_SECRET no configurados")
            return False

        try:
            response = self.session.post(
                self.TOKEN_URL,
                params={"grant_type": "account_credentials", "account_id": self.account_id},
                auth=(self.client_id, self.client_secret),
                timeout=10
            )
            response.raise_for_status()
            token = response.json().get("access_token")

            if not token:
                print("  [Zoom] Error: no se obtuvo access_token")
                return False

            self.session.headers.update({
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            })

            print("  [Zoom] Autenticado con Server-to-Server OAuth")
            return True

        except Exception as e:
            print(f"  [Zoom] Error de autenticación: {e}")
            return False

    def _listar_grabaciones(self) -> list:
        """Lista grabaciones recientes."""
        from datetime import datetime, timedelta

        fecha_desde = (datetime.utcnow() - timedelta(days=self.days_back)).strftime("%Y-%m-%d")

        try:
            data = self._get(
                f"{self.BASE_URL}/users/{self.user_id}/recordings",
                params={"from": fecha_desde, "page_size": 30}
            )

            meetings = data.get("meetings", [])
            print(f"  [Zoom] {len(meetings)} reuniones con grabación")
            return meetings

        except Exception as e:
            print(f"  [Zoom] Error listando grabaciones: {e}")
            return []

    def _descargar_transcripcion(self, download_url: str, filename: str,
                                  tmp_dir: str) -> str:
        """Descarga transcripción de Zoom."""
        try:
            response = self.session.get(download_url, timeout=60)
            response.raise_for_status()

            ruta = os.path.join(tmp_dir, filename)
            with open(ruta, "wb") as f:
                f.write(response.content)

            print(f"  [Zoom] Descargado: {filename}")
            return ruta

        except Exception as e:
            print(f"  [Zoom] Error descargando {filename}: {e}")
            return None

    def extraer_datos(self) -> dict:
        return {}

    def sincronizar(self, org_id: str = None) -> dict:
        """Extrae transcripciones de Zoom y las procesa via DII."""
        from app.core.dii import DigestInputIntelligence
        from app.core.grg import GovernanceGuardrails

        _org_id = org_id or os.getenv("ORG_ID", "default")
        tm = TraceabilityMatrix(org_id=_org_id)

        if not self.autenticar():
            return {"error": "No se pudo autenticar con Zoom"}
        self._autenticado = True

        resumen = {
            "conector": "zoom",
            "reuniones_procesadas": 0,
            "transcripciones_procesadas": 0,
            "entidades_totales": 0,
            "errores": []
        }

        meetings = self._listar_grabaciones()

        for meeting in meetings:
            tmp_dir = tempfile.mkdtemp()
            topic = meeting.get("topic", "Sin título")

            try:
                # Buscar transcripciones en los archivos de grabación
                tiene_transcripcion = False
                for recording in meeting.get("recording_files", []):
                    file_type = recording.get("file_type", "")

                    # Solo transcripciones (TRANSCRIPT o CHAT)
                    if file_type not in ("TRANSCRIPT", "CHAT", "TIMELINE"):
                        continue

                    download_url = recording.get("download_url", "")
                    if not download_url:
                        continue

                    ext = ".vtt" if file_type == "TRANSCRIPT" else ".txt"
                    filename = f"zoom_{meeting.get('id', '')}_{file_type.lower()}{ext}"

                    ruta = self._descargar_transcripcion(
                        download_url, filename, tmp_dir
                    )
                    if ruta:
                        tiene_transcripcion = True

                # Si no hay transcripción, crear resumen de metadata
                if not tiene_transcripcion:
                    lineas = [
                        "=== REUNIÓN ZOOM ===\n",
                        f"Tema: {topic}",
                        f"Fecha: {meeting.get('start_time', '')}",
                        f"Duración: {meeting.get('duration', 0)} minutos",
                        f"Participantes: {meeting.get('total_size', 'N/A')}",
                    ]
                    meta_file = os.path.join(tmp_dir, f"zoom_{meeting.get('id', '')}_meta.txt")
                    with open(meta_file, "w", encoding="utf-8") as f:
                        f.write("\n".join(lineas))

                # DII pipeline
                dii = DigestInputIntelligence(org_id=_org_id)
                dii.data_path = tmp_dir
                entidades = dii.run_dii_pipeline()

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

                resumen["reuniones_procesadas"] += 1
                if tiene_transcripcion:
                    resumen["transcripciones_procesadas"] += 1
                resumen["entidades_totales"] += len(entidades)

                tm.log(
                    component="DII",
                    action="zoom_processed",
                    detail={
                        "meeting_id": meeting.get("id"),
                        "topic": topic,
                        "entidades": len(entidades)
                    }
                )

            except Exception as e:
                resumen["errores"].append(f"{topic}: {str(e)}")
                print(f"  [Zoom] Error: {e}")

            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        print(f"  [Zoom] Resumen: {resumen}")
        return resumen
