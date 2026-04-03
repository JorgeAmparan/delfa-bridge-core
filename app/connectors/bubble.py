from app.connectors.webhook_base import WebhookConnector

# ─── BUBBLE PLUGIN CONNECTOR | Panohayan™ ───────────────────────────────────
#
# Recibe datos desde apps Bubble.io via API.
# Bubble envía JSON con datos del workflow/data thing.
# ─────────────────────────────────────────────────────────────────────────────


class BubbleConnector(WebhookConnector):

    CONNECTOR_NAME = "bubble"
    SECRET_ENV_VAR = None  # Usa auth estándar de Delfa Bridge

    def extraer_contenido(self, payload: dict) -> str:
        """
        Bubble envía datos como JSON plano desde API Connector plugin.
        Campos comunes: data, text, thing, list.
        """
        datos = (
            payload.get("data") or
            payload.get("thing") or
            payload.get("list") or
            payload
        )

        lineas = ["=== DATOS DE BUBBLE ===\n"]

        if isinstance(datos, list):
            for item in datos:
                lineas.append("---")
                if isinstance(item, dict):
                    for key, value in item.items():
                        if key.startswith("_") or key in ("api_key",):
                            continue
                        if value is not None and str(value).strip():
                            lineas.append(f"{key}: {value}")
                else:
                    lineas.append(str(item))
        elif isinstance(datos, dict):
            for key, value in datos.items():
                if key.startswith("_") or key in ("api_key",):
                    continue
                if value is not None and str(value).strip():
                    lineas.append(f"{key}: {value}")

        return "\n".join(lineas)
