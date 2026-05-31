"""
Cliente DKG (Document Knowledge Graph) — fachada de dominio sobre FalkorDB.

DOCYAN LDE™ by XCID — B1 §5 / §7.

Reemplaza al skeleton `falkor_client.py`. Ya no hablamos de "Falkor", hablamos
del DKG. La fachada:

  - Es **multi-tenant estricta** (B1 §7, regla absoluta): cada método público
    recibe `tenant_id` como primer argumento y opera SOLO sobre el grafo lógico
    aislado `docyan_tenant_<id>`. No existe forma de hacer una query cruzada
    entre tenants desde la API pública. Las únicas operaciones sin `tenant_id`
    son administrativas explícitas (`list_tenants`, `health`).
  - Valida los nodos contra la ontología (`dkg_ontology`) antes de escribir.
  - Maneja pool de conexión, retry con tenacity y timeout configurable.
  - Loguea queries de forma estructurada SIN valores sensibles (solo el Cypher
    y el grafo destino, nunca los `params`).

Decisión de librería (B1 §5.1): se usa el cliente oficial `falkordb` (FalkorDB
1.6.1, arrastrado por graphrag-sdk 1.1.1). Es el mismo cliente que usa el SDK
internamente (`FalkorDBConnection`), así backend y worker de ingesta comparten
driver y semántica de `graph_name` — sin un segundo cliente redis-py paralelo
que pueda divergir.
"""
from __future__ import annotations

import logging
import os
import uuid

from dotenv import load_dotenv
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.graph.schemas.dkg_ontology import (
    GRAPH_NAME_PREFIX,
    NodeLabel,
    graph_name_for,
    validate_node,
)

load_dotenv()

logger = logging.getLogger("docyan.dkg")

# FALKOR_HOST/PORT son las variables canónicas B1 (secrets en Fly apuntan al
# proceso docyan-lde-graph). FALKORDB_HOST/PORT se aceptan como alias (B0).
FALKOR_HOST = os.getenv("FALKOR_HOST") or os.getenv("FALKORDB_HOST", "localhost")
FALKOR_PORT = int(os.getenv("FALKOR_PORT") or os.getenv("FALKORDB_PORT", "6379"))
FALKOR_QUERY_TIMEOUT_MS = int(os.getenv("FALKOR_QUERY_TIMEOUT_MS", "10000"))


class CrossTenantError(Exception):
    """Se intentó una operación que violaría el aislamiento entre tenants."""


