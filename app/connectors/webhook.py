from app.connectors.webhook_base import WebhookConnector

# ─── WEBHOOK GENÉRICO | Panohayan™ ──────────────────────────────────────────
#
# Recibe cualquier payload JSON o archivo desde cualquier fuente.
# Soporta HMAC-SHA256 para validación de firma.
# ─────────────────────────────────────────────────────────────────────────────


class GenericWebhookConnector(WebhookConnector):

    CONNECTOR_NAME = "webhook_generico"
    SECRET_ENV_VAR = "WEBHOOK_HMAC_SECRET"

    def extraer_contenido(self, payload: dict) -> str:
        """
        Acepta cualquier estructura JSON.
        Busca campos comunes: data, text, content, body, message.
        Si no encuentra ninguno, serializa el payload completo.
        """
        # Campos prioritarios
        for campo in ["data", "text", "content", "body", "message"]:
            valor = payload.get(campo)
            if valor:
                if isinstance(valor, str):
                    return valor
                if isinstance(valor, list):
                    return self._lista_a_texto(valor)
                if isinstance(valor, dict):
                    return self._dict_a_texto(valor)

        # Fallback: todo el payload
        return self._dict_a_texto(payload)

    def _dict_a_texto(self, datos: dict) -> str:
        lineas = ["=== WEBHOOK PAYLOAD ===\n"]
        for key, value in datos.items():
            if key in ("files", "attachments", "secret", "token"):
                continue
            if value is not None and str(value).strip():
                lineas.append(f"{key}: {value}")
        return "\n".join(lineas)

    def _lista_a_texto(self, datos: list) -> str:
        lineas = ["=== WEBHOOK PAYLOAD ===\n"]
        for item in datos:
            lineas.append("---")
            if isinstance(item, dict):
                for key, value in item.items():
                    if value is not None and str(value).strip():
                        lineas.append(f"{key}: {value}")
            else:
                lineas.append(str(item))
        return "\n".join(lineas)
