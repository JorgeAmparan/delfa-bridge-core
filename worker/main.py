"""
Entry point del worker de ingesta (B2 §4.1 / §8).

DOCYAN LDE™ by XCID — `docyan-lde-ingest`.

Dos responsabilidades:

  1. Servir `/health` sobre flycast (criterio de cierre §11: "ingest health 200").
     NO se expone HTTP público (fly.toml sin http_service público; solo .flycast).
  2. Consumir la cola Redis de jobs de ingesta (BLPOP), descargar el documento,
     ejecutar el pipeline (Docling → GraphRAG-SDK → BGE-M3 → dedup → finalize) y
     actualizar el estado del job.

El consumidor corre como tarea de fondo de asyncio dentro del proceso uvicorn.
Procesa un job a la vez (jobs largos y pesados; escalado horizontal = más
máquinas, no más concurrencia por máquina).
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import tempfile

from fastapi import FastAPI

from app.jobs.dispatcher import JobDispatcher, RedisQueueBackend
from worker.ingest_pipeline import IngestPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("docyan.worker")

# Tiempo de espera del BLPOP (s) antes de reintentar (permite shutdown limpio).
POP_TIMEOUT = int(os.getenv("WORKER_POP_TIMEOUT", "5"))

app = FastAPI(title="DOCYAN LDE — Ingest Worker", docs_url=None, redoc_url=None)


def _build_document_store():
    """Almacén de documentos (Supabase Storage en prod; local si se configura)."""
    if os.getenv("INGEST_STORAGE_DIR"):
        from app.ingesta.document_store import LocalDocumentStore

        return LocalDocumentStore()
    from app.ingesta.document_store import SupabaseStorageDocumentStore

    return SupabaseStorageDocumentStore()


def _build_schema_registry():
    from app.schemas_documentales.registry import SchemaRegistry

    return SchemaRegistry()


async def _procesar_un_job(dispatcher: JobDispatcher, pipeline: IngestPipeline, job_id: str):
    """Descarga, procesa y actualiza el estado de un job."""
    dispatcher.marcar_procesando(job_id)
    job = dispatcher.backend.load_job(job_id)
    if job is None:
        logger.error("job %s desapareció del estado; se omite", job_id)
        return

    tmp_path = None
    try:
        data = pipeline.document_store.get(job.documento_ref)
        suffix = os.path.splitext(job.nombre_archivo)[1] or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        resultado = await pipeline.procesar(job, tmp_path)
        dispatcher.marcar_completado(job_id, resultado)
        logger.info("job %s completado: %s", job_id, resultado)
    except Exception as exc:  # noqa: BLE001 — un job malo no debe tumbar el worker
        logger.exception("job %s falló", job_id)
        dispatcher.marcar_fallido(job_id, f"{type(exc).__name__}: {exc}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


async def _consumer_loop():
    """Loop principal del worker: BLPOP de la cola → procesar."""
    backend = RedisQueueBackend()
    dispatcher = JobDispatcher(backend=backend)
    pipeline = IngestPipeline(
        document_store=_build_document_store(),
        schema_registry=_build_schema_registry(),
    )
    logger.info("worker de ingesta iniciado; esperando jobs…")
    while True:
        try:
            job_id = await asyncio.to_thread(backend.pop, POP_TIMEOUT)
            if job_id:
                await _procesar_un_job(dispatcher, pipeline, job_id)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            logger.exception("error en el loop del consumidor; reintentando")
            await asyncio.sleep(2)


@app.on_event("startup")
async def _startup():
    # Solo arranca el consumidor si hay cola configurada (evita arrancarlo en
    # contextos de test/health-only sin Redis).
    if os.getenv("REDIS_QUEUE_URL") or os.getenv("REDIS_URL"):
        app.state.consumer = asyncio.create_task(_consumer_loop())
    else:
        logger.warning("sin REDIS_QUEUE_URL/REDIS_URL; consumidor NO iniciado")


@app.on_event("shutdown")
async def _shutdown():
    task = getattr(app.state, "consumer", None)
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


@app.get("/health")
async def health():
    """Health check sobre flycast (criterio §11). Reporta dependencias."""
    from app.graph.dkg_client import dkg_client

    falkor_ok = False
    try:
        falkor_ok = dkg_client.health()
    except Exception:  # noqa: BLE001
        falkor_ok = False

    embedder_ok = False
    try:
        from app.embeddings.bge_client import bge_client

        embedder_ok = bool(bge_client.health()) if hasattr(bge_client, "health") else None
    except Exception:  # noqa: BLE001
        embedder_ok = False

    return {
        "status": "healthy",
        "service": "docyan-lde-ingest",
        "falkordb": falkor_ok,
        "embedder": embedder_ok,
        "consumer_running": getattr(app.state, "consumer", None) is not None,
    }
