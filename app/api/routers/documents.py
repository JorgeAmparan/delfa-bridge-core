import os
import shutil
import tempfile

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from supabase import create_client

from app.api.auth import requiere_rol
from app.core.grg import GovernanceGuardrails
from app.core.matrix import TraceabilityMatrix
from app.core.supabase_client import require_module_enabled, require_supabase_config

load_dotenv()

# FUERA DE ALCANCE MVP Consulta Viva (Adenda 31-may-2026). Este router depende del
# pipeline legacy DII (DigestInputIntelligence), reemplazado por GraphRAG-SDK; la
# ingesta MVP corre por el worker (B2), no por aquí. Cada handler que toca Supabase
# está protegido con require_module_enabled("documents") (flag DOCYAN_ENABLE_DOCUMENTS)
# y usa service_role. Se reactiva en su sprint de activación.
router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/process")
async def procesar_documento(
    file: UploadFile = File(...),
    aplicar_grg: bool = True,
    ctx: dict = Depends(requiere_rol("admin", "editor"))
):
    """
    Sube y procesa un documento a través del pipeline DOCYAN completo.
    DII → EDB → GRG → TM
    """
    org_id = ctx["org_id"]

    # Guardar archivo temporalmente
    suffix = f".{file.filename.split('.')[-1]}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    final_path = os.path.join(os.path.dirname(tmp_path), file.filename)

    try:
        os.rename(tmp_path, final_path)

        # Pipeline DII
        # Import perezoso: DII arrastra el stack pesado de ingesta
        # (Docling/LlamaIndex/torch) que NO va en la imagen B0.5 (diferido a
        # B1, donde DII se reemplaza por GraphRAG-SDK). A nivel de módulo
        # rompía el arranque de la API en el contenedor.
        from app.core.dii import DigestInputIntelligence

        dii = DigestInputIntelligence(org_id=org_id)
        dii.data_path = os.path.dirname(final_path)
        entidades = dii.run_dii_pipeline()

        # GRG si aplica
        resumen_grg = {}
        if aplicar_grg:
            require_module_enabled("documents")
            _url, _key = require_supabase_config("documents", service=True)
            supabase = create_client(_url, _key)
            doc = supabase.table("documents").select("id").eq(
                "org_id", org_id
            ).eq("name", file.filename).order(
                "created_at", desc=True
            ).limit(1).execute()

            if doc.data:
                grg = GovernanceGuardrails(org_id=org_id)
                resumen_grg = grg.evaluar_documento(doc.data[0]["id"])

        return {
            "status": "success",
            "archivo": file.filename,
            "entidades_extraidas": len(entidades),
            "gobernanza": resumen_grg
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Limpiar archivos temporales
        for path in (final_path, tmp_path):
            if os.path.exists(path):
                os.remove(path)


@router.get("/")
async def listar_documentos(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    ctx: dict = Depends(requiere_rol("admin", "editor", "viewer"))
):
    """Lista todos los documentos de la organización."""
    require_module_enabled("documents")
    _url, _key = require_supabase_config("documents", service=True)
    supabase = create_client(_url, _key)
    resultado = supabase.table("documents").select(
        "id, name, source_type, status, processed_at, created_at, metadata",
        count="exact"
    ).eq("org_id", ctx["org_id"]).order(
        "created_at", desc=True
    ).limit(limit).offset(offset).execute()

    return {
        "documentos": resultado.data,
        "total": resultado.count,
        "limit": limit,
        "offset": offset
    }


@router.get("/{document_id}")
async def detalle_documento(
    document_id: str,
    ctx: dict = Depends(requiere_rol("admin", "editor", "viewer"))
):
    """Detalle de un documento con sus entidades."""
    require_module_enabled("documents")
    _url, _key = require_supabase_config("documents", service=True)
    supabase = create_client(_url, _key)

    doc = supabase.table("documents").select("*").eq(
        "id", document_id
    ).eq("org_id", ctx["org_id"]).execute()

    if not doc.data:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")

    entidades = supabase.table("entities").select(
        "id, entity_class, entity_value, entity_type, data_text, knowledge_triple, status, confidence, created_at"
    ).eq("document_id", document_id).eq(
        "org_id", ctx["org_id"]
    ).execute()

    return {
        "documento": doc.data[0],
        "entidades": entidades.data,
        "total_entidades": len(entidades.data)
    }


@router.delete("/{document_id}")
async def eliminar_documento(
    document_id: str,
    ctx: dict = Depends(requiere_rol("admin"))
):
    """Elimina un documento y todos sus registros asociados (cascade)."""
    require_module_enabled("documents")
    _url, _key = require_supabase_config("documents", service=True)
    supabase = create_client(_url, _key)
    org_id = ctx["org_id"]

    doc = supabase.table("documents").select("id, name").eq(
        "id", document_id
    ).eq("org_id", org_id).execute()

    if not doc.data:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")

    entity_ids = supabase.table("entities").select("id").eq(
        "document_id", document_id
    ).eq("org_id", org_id).execute()
    eids = [e["id"] for e in entity_ids.data]

    if eids:
        supabase.table("audit_trail").delete().in_(
            "entity_id", eids
        ).execute()
        supabase.table("quarantine").delete().in_(
            "entity_id", eids
        ).execute()

    supabase.table("audit_trail").delete().eq(
        "document_id", document_id
    ).execute()
    supabase.table("entities").delete().eq(
        "document_id", document_id
    ).eq("org_id", org_id).execute()
    supabase.table("documents").delete().eq(
        "id", document_id
    ).eq("org_id", org_id).execute()

    tm = TraceabilityMatrix(org_id=org_id)
    tm.log(component="API", action="document_deleted",
           detail={"document_id": document_id, "name": doc.data[0]["name"]})

    return {"status": "deleted", "document_id": document_id, "name": doc.data[0]["name"]}
