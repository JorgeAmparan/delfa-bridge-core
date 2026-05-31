"""
B2 §10 — test bloqueador: un documento MSDS se ingiere con schema MSDS; el grafo
queda poblado con :Sustancia, :Riesgo, :MedidaProteccion.

Ingesta REAL → requiere FalkorDB + embedder + GEMINI_API_KEY real. Se SKIPEA si no
están. Como el corpus de prueba no incluye un PDF MSDS, se usa un texto MSDS
sintético representativo (la extracción y el grafo se ejercitan igual; lo que se
valida es que el schema MSDS extrae sus entidades, no el parseo de un PDF puntual).
"""
import os

import pytest

pytest.importorskip("graphrag_sdk")

MSDS_SINTETICO = """
# Hoja de Datos de Seguridad — Acetona

Sección 1. Identificación: Acetona. Número CAS 67-64-1.

Sección 2. Identificación de peligros:
- Líquido y vapores muy inflamables (GHS02).
- Provoca irritación ocular grave (GHS07).

Sección 4. Primeros auxilios:
- En caso de contacto con los ojos, enjuagar con agua durante 15 minutos.
- En caso de inhalación, trasladar a la víctima al aire libre.

Sección 8. Controles de exposición / protección personal:
- Usar gafas de seguridad y guantes de nitrilo.
- Ventilación adecuada; respirador con cartucho para vapores orgánicos.
"""


def _real_ingestion_available() -> bool:
    try:
        from app.graph.dkg_client import DKGClient

        falkor = DKGClient().health()
    except Exception:
        falkor = False
    gemini = os.getenv("GEMINI_API_KEY", "")
    return falkor and bool(gemini) and not gemini.startswith("fake")


@pytest.mark.skipif(
    not _real_ingestion_available(),
    reason="Ingesta real requiere FalkorDB + embedder + GEMINI_API_KEY real.",
)
@pytest.mark.asyncio
async def test_ingesta_msds_puebla_grafo(dkg):
    from graphrag_sdk import ConnectionConfig, GraphRAG

    from app.graph.embedder_adapter import BGE_M3_DIMENSION, make_bge_m3_adapter
    from app.graph.schemas.dkg_ontology import graph_name_for
    from app.schemas_documentales.catalogo import CATALOGO
    from worker import llm_config

    tenant = "test_msds_tenant"
    dkg.track(tenant)

    graphrag = GraphRAG(
        connection=ConnectionConfig(graph_name=graph_name_for(tenant)),
        llm=llm_config.build_extraction_llm(),
        embedder=make_bge_m3_adapter(),
        schema=CATALOGO["msds"].to_sdk_schema(),
        embedding_dimension=BGE_M3_DIMENSION,
    )
    try:
        await graphrag.ingest(text=MSDS_SINTETICO, document_id="msds-acetona")
        await graphrag.deduplicate_entities(fuzzy=True)
        await graphrag.finalize()
    finally:
        graphrag.close()

    sustancias = dkg.query(tenant, "MATCH (s:Sustancia) RETURN count(s) AS n")
    riesgos = dkg.query(tenant, "MATCH (r:Riesgo) RETURN count(r) AS n")
    medidas = dkg.query(tenant, "MATCH (m:MedidaProteccion) RETURN count(m) AS n")
    assert sustancias[0]["n"] > 0, "no se extrajeron :Sustancia"
    assert riesgos[0]["n"] > 0, "no se extrajeron :Riesgo"
    assert medidas[0]["n"] > 0, "no se extrajeron :MedidaProteccion"
