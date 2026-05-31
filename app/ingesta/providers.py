"""
Providers de dependencias de ingesta (B2 §8.3).

DOCYAN LDE™ by XCID.

Construyen las instancias de producción (Supabase/Redis) que usan los endpoints.
Centralizadas aquí para que los tests las sustituyan con una sola sobreescritura
(monkeypatch) por backend en memoria, sin tocar los handlers.
"""
from __future__ import annotations

from app.ingesta.budget_manager import BudgetManager
from app.ingesta.cotizador import Cotizador
from app.ingesta.document_store import SupabaseStorageDocumentStore
from app.jobs.dispatcher import JobDispatcher
from app.jobs.job_status import JobStatusReader
from app.schemas_documentales.registry import SchemaRegistry
from app.schemas_documentales.selector import SchemaSelector


def get_cotizador() -> Cotizador:
    return Cotizador(budget_manager=BudgetManager())


def get_dispatcher() -> JobDispatcher:
    return JobDispatcher()


def get_status_reader() -> JobStatusReader:
    return JobStatusReader()


def get_selector() -> SchemaSelector:
    return SchemaSelector(registry=SchemaRegistry())


def get_document_store():
    return SupabaseStorageDocumentStore()
