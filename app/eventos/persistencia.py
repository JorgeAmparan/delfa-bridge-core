"""
Persistencia de `:EventoOperativo` (consulta_realizada) y `:Observacion` (B2 §9).

DOCYAN LDE™ by XCID.

Multi-tenant strict: todo se escribe en el grafo del tenant vía `dkg_client`
(graph_name aislado). Estas funciones son la persistencia MÍNIMA descrita en §9;
NO implementan lógica de Playbook (eso es B7+).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.graph.dkg_client import dkg_client
from app.graph.schemas.dkg_ontology import NodeLabel

# Recorte de la respuesta que se guarda con el evento (§9.1: primeras 500 chars).
RESPUESTA_RESUMEN_MAX = 500


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def registrar_consulta_realizada(
    tenant_id: str,
    usuario_id: str | None,
    consulta_texto: str,
    respuesta_resumen: str | None = None,
    entidad_consultada_id: str | None = None,
    client=None,
) -> dict:
    """
    Persiste un `:EventoOperativo` con tipo="consulta_realizada" (§9.1).

    Placeholder funcional: se invoca al servir una consulta. La consulta real con
    clasificador completo es B8; aquí solo se asegura el registro mínimo.
    """
    client = client or dkg_client
    props = {
        "id": uuid.uuid4().hex,
        "tipo": "consulta_realizada",
        "usuario_id": usuario_id,
        "consulta_texto": consulta_texto,
        "entidad_consultada_id": entidad_consultada_id,
        "respuesta_resumen": (respuesta_resumen or "")[:RESPUESTA_RESUMEN_MAX],
        "timestamp": _now_iso(),
    }
    return client.create_node(tenant_id, NodeLabel.EVENTO_OPERATIVO.value, props)


def registrar_observacion(
    tenant_id: str,
    entidad_id: str,
    texto: str,
    autor_id: str | None = None,
    client=None,
) -> dict:
    """
    Crea un `:Observacion` y lo vincula a una entidad operativa (§9.2).

    Cubre el caso de un operador anotando algo sobre una entidad. La UI que lo
    consume es B9; aquí es persistencia funcional (no stub).
    """
    client = client or dkg_client
    obs_id = uuid.uuid4().hex
    props = {
        "id": obs_id,
        "texto": texto,
        "autor_id": autor_id,
        "timestamp": _now_iso(),
    }
    observacion = client.create_node(tenant_id, NodeLabel.OBSERVACION.value, props)

    # Arista (:EntidadOperativa)-[:TIENE_OBSERVACION]->(:Observacion). El grafo es
    # flexible; la relación se crea si la entidad existe (no falla si no, para no
    # bloquear la anotación libre sobre entidades aún no materializadas).
    client.query(
        tenant_id,
        """
        MATCH (o:Observacion {id: $obs_id})
        OPTIONAL MATCH (e:EntidadOperativa {id: $entidad_id})
        FOREACH (_ IN CASE WHEN e IS NULL THEN [] ELSE [1] END |
            MERGE (e)-[:TIENE_OBSERVACION]->(o)
        )
        RETURN o
        """,
        {"obs_id": obs_id, "entidad_id": entidad_id},
    )
    return observacion
