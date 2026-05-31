"""
Registry vivo de schemas documentales por tenant (B2 §6.4).

DOCYAN LDE™ by XCID.

Registra los schemas activos por tenant: los del catálogo del mercado alfa y los
derivados en runtime por el generador dinámico. Los schemas generados que
demuestran utilidad (uso_contador) se proponen como candidatos a integrar al
catálogo permanente.

Persistencia: tabla `tenant_schemas` (migración 009, JSONB). Diseño testeable
idéntico al de budget: el acceso al almacén se abstrae en `SchemaStore`; tests
inyectan `InMemorySchemaStore`, producción usa `SupabaseSchemaStore`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from app.schemas_documentales.base import DocumentSchema
from app.schemas_documentales.catalogo import CATALOGO


@dataclass
class SchemaRecord:
    tenant_id: str
    tipo_documento: str
    schema: DocumentSchema
    es_generado_dinamicamente: bool
    uso_contador: int = 0
    candidato_catalogo: bool = False


class SchemaStore:
    """Contrato de almacenamiento del registry."""

    def get(self, tenant_id: str, tipo_documento: str) -> SchemaRecord | None: ...
    def upsert(self, record: SchemaRecord) -> SchemaRecord: ...
    def list_for_tenant(self, tenant_id: str) -> list[SchemaRecord]: ...
    def increment_uso(self, tenant_id: str, tipo_documento: str) -> int: ...


# ── Almacén en memoria (tests / dev) ──────────────────────────────────────────


@dataclass
class InMemorySchemaStore:
    _rows: dict[tuple[str, str], SchemaRecord] = field(default_factory=dict)

    def get(self, tenant_id: str, tipo_documento: str) -> SchemaRecord | None:
        return self._rows.get((tenant_id, tipo_documento))

    def upsert(self, record: SchemaRecord) -> SchemaRecord:
        self._rows[(record.tenant_id, record.tipo_documento)] = record
        return record

    def list_for_tenant(self, tenant_id: str) -> list[SchemaRecord]:
        return [r for (t, _), r in self._rows.items() if t == tenant_id]

    def increment_uso(self, tenant_id: str, tipo_documento: str) -> int:
        rec = self._rows[(tenant_id, tipo_documento)]
        rec.uso_contador += 1
        return rec.uso_contador


# ── Almacén Supabase (producción) ─────────────────────────────────────────────


class SupabaseSchemaStore:
    TABLE = "tenant_schemas"

    def __init__(self, client=None):
        self._client = client

    def _sb(self):
        if self._client is None:
            from supabase import create_client

            self._client = create_client(
                os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY")
            )
        return self._client

    @staticmethod
    def _row_to_record(row: dict) -> SchemaRecord:
        return SchemaRecord(
            tenant_id=row["tenant_id"],
            tipo_documento=row["tipo_documento"],
            schema=DocumentSchema.from_dict(row["schema_def"]),
            es_generado_dinamicamente=row.get("es_generado_dinamicamente", False),
            uso_contador=row.get("uso_contador", 0),
            candidato_catalogo=row.get("candidato_catalogo", False),
        )

    def get(self, tenant_id: str, tipo_documento: str) -> SchemaRecord | None:
        res = (
            self._sb().table(self.TABLE).select("*")
            .eq("tenant_id", tenant_id).eq("tipo_documento", tipo_documento)
            .limit(1).execute()
        )
        return self._row_to_record(res.data[0]) if res.data else None

    def upsert(self, record: SchemaRecord) -> SchemaRecord:
        self._sb().table(self.TABLE).upsert(
            {
                "tenant_id": record.tenant_id,
                "tipo_documento": record.tipo_documento,
                "schema_def": record.schema.to_dict(),
                "es_generado_dinamicamente": record.es_generado_dinamicamente,
                "uso_contador": record.uso_contador,
                "candidato_catalogo": record.candidato_catalogo,
            },
            on_conflict="tenant_id,tipo_documento",
        ).execute()
        return record

    def list_for_tenant(self, tenant_id: str) -> list[SchemaRecord]:
        res = self._sb().table(self.TABLE).select("*").eq("tenant_id", tenant_id).execute()
        return [self._row_to_record(r) for r in (res.data or [])]

    def increment_uso(self, tenant_id: str, tipo_documento: str) -> int:
        rec = self.get(tenant_id, tipo_documento)
        if rec is None:
            raise KeyError(f"schema {tipo_documento} inexistente para {tenant_id}")
        nuevo = rec.uso_contador + 1
        self._sb().table(self.TABLE).update({"uso_contador": nuevo}).eq(
            "tenant_id", tenant_id
        ).eq("tipo_documento", tipo_documento).execute()
        return nuevo


# Umbral de uso para proponer un schema generado como candidato a catálogo.
UMBRAL_CANDIDATO_CATALOGO = 5


class SchemaRegistry:
    """Registro de schemas activos por tenant (catálogo + generados)."""

    def __init__(self, store: SchemaStore | None = None):
        self.store = store or SupabaseSchemaStore()

    def resolver(self, tenant_id: str, tipo_documento: str) -> DocumentSchema | None:
        """
        Resuelve un schema por tipo: primero un schema generado/registrado del
        tenant (puede sobreescribir el del catálogo con ajustes propios), luego el
        catálogo base. None si no existe en ninguno.
        """
        rec = self.store.get(tenant_id, tipo_documento)
        if rec is not None:
            return rec.schema
        return CATALOGO.get(tipo_documento)

    def registrar(
        self,
        tenant_id: str,
        schema: DocumentSchema,
        es_generado_dinamicamente: bool | None = None,
    ) -> SchemaRecord:
        """Registra (o actualiza) un schema para un tenant."""
        if es_generado_dinamicamente is None:
            es_generado_dinamicamente = schema.es_generado_dinamicamente
        record = SchemaRecord(
            tenant_id=tenant_id,
            tipo_documento=schema.tipo_documento,
            schema=schema,
            es_generado_dinamicamente=es_generado_dinamicamente,
        )
        return self.store.upsert(record)

    def marcar_uso(self, tenant_id: str, tipo_documento: str) -> SchemaRecord | None:
        """
        Incrementa el contador de uso de un schema (tras ingesta exitosa) y, si un
        schema generado supera el umbral, lo marca candidato a catálogo permanente.
        """
        rec = self.store.get(tenant_id, tipo_documento)
        if rec is None:
            return None
        nuevo_uso = self.store.increment_uso(tenant_id, tipo_documento)
        rec.uso_contador = nuevo_uso
        if (
            rec.es_generado_dinamicamente
            and nuevo_uso >= UMBRAL_CANDIDATO_CATALOGO
            and not rec.candidato_catalogo
        ):
            rec.candidato_catalogo = True
            self.store.upsert(rec)
        return rec

    def candidatos_a_catalogo(self, tenant_id: str) -> list[SchemaRecord]:
        """Schemas generados que demostraron utilidad (para revisión del equipo)."""
        return [
            r for r in self.store.list_for_tenant(tenant_id)
            if r.es_generado_dinamicamente and r.candidato_catalogo
        ]
