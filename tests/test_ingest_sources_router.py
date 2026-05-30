"""Tests del router de fuentes de ingesta documental (B0.5).

Verifican que el contrato HTTP del Modo conectado (adenda 6.1) responde
200 con los stubs, que respeta el enum de fuentes, y que las fuentes
transaccionales retiradas ya no existen.
"""

from fastapi.testclient import TestClient

from app.api.auth import verificar_credenciales
from app.api.main import app


def _override_roles():
    """Sustituye la resolución de identidad por un contexto admin de prueba.

    `requiere_rol(...)` devuelve un closure nuevo en cada llamada, por lo que
    no es sobreescribible por clave; el punto estable es `verificar_credenciales`,
    del que dependen todos los verificadores de rol.
    """

    def fake_ctx():
        return {"org_id": "test-org", "role": "admin"}

    app.dependency_overrides[verificar_credenciales] = fake_ctx


def teardown_function():
    app.dependency_overrides.clear()


class TestIngestSourcesConfigure:
    def test_configure_google_drive_returns_200(self):
        _override_roles()
        client = TestClient(app)
        r = client.post(
            "/ingest_sources/google_drive/configure",
            json={"folder_id": "abc123"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["source"] == "google_drive"
        assert body["tenant_id"] == "test-org"
        assert body["status"] == "configured"

    def test_configure_all_conserved_sources(self):
        _override_roles()
        client = TestClient(app)
        for source in ("google_drive", "onedrive", "ftp", "notion"):
            r = client.post(f"/ingest_sources/{source}/configure", json={})
            assert r.status_code == 200, f"{source} -> {r.status_code}"
            assert r.json()["source"] == source

    def test_unknown_source_rejected(self):
        _override_roles()
        client = TestClient(app)
        # 'salesforce' es una fuente transaccional retirada: no está en el enum.
        r = client.post("/ingest_sources/salesforce/configure", json={})
        assert r.status_code in (404, 422)


class TestIngestSourcesListAndIngest:
    def test_list_documents_stub(self):
        _override_roles()
        client = TestClient(app)
        r = client.post("/ingest_sources/onedrive/list_documents", json={})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "not_implemented"
        assert body["documents"] == []
        assert body["total"] == 0

    def test_ingest_document_stub(self):
        _override_roles()
        client = TestClient(app)
        r = client.post(
            "/ingest_sources/ftp/ingest_document",
            json={"external_id": "doc-1"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "not_implemented"
        assert body["external_id"] == "doc-1"
