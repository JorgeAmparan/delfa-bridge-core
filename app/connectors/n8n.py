from app.connectors.webhook_base import WebhookConnector

# ─── N8N CONNECTOR | Panohayan™ ─────────────────────────────────────────────
#
# Recibe datos desde workflows de n8n via webhook.
# n8n envía JSON con estructura de items/nodes.
# ─────────────────────────────────────────────────────────────────────────────


class N8nConnector(WebhookConnector):

    CONNECTOR_NAME = "n8n"
    SECRET_ENV_VAR = "N8N_WEBHOOK_SECRET"

    def extraer_contenido(self, payload: dict) -> str:
        """
        n8n envía payloads con items[] o data directamente.
        """
        # n8n workflow output
        datos = (
            payload.get("items") or
            payload.get("data") or
            payload.get("json") or
            payload
        )

        lineas = ["=== DATOS DE N8N ===\n"]

        if isinstance(datos, list):
            for item in datos:
                lineas.append("---")
                # n8n items tienen estructura {json: {campos...}}
                campos = item.get("json", item) if isinstance(item, dict) else item
                if isinstance(campos, dict):
                    for key, value in campos.items():
                        if value is not None and str(value).strip():
                            lineas.append(f"{key}: {value}")
                else:
                    lineas.append(str(campos))
        elif isinstance(datos, dict):
            for key, value in datos.items():
                if key in ("secret", "token", "headerAuth"):
                    continue
                if value is not None and str(value).strip():
                    lineas.append(f"{key}: {value}")
        else:
            lineas.append(str(datos))

        return "\n".join(lineas)
