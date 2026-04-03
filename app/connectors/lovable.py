from app.connectors.webhook_base import WebhookConnector

# ─── LOVABLE PLUGIN CONNECTOR | Panohayan™ ──────────────────────────────────
#
# Recibe datos desde apps generadas con Lovable (ex-GPT Engineer).
# Lovable apps envían JSON via fetch/axios al endpoint de Delfa.
# ─────────────────────────────────────────────────────────────────────────────


class LovableConnector(WebhookConnector):

    CONNECTOR_NAME = "lovable"
    SECRET_ENV_VAR = None  # Usa auth estándar de Delfa Bridge

    def extraer_contenido(self, payload: dict) -> str:
        """
        Lovable apps envían JSON libre desde su frontend.
        Busca campos comunes: data, content, text, records.
        """
        datos = (
            payload.get("data") or
            payload.get("content") or
            payload.get("records") or
            payload
        )

        lineas = ["=== DATOS DE LOVABLE ===\n"]

        if isinstance(datos, list):
            for item in datos:
                lineas.append("---")
                if isinstance(item, dict):
                    for key, value in item.items():
                        if key in ("api_key", "token"):
                            continue
                        if value is not None and str(value).strip():
                            lineas.append(f"{key}: {value}")
                else:
                    lineas.append(str(item))
        elif isinstance(datos, dict):
            for key, value in datos.items():
                if key in ("api_key", "token"):
                    continue
                if value is not None and str(value).strip():
                    lineas.append(f"{key}: {value}")

        return "\n".join(lineas)
