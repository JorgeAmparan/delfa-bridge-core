"""
Versionado in-place del DKG — DOCYAN LDE™ by XCID.

B1 §8 / decisión #11. Versionado "in-place con aristas `:VERSION_HISTORICA`":
el nodo vivo conserva su `id` estable; cada cambio versionado deja una COPIA
inmutable del estado anterior como nodo `:VersionAnterior`, enlazada desde el
nodo vivo por una arista `:VERSION_HISTORICA` con `timestamp`.

Por qué la copia se etiqueta SOLO `:VersionAnterior` (y no además su etiqueta
original): así `MATCH (e:EntidadOperativa)` sigue devolviendo únicamente los
nodos vivos — las versiones históricas no contaminan las consultas de dominio.
La etiqueta original se preserva en la propiedad `version_label`.

Política default on/off por etiqueta vive en `dkg_ontology.versioning_enabled_for`.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.graph.schemas.dkg_ontology import NodeLabel, versioning_enabled_for


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def version_node(
    client,
    tenant_id: str,
    node_id: str,
    updates: dict,
    label: str = NodeLabel.ENTIDAD_OPERATIVA.value,
) -> dict:
    """
    Versiona un nodo in-place dentro del grafo del tenant.

    Pasos (B1 §8.1):
      1. Lee el nodo vivo actual.
      2. Crea una copia `:VersionAnterior` con el estado actual (id propio,
         flag `es_version_historica`, `version_of`, `version_label`, `timestamp`).
      3. Conecta vivo → histórico con arista `:VERSION_HISTORICA {timestamp}`.
      4. Aplica `updates` al nodo vivo (conserva su `id`).
      5. Devuelve `{"current": <nodo actualizado>, "version_id": <id histórico>}`.

    Lanza ValueError si el nodo no existe.
    """
    graph = client._graph(tenant_id)
    timeout = client.query_timeout_ms

    current = client.get_node(tenant_id, label, node_id)
    if current is None:
        raise ValueError(f"Nodo {label}{{id={node_id}}} no existe en tenant '{tenant_id}'.")

    ts = _now_iso()
    snapshot = {k: v for k, v in current.items() if not k.startswith("_")}
    snapshot.update(
        {
            "id": uuid.uuid4().hex,
            "es_version_historica": True,
            "version_of": node_id,
            "version_label": label,
            "timestamp": ts,
        }
    )

    clean_updates = {k: v for k, v in updates.items() if k != "id"}

    # Crea histórico, enlaza con arista timestamped, y aplica updates en una query.
    res = graph.query(
        f"""
        MATCH (live:{label} {{id: $node_id}})
        CREATE (hist:VersionAnterior)
        SET hist = $snapshot
        CREATE (live)-[:VERSION_HISTORICA {{timestamp: $ts}}]->(hist)
        SET live += $updates
        RETURN live, hist.id
        """,
        params={
            "node_id": node_id,
            "snapshot": snapshot,
            "ts": ts,
            "updates": clean_updates,
        },
        timeout=timeout,
    )
    row = res.result_set[0]
    return {
        "current": client._node_to_dict(row[0]),
        "version_id": row[1],
    }


def get_versions(
    client,
    tenant_id: str,
    node_id: str,
    label: str = NodeLabel.ENTIDAD_OPERATIVA.value,
) -> list[dict]:
    """
    Devuelve el historial de versiones de un nodo, de más antigua a más reciente.
    Cada elemento es el dict de propiedades del estado histórico (incluye
    `timestamp`, `version_label` y las propiedades de aquel momento).
    """
    return client.query(
        tenant_id,
        f"""
        MATCH (live:{label} {{id: $node_id}})-[r:VERSION_HISTORICA]->(hist:VersionAnterior)
        RETURN hist ORDER BY hist.timestamp ASC
        """,
        {"node_id": node_id},
    )


def is_versioned(label: str) -> bool:
    """Reexporta la política default por etiqueta (decisión #11)."""
    return versioning_enabled_for(label)