class DKGClient:
    """Fachada multi-tenant del Document Knowledge Graph sobre FalkorDB."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        query_timeout_ms: int | None = None,
    ):
        self.host = host or FALKOR_HOST
        self.port = port or FALKOR_PORT
        self.query_timeout_ms = query_timeout_ms or FALKOR_QUERY_TIMEOUT_MS
        self._db = None  # instancia FalkorDB (pool interno redis)

    # ── Conexión ─────────────────────────────────────────────────────────────

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.2, max=2),
        retry=retry_if_exception_type(Exception),
    )
    def _connect(self):
        if self._db is None:
            from falkordb import FalkorDB

            self._db = FalkorDB(host=self.host, port=self.port)
        return self._db

    def _graph(self, tenant_id: str):
        """Selecciona el grafo aislado del tenant. Único punto de resolución."""
        graph_name = graph_name_for(tenant_id)  # valida tenant_id no vacío
        return self._connect().select_graph(graph_name)

    def health(self) -> bool:
        """PING al FalkorDB (operación administrativa, sin tenant)."""
        try:
            db = self._connect()
            # Una query trivial sobre un grafo de sondeo confirma el módulo graph.
            db.select_graph("__docyan_health__").query("RETURN 1")
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("DKG health check falló: %s", type(exc).__name__)
            return False

    # ── Helpers internos ──────────────────────────────────────────────────────

    @staticmethod
    def _node_to_dict(node) -> dict:
        """Aplana un nodo FalkorDB a dict de propiedades + id interno."""
        props = dict(getattr(node, "properties", {}) or {})
        props.setdefault("_internal_id", getattr(node, "id", None))
        return props

    def _records(self, result) -> list[dict]:
        """
        Normaliza un result_set a lista de dicts.

        - Fila con UNA sola columna que es nodo → se devuelven sus propiedades
          (permite `rows[0]["token_qr"]`, como espera el test de aislamiento).
        - Fila con varias columnas → dict {alias: valor} (nodos aplanados).
        """
        header = [h[1] if isinstance(h, (list, tuple)) else h for h in (result.header or [])]
        rows: list[dict] = []
        for record in result.result_set:
            values = [self._maybe_node(v) for v in record]
            if len(values) == 1 and isinstance(values[0], dict):
                rows.append(values[0])
            else:
                rows.append({header[i] if i < len(header) else f"col{i}": values[i]
                             for i in range(len(values))})
        return rows

    def _maybe_node(self, value):
        # Los nodos de falkordb exponen .properties; los escalares se devuelven igual.
        if hasattr(value, "properties"):
            return self._node_to_dict(value)
        return value

    # ── Query genérica (multi-tenant) ──────────────────────────────────────────

    def query(self, tenant_id: str, cypher: str, params: dict | None = None) -> list[dict]:
        """
        Ejecuta Cypher SOBRE EL GRAFO DEL TENANT. No hay forma de salir de ese
        grafo: `select_graph(graph_name)` confina el alcance a nivel FalkorDB.
        """
        graph = self._graph(tenant_id)
        logger.info(
            "DKG query | graph=%s%s | cypher=%s",
            GRAPH_NAME_PREFIX,
            tenant_id,
            cypher.strip().split("\n")[0][:200],
        )  # NO se loguean params (pueden traer valores sensibles).
        result = graph.query(cypher, params=params or {}, timeout=self.query_timeout_ms)
        return self._records(result)

    # ── Operaciones de dominio ─────────────────────────────────────────────────

    def _create_node(self, tenant_id: str, label: str, props: dict) -> dict:
        validated = validate_node(label, props)
        if "id" not in validated:
            validated["id"] = uuid.uuid4().hex
        graph = self._graph(tenant_id)
        result = graph.query(
            f"CREATE (n:{label}) SET n = $props RETURN n",
            params={"props": validated},
            timeout=self.query_timeout_ms,
        )
        logger.info("DKG create | graph=%s%s | label=%s", GRAPH_NAME_PREFIX, tenant_id, label)
        return self._node_to_dict(result.result_set[0][0])

    def create_tenant(self, tenant_id: str, props: dict | None = None) -> dict:
        """Crea (o asegura) el nodo `:Tenant` dentro del grafo del propio tenant."""
        data = dict(props or {})
        data.setdefault("tenant_id", tenant_id)
        data.setdefault("nombre", data.get("nombre", tenant_id))
        data.setdefault("tipo", data.get("tipo", "cliente_final_directo"))
        return self._create_node(tenant_id, NodeLabel.TENANT.value, data)

    def get_tenant(self, tenant_id: str) -> dict | None:
        rows = self.query(
            tenant_id,
            "MATCH (t:Tenant {tenant_id: $tid}) RETURN t",
            {"tid": tenant_id},
        )
        return rows[0] if rows else None

    def create_entity(self, tenant_id: str, entity_data: dict) -> dict:
        """Crea una `:EntidadOperativa` validada contra la ontología."""
        return self._create_node(tenant_id, NodeLabel.ENTIDAD_OPERATIVA.value, entity_data)

    def create_node(self, tenant_id: str, label: str, props: dict) -> dict:
        """Crea un nodo de cualquier etiqueta válida de la ontología."""
        return self._create_node(tenant_id, label, props)

    def get_entity(self, tenant_id: str, node_id: str) -> dict | None:
        return self.get_node(tenant_id, NodeLabel.ENTIDAD_OPERATIVA.value, node_id)

    def get_node(self, tenant_id: str, label: str, node_id: str) -> dict | None:
        rows = self.query(
            tenant_id,
            f"MATCH (n:{label} {{id: $id}}) RETURN n",
            {"id": node_id},
        )
        return rows[0] if rows else None

    def update_entity(self, tenant_id: str, node_id: str, updates: dict) -> dict | None:
        return self.update_node(tenant_id, NodeLabel.ENTIDAD_OPERATIVA.value, node_id, updates)

    def update_node(self, tenant_id: str, label: str, node_id: str, updates: dict) -> dict | None:
        """Actualiza propiedades in-place (sin versionar — eso lo hace versioning.py)."""
        clean = {k: v for k, v in updates.items() if k != "id"}
        graph = self._graph(tenant_id)
        result = graph.query(
            f"MATCH (n:{label} {{id: $id}}) SET n += $updates RETURN n",
            params={"id": node_id, "updates": clean},
            timeout=self.query_timeout_ms,
        )
        if not result.result_set:
            return None
        return self._node_to_dict(result.result_set[0][0])

    # ── Versionado in-place (B1 §8 — delega en app/graph/versioning.py) ─────────

    def version_node(
        self,
        tenant_id: str,
        node_id: str,
        updates: dict,
        label: str = NodeLabel.ENTIDAD_OPERATIVA.value,
    ) -> dict:
        from app.graph import versioning

        return versioning.version_node(self, tenant_id, node_id, updates, label)

    def get_versions(
        self,
        tenant_id: str,
        node_id: str,
        label: str = NodeLabel.ENTIDAD_OPERATIVA.value,
    ) -> list[dict]:
        from app.graph import versioning

        return versioning.get_versions(self, tenant_id, node_id, label)

    # ── Operaciones administrativas (sin tenant) ───────────────────────────────

    def list_tenants(self) -> list[str]:
        """
        Lista los tenants existentes inspeccionando los nombres de grafo de la
        instancia FalkorDB. Operación administrativa (no scopeada a un tenant).
        """
        db = self._connect()
        graphs = db.list_graphs()
        return sorted(
            g[len(GRAPH_NAME_PREFIX):]
            for g in graphs
            if isinstance(g, str) and g.startswith(GRAPH_NAME_PREFIX)
        )

    def drop_tenant_graph(self, tenant_id: str) -> bool:
        """Elimina por completo el grafo de un tenant (admin / cleanup de tests)."""
        try:
            self._graph(tenant_id).delete()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("drop_tenant_graph(%s) falló: %s", tenant_id, type(exc).__name__)
            return False


# Singleton de módulo (mismo patrón que bge_client).
dkg_client = DKGClient()
