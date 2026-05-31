import os

import pytest

os.environ.setdefault("JWT_SECRET", "test-secret-for-pytest-min-32-bytes-long-0000")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "fake-key")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "fake-service-key")
os.environ.setdefault("GEMINI_API_KEY", "fake-key")
os.environ.setdefault("BGE_M3_URL", "http://localhost:8080")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("FALKORDB_HOST", "localhost")
os.environ.setdefault("ORG_ID", "test-org")
os.environ.setdefault("API_KEY", "test-api-key-for-pytest")


@pytest.fixture
def test_client():
    from fastapi.testclient import TestClient

    from app.api.main import app
    return TestClient(app)


# ── DKG / FalkorDB (B1) ──────────────────────────────────────────────────────


def falkordb_available() -> bool:
    """True si hay un FalkorDB alcanzable con el módulo graph (no solo Redis)."""
    try:
        from app.graph.dkg_client import DKGClient

        return DKGClient().health()
    except Exception:
        return False


requires_falkordb = pytest.mark.skipif(
    not falkordb_available(),
    reason="FalkorDB (docyan-lde-graph) no disponible en este entorno.",
)


@pytest.fixture
def dkg():
    """
    Cliente DKG contra el FalkorDB del entorno, con limpieza automática de los
    grafos de tenant que el test cree (rastrea cualquier tenant tocado por
    create_tenant / _create_node). Para tenants creados por otra vía usar
    `dkg.track(tid)`.
    """
    from app.graph.dkg_client import DKGClient

    client = DKGClient()
    created: set[str] = set()

    _orig_create_tenant = client.create_tenant
    _orig_create_node = client._create_node

    def _tracked_create_tenant(tenant_id, props=None):
        created.add(tenant_id)
        return _orig_create_tenant(tenant_id, props)

    def _tracked_create_node(tenant_id, label, props):
        created.add(tenant_id)
        return _orig_create_node(tenant_id, label, props)

    client.create_tenant = _tracked_create_tenant  # type: ignore[method-assign]
    client._create_node = _tracked_create_node  # type: ignore[method-assign]
    client.track = lambda tid: created.add(tid)  # type: ignore[attr-defined]

    try:
        yield client
    finally:
        for tid in created:
            try:
                client.drop_tenant_graph(tid)
            except Exception:
                pass
