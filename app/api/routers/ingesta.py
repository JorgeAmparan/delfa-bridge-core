"""
Router de ingesta manual (B2 §8.3).

DOCYAN LDE™ by XCID.

Flujo del gate (cotizador sin bypass, CLAUDE.md §14):

  POST /ingesta/documents
      → mide tokens, selecciona schema, cotiza, crea job.
      → si RECHAZADO (saldo/hard cap): job 'rejected', responde la cotización.
      → si APROBADO: job 'pending_confirmation', responde estimación + job_id.
        NO se encola nada todavía.

  POST /ingesta/documents/{job_id}/confirm
      → solo si el job es confirmable (aprobado y pendiente): encola al worker.

  GET  /ingesta/documents/{job_id}
      → estado del job (aislado por tenant).

Separado del router `ingest_sources` (B0.5, modo conectado — stubs, NO activo en
B2). El activo en B2 es el modo manual (usuario sube archivo).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.auth import requiere_rol
from app.ingesta import providers
from app.ingesta.text_extract import extraer_texto
from app.jobs.job_models import CotizacionSnapshot, IngestJob, JobStatus

router = APIRouter(prefix="/ingesta", tags=["ingesta"])


@router.post("/documents")
async def cotizar_documento(
    file: UploadFile = File(...),
    tipo_forzado: str | None = Form(default=None),
    ctx: dict = Depends(requiere_rol("admin", "editor")),
):
    """
    Cotiza un documento (gate financiero) y crea el job. NO ingiere: devuelve la
    estimación + job_id pendiente de confirmación, o el rechazo con motivo.
    """
    tenant_id = ctx["org_id"]
    data = await file.read()

    texto, confiable = extraer_texto(data, file.filename)

    # Clasificación SOLO heurística en el backend (sin generación dinámica: esa usa
    # litellm/Gemini y vive en el worker, para mantener el backend <1 GB y sin
    # litellm). Si no hay match de catálogo, el tipo queda tentativo y el worker
    # resuelve/genera el schema definitivo al procesar.
    selector = providers.get_selector()
    tipo_heuristico, _conf = selector.clasificar_heuristica(texto[:8000], file.filename)
    tipo_tentativo = tipo_forzado or tipo_heuristico  # puede ser None → worker genera

    # Cotización (mide tokens, estima costo/tiempo, verifica presupuesto). El costo
    # NO depende del schema: se mide por tokens del documento.
    cotizador = providers.get_cotizador()
    cotizacion = cotizador.cotizar(
        tenant_id=tenant_id,
        texto_documento=texto,
        tipo_documento=tipo_tentativo,
    )

    # Guarda el binario y referencia (worker lo leerá si se confirma).
    store = providers.get_document_store()
    documento_ref = store.put(tenant_id, file.filename, data)

    job = IngestJob(
        job_id=uuid.uuid4().hex,
        tenant_id=tenant_id,
        documento_ref=documento_ref,
        nombre_archivo=file.filename,
        tipo_documento=tipo_tentativo,
        tipo_forzado=tipo_forzado,
        usuario_id=ctx.get("user_id"),
        cotizacion=CotizacionSnapshot(
            costo_estimado_usd=cotizacion.costo_estimado_usd,
            tiempo_estimado_seg=cotizacion.tiempo_estimado_seg,
            tokens_documento=cotizacion.tokens_documento,
            aprobado=cotizacion.aprobado,
            decision=cotizacion.decision.value,
        ),
    )

    dispatcher = providers.get_dispatcher()
    dispatcher.crear_job(job)

    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "tipo_documento": tipo_tentativo,
        "tipo_resuelto_por": "usuario" if tipo_forzado else (
            "heuristica" if tipo_heuristico else "worker_generara"
        ),
        "cotizacion": cotizacion.to_dict(),
        "extraccion_confiable": confiable,
        "advertencia": None if confiable else (
            "El extractor ligero pudo subestimar el texto (¿PDF escaneado?). "
            "El worker re-medirá con OCR; el costo real puede variar."
        ),
        "requiere_confirmacion": job.status == JobStatus.pending_confirmation,
    }


@router.post("/documents/{job_id}/confirm")
async def confirmar_ingesta(
    job_id: str,
    ctx: dict = Depends(requiere_rol("admin", "editor")),
):
    """Confirma e encola un job aprobado hacia el worker. Sin esto, no hay ingesta."""
    tenant_id = ctx["org_id"]
    reader = providers.get_status_reader()
    job = reader.get(tenant_id, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job no encontrado.")

    dispatcher = providers.get_dispatcher()
    try:
        job = dispatcher.confirmar(job_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return {"job_id": job.job_id, "status": job.status.value, "encolado": True}


@router.get("/documents/{job_id}")
async def estado_job(
    job_id: str,
    ctx: dict = Depends(requiere_rol("admin", "editor", "viewer")),
):
    """Estado de un job (aislado por tenant)."""
    reader = providers.get_status_reader()
    job = reader.get(ctx["org_id"], job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job no encontrado.")
    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "tipo_documento": job.tipo_documento,
        "resultado": job.resultado,
        "error": job.error,
    }
