"""B1 §8.2 / §13 — Versionado in-place con :VERSION_HISTORICA. Test bloqueador."""
from app.graph.versioning import is_versioned
from tests.conftest import requires_falkordb


@requires_falkordb
def test_versioning_creates_history(dkg):
    entity = dkg.create_entity("tenant_X", {"token_qr": "QR-100", "estado": "activo"})
    dkg.version_node("tenant_X", entity["id"], {"estado": "mantenimiento"})

    current = dkg.get_entity("tenant_X", entity["id"])
    history = dkg.get_versions("tenant_X", entity["id"])

    assert current["estado"] == "mantenimiento"
    assert len(history) == 1
    assert history[0]["estado"] == "activo"
    assert "timestamp" in history[0]


@requires_falkordb
def test_versioning_keeps_live_node_unique(dkg):
    """La versión histórica NO contamina las consultas de dominio."""
    ent = dkg.create_entity("tenant_Xv", {"token_qr": "QR-200", "estado": "v1"})
    dkg.version_node("tenant_Xv", ent["id"], {"estado": "v2"})
    dkg.version_node("tenant_Xv", ent["id"], {"estado": "v3"})

    live = dkg.query("tenant_Xv", "MATCH (e:EntidadOperativa) RETURN e")
    assert len(live) == 1 and live[0]["estado"] == "v3"

    history = dkg.get_versions("tenant_Xv", ent["id"])
    assert [h["estado"] for h in history] == ["v1", "v2"]  # ordenado por timestamp


def test_versioning_policy_defaults():
    """Decisión #11: documentos/procedimientos/entidades ON; término individual OFF."""
    assert is_versioned("DocumentoSource") is True
    assert is_versioned("EntidadOperativa") is True
    assert is_versioned("Procedimiento") is True
    assert is_versioned("TerminoTecnico") is False
