"""
Dispatcher de jobs de ingesta (B2 §8.1 / §8.2).

DOCYAN LDE™ by XCID.

Decisión técnica §8 = **Opción A (cola Redis)**. Razones (vs HTTP directo o Fly
machine API): separación limpia de concerns, retry/monitoring naturales, escalado
horizontal (varios workers si crece la carga) y Redis ya está en el stack por la
decisión #6 (sesiones MO + APScheduler). Se implementa con una cola ligera sobre
`redis-py` (LIST + BLPOP) en vez de `rq`, para no añadir una dependencia nueva al
backend ni acoplar su modelo de worker; el backend solo necesita `redis` (ya en
deps). Ver docs/worker_architecture.md.

Diseño testeable: el backend de cola se abstrae en `QueueBackend`. Tests inyectan
`InMemoryQueueBackend`; producción usa `RedisQueueBackend` (REDIS_QUEUE_URL).

Flujo del gate (sin bypass):
  crear job (cotizado) → pending_confirmation  [NO se encola]
  confirmar (si aprobado) → queued              [se encola hacia el worker]
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from app.jobs.job_models import IngestJob, JobStatus

QUEUE_KEY = "docyan:ingest:queue"
JOB_KEY_PREFIX = "docyan:ingest:job:"
# TTL del estado de jobs en Redis (7 días); el FAT lleva el registro permanente.
JOB_STATE_TTL_SECONDS = 7 * 24 * 3600


class QueueBackend:
    """Contrato de cola + almacén de estado de jobs."""

    def save_job(self, job: IngestJob) -> None: ...
    def load_job(self, job_id: str) -> IngestJob | None: ...
    def push(self, job_id: str) -> None: ...
    def pop(self, timeout: int = 0) -> str | None: ...
    def queue_length(self) -> int: ...


# ── Backend en memoria (tests / dev sin Redis) ───────────────────────────────


@dataclass
class InMemoryQueueBackend:
    _jobs: dict[str, str] = field(default_factory=dict)
    _queue: list[str] = field(default_factory=list)

    def save_job(self, job: IngestJob) -> None:
        self._jobs[job.job_id] = job.model_dump_json()

    def load_job(self, job_id: str) -> IngestJob | None:
        raw = self._jobs.get(job_id)
        return IngestJob.model_validate_json(raw) if raw else None

    def push(self, job_id: str) -> None:
        self._queue.append(job_id)

    def pop(self, timeout: int = 0) -> str | None:
        return self._queue.pop(0) if self._queue else None

    def queue_length(self) -> int:
        return len(self._queue)


# ── Backend Redis (producción) ────────────────────────────────────────────────


class RedisQueueBackend:
    def __init__(self, url: str | None = None, client=None):
        self.url = url or os.getenv("REDIS_QUEUE_URL") or os.getenv("REDIS_URL")
        self._client = client

    def _r(self):
        if self._client is None:
            import redis

            self._client = redis.from_url(self.url, decode_responses=True)
        return self._client

    def save_job(self, job: IngestJob) -> None:
        self._r().setex(
            JOB_KEY_PREFIX + job.job_id, JOB_STATE_TTL_SECONDS, job.model_dump_json()
        )

    def load_job(self, job_id: str) -> IngestJob | None:
        raw = self._r().get(JOB_KEY_PREFIX + job_id)
        return IngestJob.model_validate_json(raw) if raw else None

    def push(self, job_id: str) -> None:
        self._r().rpush(QUEUE_KEY, job_id)

    def pop(self, timeout: int = 0) -> str | None:
        if timeout > 0:
            res = self._r().blpop(QUEUE_KEY, timeout=timeout)
            return res[1] if res else None
        return self._r().lpop(QUEUE_KEY)

    def queue_length(self) -> int:
        return int(self._r().llen(QUEUE_KEY))


# ── Dispatcher ─────────────────────────────────────────────────────────────────


class JobDispatcher:
    """Encola jobs hacia el worker y gestiona transiciones de estado."""

    def __init__(self, backend: QueueBackend | None = None):
        self.backend = backend or RedisQueueBackend()

    def crear_job(self, job: IngestJob) -> IngestJob:
        """
        Persiste un job recién cotizado. Si el cotizador lo rechazó, queda
        `rejected` y NO es confirmable. Si fue aprobado, queda
        `pending_confirmation` (aún NO encolado). No hay encolado sin confirmación.
        """
        if job.cotizacion is not None and not job.cotizacion.aprobado:
            job.status = JobStatus.rejected
        else:
            job.status = JobStatus.pending_confirmation
        self.backend.save_job(job)
        return job

    def confirmar(self, job_id: str) -> IngestJob:
        """
        Confirma e encola un job aprobado. Lanza si el job no existe o no es
        confirmable (rechazado, ya procesado, o sin cotización aprobada).
        """
        job = self.backend.load_job(job_id)
        if job is None:
            raise KeyError(f"job inexistente: {job_id}")
        if not job.confirmable():
            raise ValueError(
                f"job {job_id} no es confirmable (status={job.status.value}, "
                f"aprobado={job.cotizacion.aprobado if job.cotizacion else None}). "
                "Sin confirmación válida no se encola hacia el worker."
            )
        job.status = JobStatus.queued
        self.backend.save_job(job)
        self.backend.push(job_id)
        return job

    # ── Transiciones que ejecuta el worker ───────────────────────────────────
    def marcar_procesando(self, job_id: str) -> IngestJob:
        return self._transicion(job_id, JobStatus.processing)

    def marcar_completado(self, job_id: str, resultado: dict) -> IngestJob:
        job = self.backend.load_job(job_id)
        if job is None:
            raise KeyError(f"job inexistente: {job_id}")
        job.status = JobStatus.completed
        job.resultado = resultado
        self.backend.save_job(job)
        return job

    def marcar_fallido(self, job_id: str, error: str) -> IngestJob:
        job = self.backend.load_job(job_id)
        if job is None:
            raise KeyError(f"job inexistente: {job_id}")
        job.status = JobStatus.failed
        job.error = error
        self.backend.save_job(job)
        return job

    def _transicion(self, job_id: str, status: JobStatus) -> IngestJob:
        job = self.backend.load_job(job_id)
        if job is None:
            raise KeyError(f"job inexistente: {job_id}")
        job.status = status
        self.backend.save_job(job)
        return job
