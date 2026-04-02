from fastapi import APIRouter, Depends, HTTPException
from app.api.auth import verificar_api_key
from app.core.matrix import TraceabilityMatrix

router = APIRouter(prefix="/trail", tags=["trail"])


@router.get("/document/{document_id}")
async def trail_documento(
    document_id: str,
    ctx: dict = Depends(verificar_api_key)
):
    """Audit trail completo de un documento."""
    import os
    os.environ["ORG_ID"] = ctx["org_id"]

    tm = TraceabilityMatrix()
    trail = tm.get_document_trail(document_id)

    if not trail:
        raise HTTPException(
            status_code=404,
            detail="No se encontró trail para este documento."
        )

    return {
        "document_id": document_id,
        "total_eventos": len(trail),
        "trail": trail
    }


@router.get("/recent")
async def actividad_reciente(
    limit: int = 20,
    ctx: dict = Depends(verificar_api_key)
):
    """Actividad reciente de la organización."""
    import os
    os.environ["ORG_ID"] = ctx["org_id"]

    tm = TraceabilityMatrix()
    actividad = tm.get_recent_activity(limit=limit)

    return {
        "org_id": ctx["org_id"],
        "actividad": actividad
    }


@router.get("/summary")
async def resumen_actividad(ctx: dict = Depends(verificar_api_key)):
    """Resumen de actividad por componente."""
    import os
    os.environ["ORG_ID"] = ctx["org_id"]

    tm = TraceabilityMatrix()
    resumen = tm.get_component_summary()

    return {
        "org_id": ctx["org_id"],
        "resumen": resumen
    }