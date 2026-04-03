from app.connectors.webhook_base import WebhookConnector

# ─── CHROME EXTENSION CONNECTOR | Panohayan™ ────────────────────────────────
#
# Recibe datos capturados por la extensión de Chrome de Delfa Bridge.
# La extensión envía: texto seleccionado, HTML de página, o screenshots.
# ─────────────────────────────────────────────────────────────────────────────


class ChromeExtConnector(WebhookConnector):

    CONNECTOR_NAME = "chrome_ext"
    SECRET_ENV_VAR = None  # Usa auth estándar de Delfa Bridge (JWT)

    def extraer_contenido(self, payload: dict) -> str:
        """
        La extensión envía:
        - text: texto seleccionado por el usuario
        - html: HTML de la página o selección
        - url: URL de origen
        - title: título de la página
        """
        lineas = ["=== CAPTURA DE CHROME EXTENSION ===\n"]

        url = payload.get("url", "")
        title = payload.get("title", "")

        if url:
            lineas.append(f"URL: {url}")
        if title:
            lineas.append(f"Título: {title}")

        # Texto seleccionado (prioridad)
        texto = payload.get("text") or payload.get("content") or ""
        if texto:
            lineas.append(f"\n--- CONTENIDO ---\n{texto}")

        # HTML como fallback
        html = payload.get("html", "")
        if html and not texto:
            # Extraer texto plano del HTML básico
            import re
            texto_html = re.sub(r"<[^>]+>", " ", html)
            texto_html = re.sub(r"\s+", " ", texto_html).strip()
            if texto_html:
                lineas.append(f"\n--- CONTENIDO HTML ---\n{texto_html}")

        # Datos estructurados adicionales
        data = payload.get("data")
        if data and isinstance(data, dict):
            lineas.append("\n--- DATOS ADICIONALES ---")
            for key, value in data.items():
                if value is not None and str(value).strip():
                    lineas.append(f"{key}: {value}")

        return "\n".join(lineas)
