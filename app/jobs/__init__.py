"""
Dispatcher de jobs de ingesta backend → worker (B2 §8).

DOCYAN LDE™ by XCID.

El backend principal NO ingiere: encola jobs hacia el worker `docyan-lde-ingest`
(Fly app aparte) tras pasar el cotizador y recibir confirmación explícita. El
worker consume la cola, procesa y actualiza el estado del job.

Decisión técnica §8 = Opción A (cola Redis). Ver docs/worker_architecture.md.
"""
from app.jobs.dispatcher import JobDispatcher
from app.jobs.job_models import IngestJob, JobStatus
from app.jobs.job_status import JobStatusReader

__all__ = ["IngestJob", "JobStatus", "JobDispatcher", "JobStatusReader"]
