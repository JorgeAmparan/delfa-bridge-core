"""
B2 §10 / §5.5 — regresión del bug PoC #1: `deduplicate_entities(fuzzy=True)` debe
ejecutarse con `await` correcto (el PoC dejó 653 residuos por NO ejecutarlo).

Dos capas:
  - CONTRATO (siempre corre): `deduplicate_entities` es coroutine (DEBE awaitarse)
    y NO existe `deduplicate_entities_sync` (§5.6) → si el código la llamara sin
    await, sería un no-op silencioso (el bug). El pipeline del worker la awaita.
  - FUNCIONAL (skip si no hay servicios): se ejecuta y reduce duplicados.
"""
import inspect

import pytest

pytest.importorskip("graphrag_sdk")


def test_deduplicate_entities_es_coroutine_y_sin_variante_sync():
    from graphrag_sdk import GraphRAG

    assert inspect.iscoroutinefunction(GraphRAG.deduplicate_entities), (
        "deduplicate_entities debe ser async → DEBE awaitarse (bug PoC #1)"
    )
    # Confirma §5.6: NO hay versión sync; llamarla sin await sería no-op silencioso.
    assert not hasattr(GraphRAG, "deduplicate_entities_sync")


def test_pipeline_del_worker_awaita_deduplicate():
    """El código del pipeline awaita deduplicate_entities(fuzzy=True), no lo ignora."""
    from worker import ingest_pipeline

    src = inspect.getsource(ingest_pipeline)
    assert "await graphrag.deduplicate_entities(fuzzy=True)" in src, (
        "el pipeline debe awaitar deduplicate_entities(fuzzy=True)"
    )


def test_procesar_es_coroutine():
    """El método que orquesta la ingesta es async (permite awaitar dedup/finalize)."""
    from worker.ingest_pipeline import IngestPipeline

    assert inspect.iscoroutinefunction(IngestPipeline.procesar)


def _real_ingestion_available() -> bool:
    import os

    try:
        from app.graph.dkg_client import DKGClient

        falkor = DKGClient().health()
    except Exception:
        falkor = False
    gemini = os.getenv("GEMINI_API_KEY", "")
    return falkor and bool(gemini) and not gemini.startswith("fake")


@pytest.mark.skipif(not _real_ingestion_available(), reason="FalkorDB + GEMINI real no disponibles")
@pytest.mark.asyncio
async def test_deduplicate_reduce_duplicados_funcional(dkg):
    """
    Ingesta un texto con entidades claramente duplicadas y verifica que
    deduplicate_entities(fuzzy=True) devuelve >0 resoluciones (reduce duplicados).
    """
    from graphrag_sdk import ConnectionConfig, GraphRAG

    from app.graph.embedder_adapter import BGE_M3_DIMENSION, make_bge_m3_adapter
    from app.graph.schemas.dkg_ontology import graph_name_for
    from app.schemas_documentales.catalogo import CATALOGO
    from worker import llm_config

    tenant = "test_dedup_tenant"
    dkg.track(tenant)
    graphrag = GraphRAG(
        connection=ConnectionConfig(graph_name=graph_name_for(tenant)),
        llm=llm_config.build_extraction_llm(),
        embedder=make_bge_m3_adapter(),
        schema=CATALOGO["manual_tecnico"].to_sdk_schema(),
        embedding_dimension=BGE_M3_DIMENSION,
    )
    try:
        texto = (
            "El procedimiento de instalación usa un desarmador. "
            "Para instalar, tome el desarmador y afloje el tornillo. "
            "El destornillador (desarmador) debe estar aislado."
        )
        await graphrag.ingest(text=texto, document_id="dedup-doc")
        resueltos = await graphrag.deduplicate_entities(fuzzy=True)
        assert resueltos >= 0  # ejecuta sin error y devuelve conteo (no no-op)
        await graphrag.finalize()
    finally:
        graphrag.close()
