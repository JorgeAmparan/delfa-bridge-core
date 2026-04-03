import os
import io
import base64
import tempfile
import shutil
from app.connectors.google_base import GoogleBaseConnector
from app.core.matrix import TraceabilityMatrix
from dotenv import load_dotenv

load_dotenv()


# ─── GMAIL CONNECTOR | Panohayan™ ───────────────────────────────────────────
#
# Extrae correos y adjuntos de Gmail via API.
# Procesa cuerpo de correo + archivos adjuntos a través del pipeline DII.
# ─────────────────────────────────────────────────────────────────────────────


class GmailConnector(GoogleBaseConnector):

    SERVICE_NAME = "gmail"
    SERVICE_VERSION = "v1"
    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
    CONNECTOR_NAME = "gmail"

    EXTENSIONES_ADJUNTOS = {
        "pdf", "docx", "doc", "xlsx", "xls", "csv",
        "txt", "html", "htm", "png", "jpg", "jpeg"
    }

    def __init__(self, user_email: str = "me", query: str = None,
                 max_results: int = 50):
        super().__init__()
        self.user_email = user_email
        self.query = query or "newer_than:7d"
        self.max_results = max_results

    def _obtener_mensaje(self, msg_id: str) -> dict:
        """Obtiene un mensaje completo de Gmail."""
        return self.service.users().messages().get(
            userId=self.user_email, id=msg_id, format="full"
        ).execute()

    def _extraer_headers(self, mensaje: dict) -> dict:
        """Extrae headers relevantes del mensaje."""
        headers = {}
        for h in mensaje.get("payload", {}).get("headers", []):
            nombre = h["name"].lower()
            if nombre in ("from", "to", "subject", "date", "cc"):
                headers[h["name"]] = h["value"]
        return headers

    def _extraer_cuerpo(self, payload: dict) -> str:
        """Extrae texto plano del cuerpo del mensaje."""
        if payload.get("mimeType") == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

        for parte in payload.get("parts", []):
            texto = self._extraer_cuerpo(parte)
            if texto:
                return texto

        return ""

    def _descargar_adjuntos(self, mensaje: dict, tmp_dir: str) -> list:
        """Descarga adjuntos soportados a directorio temporal."""
        adjuntos = []
        partes = mensaje.get("payload", {}).get("parts", [])

        for parte in partes:
            filename = parte.get("filename", "")
            if not filename:
                continue

            extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if extension not in self.EXTENSIONES_ADJUNTOS:
                continue

            att_id = parte.get("body", {}).get("attachmentId")
            if not att_id:
                continue

            try:
                att = self.service.users().messages().attachments().get(
                    userId=self.user_email,
                    messageId=mensaje["id"],
                    id=att_id
                ).execute()

                data = base64.urlsafe_b64decode(att["data"])
                ruta = os.path.join(tmp_dir, filename)
                with open(ruta, "wb") as f:
                    f.write(data)
                adjuntos.append(ruta)
                print(f"  [Gmail] Adjunto: {filename}")

            except Exception as e:
                print(f"  [Gmail] Error descargando adjunto {filename}: {e}")

        return adjuntos

    def sincronizar(self, org_id: str = None) -> dict:
        """Extrae correos + adjuntos y los procesa via DII pipeline."""
        from app.core.dii import DigestInputIntelligence
        from app.core.grg import GovernanceGuardrails

        _org_id = org_id or os.getenv("ORG_ID", "default")
        tm = TraceabilityMatrix(org_id=_org_id)

        if not self.autenticar_google():
            return {"error": "No se pudo autenticar con Gmail"}

        print(f"\n  [Gmail] Buscando correos: {self.query}")

        resumen = {
            "conector": "gmail",
            "correos_procesados": 0,
            "adjuntos_procesados": 0,
            "entidades_totales": 0,
            "errores": []
        }

        try:
            result = self.service.users().messages().list(
                userId=self.user_email,
                q=self.query,
                maxResults=self.max_results
            ).execute()

            mensajes = result.get("messages", [])
            print(f"  [Gmail] {len(mensajes)} correos encontrados")

        except Exception as e:
            return {"error": f"Error listando correos: {str(e)}"}

        for msg_ref in mensajes:
            tmp_dir = tempfile.mkdtemp()

            try:
                mensaje = self._obtener_mensaje(msg_ref["id"])
                headers = self._extraer_headers(mensaje)
                cuerpo = self._extraer_cuerpo(mensaje.get("payload", {}))

                # Crear texto del correo
                lineas = ["=== CORREO DE GMAIL ===\n"]
                for key, value in headers.items():
                    lineas.append(f"{key}: {value}")
                if cuerpo:
                    lineas.append(f"\n--- CUERPO ---\n{cuerpo}")
                texto = "\n".join(lineas)

                # Guardar correo como texto
                correo_file = os.path.join(tmp_dir, f"gmail_{msg_ref['id']}.txt")
                with open(correo_file, "w", encoding="utf-8") as f:
                    f.write(texto)

                # Descargar adjuntos al mismo directorio
                adjuntos = self._descargar_adjuntos(mensaje, tmp_dir)

                # DII pipeline (procesa texto + adjuntos en tmp_dir)
                dii = DigestInputIntelligence(org_id=_org_id)
                dii.data_path = tmp_dir
                entidades = dii.run_dii_pipeline()

                resumen["correos_procesados"] += 1
                resumen["adjuntos_procesados"] += len(adjuntos)
                resumen["entidades_totales"] += len(entidades)

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

                tm.log(
                    component="DII",
                    action="gmail_processed",
                    detail={
                        "message_id": msg_ref["id"],
                        "subject": headers.get("Subject", ""),
                        "adjuntos": len(adjuntos),
                        "entidades": len(entidades)
                    }
                )

            except Exception as e:
                resumen["errores"].append(f"{msg_ref['id']}: {str(e)}")
                print(f"  [Gmail] Error: {e}")

            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        print(f"  [Gmail] Resumen: {resumen}")
        return resumen
