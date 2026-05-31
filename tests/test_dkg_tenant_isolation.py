"""
B1 §7.3 / §13 — Aislamiento estricto multi-tenant. TEST BLOQUEADOR.

Si este test falla, el sprint NO cierra (regla absoluta: tenant A nunca ve
datos de tenant B). El aislamiento es nativo por `graph_name`.
"""
from app.graph.schemas.dkg_ontology import graph_name_for
from tests.conftest import requires_falkordb


@requires_falkordb
def test_tenant_isolation(dkg):
    dkg.create_entity("tenant_A", {"token_qr": "QR-001", "tipo": "compresor"})
    dkg.create_entity("tenant_B", {"token_qr": "QR-002", "tipo": "valvula"})

    entities_A = dkg.query("tenant_A", "MATCH (e:EntidadOperativa) RETURN e")
    entities_B = dkg.query("tenant_B", "MATCH (e:EntidadOperativa) RETURN e")

    assert len(entities_A) == 1 and entities_A[0]["token_qr"] == "QR-001"
    assert len(entities_B) == 1 and entities_B[0]["token_qr"] == "QR-002"


@requires_falkordb
def test_cross_tenant_query_cannot_leak(dkg):
    """
    Una query lanzada con el scope de tenant_C jamás ve datos de tenant_D, ni
    siquiera con un MATCH que intentara abarcar 'todo'. El confinamiento es a
    nivel de grafo FalkorDB (graph_name), no un filtro de aplicación evadible.
    """
    dkg.create_entity("tenant_C", {"token_qr": "QR-C", "tipo": "x"})
    dkg.create_entity("tenant_D", {"token_qr": "QR-D", "tipo": "y"})

    all_in_C = dkg.query("tenant_C", "MATCH (n) RETURN n")
    qrs = {row.get("token_qr") for row in all_in_C}
    assert "QR-D" not in qrs
    assert qrs == {"QR-C"}

    # Los grafos son físicamente distintos.
    assert graph_name_for("tenant_C") != graph_name_for("tenant_D")


@requires_falkordb
def test_empty_tenant_returns_empty(dkg):
    dkg.track("tenant_empty")
    rows = dkg.query("tenant_empty", "MATCH (e:EntidadOperativa) RETURN e")
    assert rows == []
