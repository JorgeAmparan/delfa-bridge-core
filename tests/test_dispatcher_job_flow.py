"""
B2 §10 — test bloqueador: el backend encola un job, el worker lo recoge, lo
procesa y lo marca completo. Se usa InMemoryQueueBackend + un consumidor que
simula el loop del worker (sin Redis, sin GraphRAG-SDK real).
"""
from app.jobs.dispatcher import InMemoryQueueBackend, JobDispatcher
from app.jobs.job_models import CotizacionSnapshot, IngestJob, JobStatus


def _job_aprobado(job_id="j1", tenant="t1"):
    return IngestJob(
        job_id=job_id,
        tenant_id=tenant,
        documento_ref=f"{tenant}/doc.pdf",
        nombre_archivo="doc.pdf",
        tipo_documento="manual_tecnico",
        cotizacion=CotizacionSnapshot(
            costo_estimado_usd=0.02, tiempo_estimado_seg=120, tokens_documento=9000,
            aprobado=True, decision="aprobado_requiere_confirmacion",
        ),
    )


def test_flujo_completo_encolar_recoger_procesar_completar():
    backend = InMemoryQueueBackend()
    dispatcher = JobDispatcher(backend=backend)

    # 1. Backend crea el job (cotizado, aprobado) → pending_confirmation, NO encolado.
    job = dispatcher.crear_job(_job_aprobado())
    assert job.status == JobStatus.pending_confirmation
    assert backend.queue_length() == 0

    # 2. Confirmación → queued + encolado.
    dispatcher.confirmar("j1")
    assert backend.queue_length() == 1

    # 3. El worker recoge el job de la cola.
    job_id = backend.pop()
    assert job_id == "j1"
    dispatcher.marcar_procesando(job_id)
    assert backend.load_job(job_id).status == JobStatus.processing

    # 4. El worker procesa (pipeline simulado) y marca completo.
    resultado = {"procedimientos": 7, "pasos": 23, "advertencias": 5}
    dispatcher.marcar_completado(job_id, resultado)
    final = backend.load_job(job_id)
    assert final.status == JobStatus.completed
    assert final.resultado == resultado
    assert backend.queue_length() == 0


def test_job_rechazado_no_es_confirmable():
    backend = InMemoryQueueBackend()
    dispatcher = JobDispatcher(backend=backend)
    job = _job_aprobado(job_id="jr")
    job.cotizacion.aprobado = False  # cotizador rechazó
    job.cotizacion.decision = "rechazado_presupuesto"
    creado = dispatcher.crear_job(job)
    assert creado.status == JobStatus.rejected

    import pytest

    with pytest.raises(ValueError):
        dispatcher.confirmar("jr")
    assert backend.queue_length() == 0


def test_job_fallido_se_marca():
    backend = InMemoryQueueBackend()
    dispatcher = JobDispatcher(backend=backend)
    dispatcher.crear_job(_job_aprobado(job_id="jf"))
    dispatcher.confirmar("jf")
    backend.pop()
    dispatcher.marcar_fallido("jf", "Docling no pudo parsear el PDF")
    assert backend.load_job("jf").status == JobStatus.failed
    assert "Docling" in backend.load_job("jf").error
