"""
Almacén de documentos para ingesta (B2 §8).

DOCYAN LDE™ by XCID.

El backend (`docyan-lde-api`) recibe el archivo (modo manual), lo guarda y pasa
al worker (`docyan-lde-ingest`) una REFERENCIA (`documento_ref`), no el binario:
ambos son Fly apps separadas sin filesystem compartido. El worker lee el binario
por esa referencia.

Dos implementaciones:
  - LocalDocumentStore: filesystem (dev/tests, o un volumen montado).
  - SupabaseStorageDocumentStore: bucket de Supabase Storage (producción) — el
    backend sube, el worker descarga con la misma service key.

PENDIENTE DE JORGE (ops): crear el bucket `ingest-tmp` en Supabase Storage para
producción (con política de retención corta; el documento permanente vive en el
grafo tras la ingesta).
"""
from __future__ import annotations

import os
import pathlib
import uuid


class LocalDocumentStore:
    """Almacén en filesystem. Para dev/tests o un volumen montado compartido."""

    def __init__(self, base_dir: str | None = None):
        self.base_dir = pathlib.Path(
            base_dir or os.getenv("INGEST_STORAGE_DIR", "/tmp/docyan_ingest")
        )
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def put(self, tenant_id: str, nombre_archivo: str, data: bytes) -> str:
        key = f"{tenant_id}/{uuid.uuid4().hex}_{nombre_archivo}"
        dest = self.base_dir / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return key

    def get(self, ref: str) -> bytes:
        return (self.base_dir / ref).read_bytes()

    def delete(self, ref: str) -> None:
        p = self.base_dir / ref
        if p.exists():
            p.unlink()


class SupabaseStorageDocumentStore:
    """Almacén en Supabase Storage (producción). Bucket configurable."""

    def __init__(self, bucket: str | None = None, client=None):
        self.bucket = bucket or os.getenv("INGEST_STORAGE_BUCKET", "ingest-tmp")
        self._client = client

    def _sb(self):
        if self._client is None:
            from supabase import create_client

            self._client = create_client(
                os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY")
            )
        return self._client

    def put(self, tenant_id: str, nombre_archivo: str, data: bytes) -> str:
        key = f"{tenant_id}/{uuid.uuid4().hex}_{nombre_archivo}"
        self._sb().storage.from_(self.bucket).upload(key, data)
        return key

    def get(self, ref: str) -> bytes:
        return self._sb().storage.from_(self.bucket).download(ref)

    def delete(self, ref: str) -> None:
        self._sb().storage.from_(self.bucket).remove([ref])
