from app.connectors.webhook_base import WebhookConnector

# ─── MAKE (INTEGROMAT) CONNECTOR | Panohayan™ ───────────────────────────────
#
# Recibe datos desde escenarios de Make via webhook.
# Make envía payload JSON con la estructura del escenario.
# ─────────────────────────────────────────────────────────────────────────────


class MakeConnector(WebhookConnector):

    CONNECTOR_NAME = "make"
    SECRET_ENV_VAR = "MAKE_WEBHOOK_SECRET"

    def extraer_contenido(self, payload: dict) -> str:
        """
        Make envía payloads con estructura variable según el escenario.
        Campos comunes: data, output, result, bundles.
        """
        # Make scenario output
        datos = (
            payload.get("data") or
            payload.get("output") or
            payload.get("result") or
            payload.get("bundles") or
            payload
        )

        if isinstance(datos, list):
            lineas = ["=== DATOS DE MAKE (INTEGROMAT) ===\n"]
            for item in datos:
                lineas.append("---")
                if isinstance(item, dict):
                    for key, value in item.items():
                        if value is not None and str(value).strip():
                            lineas.append(f"{key}: {value}")
                else:
                    lineas.append(str(item))
            return "\n".join(lineas)

        if isinstance(datos, dict):
            lineas = ["=== DATOS DE MAKE (INTEGROMAT) ===\n"]
            for key, value in datos.items():
                if key in ("secret", "token", "webhook_secret"):
                    continue
                if value is not None and str(value).strip():
                    lineas.append(f"{key}: {value}")
            return "\n".join(lineas)

        return str(datos) if datos else ""
