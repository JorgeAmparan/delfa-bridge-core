"""B1 §13 — El backend conecta a FalkorDB y responde PING. Test bloqueador."""
from tests.conftest import requires_falkordb


@requires_falkordb
def test_dkg_health_ping(dkg):
    assert dkg.health() is True


@requires_falkordb
def test_dkg_trivial_query(dkg):
    rows = dkg.query("conn_probe", "RETURN 1 AS uno")
    dkg.track("conn_probe")
    assert rows and rows[0]["uno"] == 1
