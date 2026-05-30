"""
DOCYAN LDE™ — Router de Fuentes de Ingesta Documental (B0.5).

Expone el contrato HTTP del *Modo conectado* de la ingesta documental
(adenda 6.1): DOCYAN se conecta a un repositorio documental del cliente
(Google Drive, OneDrive, FTP/SFTP, Notion como wiki) y lista / ingiere
documentos desde ahí.

ALCANCE B0.5: contrato HTTP + schemas Pydantic v2 definidos. La lógica
completa de listado e ingesta real se construye en B1+ sobre GraphRAG-SDK
(Docling + LlamaIndex → FalkorDB). Los handlers de `list_documents` e
`ingest_document` son STUBS EXPLÍCITOS — devuelven la forma del contrato
con `status="not_implemented"`, no fingen capacidad (CLAUDE.md §2.4).

FUERA DE SCOPE (absoluto, adenda 6.1 / §9): extracción de datos
transaccionales de ERPs, CRMs, email, chat, video o bases transaccionales.
DOCYAN complementa el sistema de registro, no lo reemplaza.
"""

from enum import Enum
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.api.auth import requiere_rol

router = APIRouter(prefix="/ingest_sources", tags=["ingest_sources"])


class DocumentSource(str, Enum):
    """Fuentes documentales soportadas (Modo conectado, adenda 6.1)."""

    google_drive = "google_drive"
    onedrive = "onedrive"
    ftp = "ftp"
    notion = "notion"


# ─── Schemas ────────────────────────────────────────────────────────────────


class SourceConfigRequest(BaseModel):
    """Configuración de conexión a un repositorio documental del cliente.

    Los campos son opcionales y dependientes de la fuente; la validación
    específica por fuente se realiza en B1+ al construir cada cliente real.
    """

    model_config = ConfigDict(extra="forbid")

    # Credenciales / endpoints genéricos (subconjunto según fuente)
    token: Optional[str] = Field(
        default=None, description="Token/credencial de la fuente (OAuth, API key, integration token)."
    )
    host: Optional[str] = Field(default=None, description="Host del repositorio (FTP/SFTP).")
    port: Optional[int] = Field(default=None, description="Puerto (FTP/SFTP).")
    username: Optional[str] = Field(default=None, description="Usuario (FTP/SFTP).")
    password: Optional[str] = Field(default=None, description="Contraseña (FTP/SFTP).")
    # Selector de ámbito a monitorear/sincronizar
    folder_id: Optional[str] = Field(
        default=None, description="ID de carpeta/biblioteca a monitorear (Drive/OneDrive)."
    )
    remote_path: Optional[str] = Field(default=None, description="Ruta remota a sincronizar (FTP/SFTP).")


class SourceConfigResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: DocumentSource
    tenant_id: str
    status: str
    detail: str


class DocumentRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_id: str
    name: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None


class ListDocumentsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    folder_id: Optional[str] = Field(default=None, description="Carpeta/ruta a listar.")


class ListDocumentsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: DocumentSource
    tenant_id: str
    documents: list[DocumentRef]
    total: int
    status: str
    detail: str


class IngestDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_id: str = Field(description="ID del documento en la fuente.")


class IngestDocumentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: DocumentSource
    tenant_id: str
    external_id: str
    status: str
    detail: str


# ─── Endpoints ──────────────────────────────────────────────────────────────


@router.post("/{source}/configure", response_model=SourceConfigResponse)
async def configure_source(
    source: DocumentSource,
    request: SourceConfigRequest,
    ctx: dict = Depends(requiere_rol("admin", "editor")),
) -> SourceConfigResponse:
    """Registra/valida la configuración de conexión a una fuente documental.

    Multi-tenant strict: el `tenant_id` se resuelve del usuario logueado.
    STUB B0.5 — la persistencia de credenciales (Supabase, cifrada) y la
    verificación de conexión real se implementan en B12 Onboarding.
    """
    tenant_id = ctx.get("org_id") or ctx.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id no resuelto del contexto de usuario")

    return SourceConfigResponse(
        source=source,
        tenant_id=tenant_id,
        status="configured",
        detail=(
            f"Configuración de '{source.value}' aceptada para tenant '{tenant_id}'. "
            "Persistencia cifrada y verificación de conexión: B12."
        ),
    )


@router.post("/{source}/list_documents", response_model=ListDocumentsResponse)
async def list_documents(
    source: DocumentSource,
    request: ListDocumentsRequest,
    ctx: dict = Depends(requiere_rol("admin", "editor", "viewer")),
) -> ListDocumentsResponse:
    """Lista documentos disponibles en la fuente para el tenant.

    STUB B0.5 — el listado real (vía los clientes de `app.ingest_sources.*`)
    se conecta en B1+/B12. No finge resultados: devuelve lista vacía con
    status='not_implemented'.
    """
    tenant_id = ctx.get("org_id") or ctx.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id no resuelto del contexto de usuario")

    return ListDocumentsResponse(
        source=source,
        tenant_id=tenant_id,
        documents=[],
        total=0,
        status="not_implemented",
        detail=f"Listado de '{source.value}' se implementa en B1+/B12 sobre GraphRAG-SDK.",
    )


@router.post("/{source}/ingest_document", response_model=IngestDocumentResponse)
async def ingest_document(
    source: DocumentSource,
    request: IngestDocumentRequest,
    ctx: dict = Depends(requiere_rol("admin", "editor")),
) -> IngestDocumentResponse:
    """Ingiere un documento desde la fuente al DKG del tenant.

    STUB B0.5 — la ingesta real (Docling + LlamaIndex → GraphRAG-SDK →
    FalkorDB, con cotizador pre-ingesta) se construye en B1+/B3. No finge
    ingesta: devuelve status='not_implemented'.
    """
    tenant_id = ctx.get("org_id") or ctx.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id no resuelto del contexto de usuario")

    return IngestDocumentResponse(
        source=source,
        tenant_id=tenant_id,
        external_id=request.external_id,
        status="not_implemented",
        detail=(
            f"Ingesta de '{source.value}' se implementa en B1+ (GraphRAG-SDK) "
            "con cotizador pre-ingesta (B3)."
        ),
    )
