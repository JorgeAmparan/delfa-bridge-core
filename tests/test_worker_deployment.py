"""
B2 §10 — test bloqueador: el worker arranca, expone /health y (donde haya
servicios) conecta a FalkorDB y al embedder.

Dos capas:
  - El health endpoint del worker responde 200 siempre (sin Redis no arranca el
    consumidor, pero el servicio vive — criterio §11 "ingest health 200").
  - Las verificaciones de conexión real a FalkorDB/embedder se SKIPEAN si no hay
    servicios alcanzables (no se reportan verdes falsos).
"""
import os

import pytest

pytest.importorskip("graphrag_sdk")


@pytest.fixture
def worker_client():
    # Sin REDIS_QUEUE_URL/REDIS_URL el startup NO arranca el consumidor (correcto
    # para un test de health). Aseguramos que no estén para no colgar el test.
    os.environ.pop("REDIS_QUEUE_URL", None)
    prev_redis = os.environ.pop("REDIS_URL", None)
    from fastapi.testclient import TestClient

    from worker.main import app

    try:
        with TestClient(app) as client:
            yield client
    finally:
        if prev_redis is not None:
            os.environ["REDIS_URL"] = prev_redis


def test_worker_health_responde_200(worker_client):
    r = worker_client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "docyan-lde-ingest"
    assert body["status"] == "healthy"
    # Sin Redis el consumidor no arranca (esperado en este test).
    assert body["consumer_running"] is False


def test_worker_pipeline_y_llm_config_importan():
    from worker import llm_config

    assert llm_config.LLM_CONFIG["extraction_model"] == "gemini/gemini-2.5-flash"
    assert llm_config.LLM_CONFIG["resolution_model"] == "gemini/gemini-2.5-flash"
    assert llm_config.LLM_CONFIG["qa_model"] == "gpt-4o-mini"
    assert llm_config.LLM_CONFIG["deduplicate_fuzzy"] is True
    # El pipeline puede construir el schema SDK del catálogo.
    from app.schemas_documentales.catalogo import CATALOGO

    gs = CATALOGO["manual_tecnico"].to_sdk_schema()
    assert {e.label for e in gs.entities} >= {"Procedimiento", "Paso", "Advertencia"}


def _falkordb_available() -> bool:
    try:
        from app.graph.dkg_client import DKGClient

        return DKGClient().health()
    except Exception:
        return False


@pytest.mark.skipif(not _falkordb_available(), reason="FalkorDB no alcanzable")
def test_worker_conecta_falkordb(worker_client):
    body = worker_client.get("/health").json()
    assert body["falkordb"] is True
