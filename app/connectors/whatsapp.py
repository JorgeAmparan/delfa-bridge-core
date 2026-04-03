import os
import tempfile
import shutil
from app.connectors.webhook_base import WebhookConnector
from app.core.matrix import TraceabilityMatrix
from dotenv import load_dotenv

load_dotenv()


# ─── WHATSAPP BUSINESS CONNECTOR | Panohayan™ ───────────────────────────────
#
# Recibe mensajes de WhatsApp Business Cloud API via webhook.
# Soporta: texto, documentos, imágenes.
# Modo dual: webhook (recibir) + sync (descargar media pendiente).
# ─────────────────────────────────────────────────────────────────────────────


class WhatsAppConnector(WebhookConnector):

    CONNECTOR_NAME = "whatsapp"
    SECRET_ENV_VAR = None  # Usa verify_token para webhook verification

    GRAPH_URL = "https://graph.facebook.com/v18.0"

    def __init__(self):
        self.token = os.getenv("WHATSAPP_TOKEN", "")
        self.verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
        self.phone_id = os.getenv("WHATSAPP_PHONE_ID", "")

    def verificar_webhook(self, mode: str, token: str,
                          challenge: str) -> str:
        """
        Verificación de webhook de WhatsApp (GET).
        Retorna challenge si el token es correcto, None si no.
        """
        if mode == "subscribe" and token == self.verify_token:
            return challenge
        return None

    def extraer_contenido(self, payload: dict) -> str:
        """
        Extrae mensajes del payload webhook de WhatsApp Cloud API.
        Estructura: entry[].changes[].value.messages[]
        """
        lineas = ["=== MENSAJES DE WHATSAPP ===\n"]
        mensajes_encontrados = 0

        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                # Contactos (info del remitente)
                contactos = {
                    c.get("wa_id", ""): c.get("profile", {}).get("name", "")
                    for c in value.get("contacts", [])
                }

                for mensaje in value.get("messages", []):
                    wa_id = mensaje.get("from", "")
                    nombre = contactos.get(wa_id, wa_id)
                    tipo = mensaje.get("type", "")
                    timestamp = mensaje.get("timestamp", "")

                    lineas.append("---")
                    lineas.append(f"De: {nombre} ({wa_id})")
                    lineas.append(f"Timestamp: {timestamp}")
                    lineas.append(f"Tipo: {tipo}")

                    if tipo == "text":
                        texto = mensaje.get("text", {}).get("body", "")
                        lineas.append(f"Mensaje: {texto}")

                    elif tipo == "document":
                        doc = mensaje.get("document", {})
                        lineas.append(f"Documento: {doc.get('filename', 'sin nombre')}")
                        lineas.append(f"Caption: {doc.get('caption', '')}")
                        lineas.append(f"Media ID: {doc.get('id', '')}")

                    elif tipo == "image":
                        img = mensaje.get("image", {})
                        lineas.append(f"Imagen caption: {img.get('caption', '')}")
                        lineas.append(f"Media ID: {img.get('id', '')}")

                    elif tipo == "audio":
                        audio = mensaje.get("audio", {})
                        lineas.append(f"Audio ID: {audio.get('id', '')}")

                    elif tipo == "location":
                        loc = mensaje.get("location", {})
                        lineas.append(f"Ubicación: {loc.get('latitude')}, {loc.get('longitude')}")
                        lineas.append(f"Nombre: {loc.get('name', '')}")

                    elif tipo == "reaction":
                        reaction = mensaje.get("reaction", {})
                        lineas.append(f"Reacción: {reaction.get('emoji', '')}")

                    mensajes_encontrados += 1

        if mensajes_encontrados == 0:
            return ""

        return "\n".join(lineas)

    def descargar_media(self, media_id: str, tmp_dir: str) -> str:
        """Descarga archivo media de WhatsApp Cloud API."""
        import requests

        if not self.token:
            return None

        try:
            # Obtener URL del media
            response = requests.get(
                f"{self.GRAPH_URL}/{media_id}",
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10
            )
            response.raise_for_status()
            media_url = response.json().get("url")

            if not media_url:
                return None

            # Descargar archivo
            response = requests.get(
                media_url,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=30
            )
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "")
            ext_map = {
                "application/pdf": ".pdf",
                "image/jpeg": ".jpg",
                "image/png": ".png",
                "audio/ogg": ".ogg",
            }
            ext = ext_map.get(content_type, ".bin")

            ruta = os.path.join(tmp_dir, f"wa_media_{media_id[:10]}{ext}")
            with open(ruta, "wb") as f:
                f.write(response.content)

            return ruta

        except Exception as e:
            print(f"  [WhatsApp] Error descargando media {media_id}: {e}")
            return None

    def extraer_archivos(self, payload: dict) -> list:
        """Descarga media adjunta de los mensajes de WhatsApp."""
        archivos = []
        tmp_dir = tempfile.mkdtemp()

        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                for mensaje in change.get("value", {}).get("messages", []):
                    tipo = mensaje.get("type", "")

                    media_id = None
                    if tipo == "document":
                        media_id = mensaje.get("document", {}).get("id")
                    elif tipo == "image":
                        media_id = mensaje.get("image", {}).get("id")

                    if media_id:
                        ruta = self.descargar_media(media_id, tmp_dir)
                        if ruta:
                            archivos.append(ruta)

        return archivos
