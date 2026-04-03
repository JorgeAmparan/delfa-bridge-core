from app.connectors.webhook_base import WebhookConnector

# ─── ZAPIER CONNECTOR | Panohayan™ ──────────────────────────────────────────
#
# Recibe datos desde Zaps de Zapier via webhook.
# Zapier envía payload JSON plano con los campos del trigger/action.
# ─────────────────────────────────────────────────────────────────────────────


class ZapierConnector(WebhookConnector):

    CONNECTOR_NAME = "zapier"
    SECRET_ENV_VAR = "ZAPIER_WEBHOOK_SECRET"

    def extraer_contenido(self, payload: dict) -> str:
        """
        Zapier envía payloads planos (key-value) desde el Zap.
        """
        datos = payload.get("data") or payload

        lineas = ["=== DATOS DE ZAPIER ===\n"]

        if isinstance(datos, list):
            for item in datos:
                lineas.append("---")
                if isinstance(item, dict):
                    for key, value in item.items():
                        if value is not None and str(value).strip():
                            lineas.append(f"{key}: {value}")
                else:
                    lineas.append(str(item))
        elif isinstance(datos, dict):
            for key, value in datos.items():
                if key in ("secret", "token", "webhook_secret"):
                    continue
                if value is not None and str(value).strip():
                    lineas.append(f"{key}: {value}")
        else:
            lineas.append(str(datos))

        return "\n".join(lineas)
