"""B1 §14 — Endpoints admin de verificación de infraestructura DKG."""
import os

from tests.conftest import requires_falkordb

ADMIN_KEY = {"X-API-Key": os.environ.get("API_KEY", "test-api-key-for-pytest")}


def test_admin_requires_auth(test_client):
    assert test_client.post("/admin/tenants/test").status_code == 401
    assert test_client.post("/admin/embedding/test").status_code == 401


@requires_falkordb
def test_admin_tenants_test(test_client, dkg):
    resp = test_client.post("/admin/tenants/test", headers=ADMIN_KEY)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    dkg.track(body["tenant_id"])  # limpieza vía fixture
    assert body["ok"] is True
    assert body["graph_name"].startswith("docyan_tenant_")
    assert body["tenant"]["tenant_id"] == body["tenant_id"]


@requires_falkordb
def test_admin_dkg_health(test_client):
    resp = test_client.get("/admin/dkg/health", headers=ADMIN_KEY)
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_admin_embedding_test_contract(test_client):
    """
    Sin embedder alcanzable → 503 explícito (verdad operacional). Con embedder
    → 200 con dim=1024. Ambos son comportamientos válidos del endpoint.
    """
    resp = test_client.post("/admin/embedding/test", headers=ADMIN_KEY)
    assert resp.status_code in (200, 503)
    if resp.status_code == 200:
        body = resp.json()
        assert body["dim"] == 1024
        assert body["ok"] is True
        assert len(body["sample"]) == 5
