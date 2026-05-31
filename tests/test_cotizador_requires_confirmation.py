"""
B2 §10 — test bloqueador: sin confirmación explícita NO se invoca a GraphRAG-SDK.

Se modela el pipeline de ingesta como un callable con contador de invocaciones.
Un consumidor (loop del worker) solo procesa jobs que están ENCOLADOS. Como
crear_job NO encola (queda pending_confirmation), el pipeline no se llama hasta
que se confirma. El gate no tiene bypass (CLAUDE.md §14).
"""
from app.ingesta.budget_manager import BudgetManager, InMemoryBudgetStore
from app.ingesta.cotizador import Cotizador
from app.jobs.dispatcher import InMemoryQueueBackend, JobDispatcher
from app.jobs.job_models import CotizacionSnapshot, IngestJob, JobStatus

TEXTO = "Procedimiento de instalación del seccionador. " * 800


class _PipelineEspia:
    """Sustituto de GraphRAG-SDK que cuenta invocaciones reales de ingesta."""

    def __init__(self):
        self.invocaciones = 0

    def ingerir(self, job: IngestJob) -> dict:
        self.invocaciones += 1
        return {"ok": True}


def _drenar_cola(backend, dispatcher, pipeline):
    """Simula el loop del worker: solo procesa lo que esté ENCOLADO."""
    while (job_id := backend.pop()) is not None:
        dispatcher.marcar_procesando(job_id)
        job = backend.load_job(job_id)
        resultado = pipeline.ingerir(job)
        dispatcher.marcar_completado(job_id, resultado)


def _crear_job_cotizado(tenant, dispatcher):
    store = InMemoryBudgetStore()
    bm = BudgetManager(store=store)
    bm.ensure_budget(tenant, saldo_inicial_usd=10.0)
    cz = Cotizador(budget_manager=bm)
    c = cz.cotizar(tenant, TEXTO, tipo_documento="manual_tecnico")
    job = IngestJob(
        job_id="j1", tenant_id=tenant, documento_ref=f"{tenant}/d.pdf",
        nombre_archivo="d.pdf", tipo_documento="manual_tecnico",
        cotizacion=CotizacionSnapshot(
            costo_estimado_usd=c.costo_estimado_usd,
            tiempo_estimado_seg=c.tiempo_estimado_seg,
            tokens_documento=c.tokens_documento,
            aprobado=c.aprobado, decision=c.decision.value,
        ),
    )
    return dispatcher.crear_job(job)


def test_sin_confirmacion_no_se_invoca_pipeline():
    backend = InMemoryQueueBackend()
    dispatcher = JobDispatcher(backend=backend)
    pipeline = _PipelineEspia()

    job = _crear_job_cotizado("t1", dispatcher)
    assert job.status == JobStatus.pending_confirmation

    # El worker intenta drenar la cola SIN que haya confirmación → no procesa nada.
    _drenar_cola(backend, dispatcher, pipeline)
    assert pipeline.invocaciones == 0, "GraphRAG-SDK NO debe invocarse sin confirmación"
    assert backend.load_job("j1").status == JobStatus.pending_confirmation


def test_tras_confirmacion_si_se_invoca_pipeline():
    backend = InMemoryQueueBackend()
    dispatcher = JobDispatcher(backend=backend)
    pipeline = _PipelineEspia()

    _crear_job_cotizado("t1", dispatcher)
    dispatcher.confirmar("j1")  # confirmación explícita
    _drenar_cola(backend, dispatcher, pipeline)

    assert pipeline.invocaciones == 1
    assert backend.load_job("j1").status == JobStatus.completed
