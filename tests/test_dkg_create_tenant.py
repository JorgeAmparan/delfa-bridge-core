"""B1 §13 — Crear :Tenant, leerlo, verificar propiedades. Test bloqueador."""
from app.graph.schemas.dkg_ontology import graph_name_for
from tests.conftest import requires_falkordb


@requires_falkordb
def test_create_and_read_tenant(dkg):
    tid = "t_create_tenant"
    created = dkg.create_tenant(
        tid,
        {"nombre": "ACME Labs", "tipo": "cliente_final_directo", "idiomas_activos": ["es", "en"]},
    )
    assert created["tenant_id"] == tid
    assert "id" in created  # uid generado

    read = dkg.get_tenant(tid)
    assert read is not None
    assert read["nombre"] == "ACME Labs"
    assert read["tipo"] == "cliente_final_directo"
    assert read["idiomas_activos"] == ["es", "en"]


@requires_falkordb
def test_tenant_lives_in_its_own_graph(dkg):
    tid = "t_graph_name"
    dkg.create_tenant(tid, {"nombre": "X", "tipo": "agencia_traduccion"})
    assert graph_name_for(tid) == "docyan_tenant_t_graph_name"
    assert tid in dkg.list_tenants()
