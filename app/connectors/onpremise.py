import os
import time
from app.connectors.webhook_base import WebhookConnector
from dotenv import load_dotenv

load_dotenv()


# ─── AGENTE ON-PREMISE CONNECTOR | Panohayan™ ───────────────────────────────
#
# Recibe datos enviados por un agente instalado en la red del cliente.
# El agente on-premise actúa como bridge entre sistemas internos y Delfa.
#
# Flujo:
#   1. Agente on-premise extrae datos de sistemas internos
#   2. Agente envía via POST a /connectors/onpremise/receive
#   3. Delfa procesa via DII pipeline
#   4. Agente consulta /connectors/onpremise/status para verificar
#
# Autenticación: shared secret (API Key en header X-Agent-Secret)
# ─────────────────────────────────────────────────────────────────────────────

# Registro en memoria de agentes activos (para status endpoint)
_AGENT_REGISTRY = {}


class OnPremiseConnector(WebhookConnector):

    CONNECTOR_NAME = "onpremise"
    SECRET_ENV_VAR = "ONPREMISE_SHARED_SECRET"

    def extraer_contenido(self, payload: dict) -> str:
        """
        El agente on-premise envía payloads estructurados:
        - agent_id: identificador del agente
        - source: sistema de origen (e.g. "erp_local", "bd_interna")
        - data_type: tipo de datos (e.g. "facturas", "inventario")
        - data: los datos extraídos (list o dict)
        - metadata: info adicional del agente
        """
        agent_id = payload.get("agent_id", "unknown")
        source = payload.get("source", "desconocido")
        data_type = payload.get("data_type", "datos")
        datos = payload.get("data")
        metadata = payload.get("metadata", {})

        # Registrar actividad del agente
        _AGENT_REGISTRY[agent_id] = {
            "last_seen": time.time(),
            "source": source,
            "data_type": data_type,
            "status": "processing",
            "metadata": metadata
        }

        if not datos:
            return ""

        lineas = [
            f"=== AGENTE ON-PREMISE: {agent_id} ===",
            f"Fuente: {source}",
            f"Tipo: {data_type}",
            ""
        ]

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
                if value is not None and str(value).strip():
                    lineas.append(f"{key}: {value}")

        elif isinstance(datos, str):
            lineas.append(datos)

        return "\n".join(lineas)

    def procesar(self, payload: dict, org_id: str = None) -> dict:
        """Override para actualizar registro del agente tras procesar."""
        agent_id = payload.get("agent_id", "unknown")

        resultado = super().procesar(payload, org_id=org_id)

        # Actualizar status
        if agent_id in _AGENT_REGISTRY:
            if resultado.get("errores"):
                _AGENT_REGISTRY[agent_id]["status"] = "error"
                _AGENT_REGISTRY[agent_id]["last_error"] = resultado["errores"][-1]
            else:
                _AGENT_REGISTRY[agent_id]["status"] = "ok"
                _AGENT_REGISTRY[agent_id]["last_entidades"] = resultado.get(
                    "entidades_totales", 0
                )

        return resultado

    @staticmethod
    def obtener_status(agent_id: str = None) -> dict:
        """
        Retorna status de agentes registrados.
        Si agent_id, retorna solo ese agente.
        """
        if agent_id:
            info = _AGENT_REGISTRY.get(agent_id)
            if not info:
                return {"agent_id": agent_id, "status": "unknown"}

            return {
                "agent_id": agent_id,
                "status": info.get("status", "unknown"),
                "last_seen": info.get("last_seen"),
                "seconds_ago": int(time.time() - info.get("last_seen", 0)),
                "source": info.get("source"),
                "data_type": info.get("data_type"),
                "last_entidades": info.get("last_entidades"),
                "last_error": info.get("last_error"),
                "metadata": info.get("metadata", {})
            }

        # Todos los agentes
        agentes = []
        for aid, info in _AGENT_REGISTRY.items():
            agentes.append({
                "agent_id": aid,
                "status": info.get("status", "unknown"),
                "last_seen": info.get("last_seen"),
                "seconds_ago": int(time.time() - info.get("last_seen", 0)),
                "source": info.get("source")
            })

        return {
            "agentes_registrados": len(agentes),
            "agentes": agentes
        }
