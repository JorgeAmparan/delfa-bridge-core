"""
Consulta de estado de jobs de ingesta (B2 §8.2).

DOCYAN LDE™ by XCID.

Lectura del estado de un job desde el backend de cola, con verificación de
pertenencia al tenant (multi-tenant strict: un tenant NO puede consultar jobs de
otro).
"""
from __future__ import annotations

from app.jobs.dispatcher import QueueBackend, RedisQueueBackend
from app.jobs.job_models import IngestJob


class JobStatusReader:
    def __init__(self, backend: QueueBackend | None = None):
        self.backend = backend or RedisQueueBackend()

    def get(self, tenant_id: str, job_id: str) -> IngestJob | None:
        """Devuelve el job solo si pertenece al tenant (aislamiento estricto)."""
        job = self.backend.load_job(job_id)
        if job is None or job.tenant_id != tenant_id:
            return None
        return job
