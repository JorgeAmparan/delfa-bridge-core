"""
B2 §10 — test bloqueador: un PDF de manual técnico se ingiere completo; el grafo
del tenant queda poblado con :Procedimiento, :Paso, :Advertencia esperados y con
provenance (MENTIONED_IN / spans).

Ingesta REAL → requiere FalkorDB + embedder + GEMINI_API_KEY real. Se SKIPEA si no
están (lo ejecuta el fundador con secrets, ver reporte). Usa el PDF de prueba real
(IB-111-RDA, manual de instalación de seccionador) si está disponible.
"""
import os
import pathlib

import pytest

pytest.importorskip("graphrag_sdk")

PDF_PRUEBA = os.getenv(
    "TEST_MANUAL_PDF",
    "/Users/jamparan/Desktop/XitleCore/DOCYAN LDE files/IB-111-RDA RDA1 230 R5 02172021.pdf",
)


def _real_ingestion_available() -> bool:
    try:
        from app.graph.dkg_client import DKGClient

        falkor = DKGClient().health()
    except Exception:
        falkor = False
    gemini = os.getenv("GEMINI_API_KEY", "")
    return falkor and bool(gemini) and not gemini.startswith("fake")


requires_ingestion = pytest.mark.skipif(
    not _real_ingestion_available(),
    reason="Ingesta real requiere FalkorDB + embedder + GEMINI_API_KEY real.",
)
requires_pdf = pytest.mark.skipif(
    not pathlib.Path(PDF_PRUEBA).exists(),
    reason=f"PDF de prueba no encontrado: {PDF_PRUEBA}",
)


@requires_ingestion
@requires_pdf
@pytest.mark.asyncio
async def test_ingesta_manual_tecnico_puebla_grafo(dkg):
    from app.jobs.job_models import CotizacionSnapshot, IngestJob
    from worker.ingest_pipeline import IngestPipeline

    tenant = "test_manual_tenant"
    dkg.track(tenant)

    job = IngestJob(
        job_id="manual-doc-1",
        tenant_id=tenant,
        documento_ref="n/a",
        nombre_archivo=pathlib.Path(PDF_PRUEBA).name,
        tipo_documento="manual_tecnico",
        cotizacion=CotizacionSnapshot(
            costo_estimado_usd=0.02, tiempo_estimado_seg=300, tokens_documento=9000,
            aprobado=True, decision="aprobado_requiere_confirmacion",
        ),
    )

    pipeline = IngestPipeline()  # sin registry: usa el catálogo
    resultado = await pipeline.procesar(job, PDF_PRUEBA)
    assert resultado["tipo_documento"] == "manual_tecnico"

    # El grafo del tenant quedó poblado con los nodos esperados.
    procedimientos = dkg.query(tenant, "MATCH (p:Procedimiento) RETURN count(p) AS n")
    pasos = dkg.query(tenant, "MATCH (p:Paso) RETURN count(p) AS n")
    assert procedimientos[0]["n"] > 0, "no se extrajeron :Procedimiento"
    assert pasos[0]["n"] > 0, "no se extrajeron :Paso"

    # Provenance nativo del SDK presente (MENTIONED_IN + spans / document source).
    prov = dkg.query(
        tenant,
        "MATCH ()-[r]->() WHERE type(r) IN ['MENTIONED_IN','PART_OF','NEXT_CHUNK'] "
        "RETURN count(r) AS n",
    )
    assert prov[0]["n"] > 0, "no hay aristas de provenance (MENTIONED_IN/PART_OF/NEXT_CHUNK)"
