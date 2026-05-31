from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.auth import requiere_rol
from app.core.edb import EntityDataBrain

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=100)


@router.post("/")
async def buscar(
    request: SearchRequest,
    ctx: dict = Depends(requiere_rol("admin", "editor", "viewer"))
):
    """
    Búsqueda semántica con Intent-B integrado.
    Acepta lenguaje natural y retorna entidades relevantes.
    """
    edb = EntityDataBrain(org_id=ctx["org_id"])
    resultados = edb.search_semantic(request.query, limit=request.limit)

    # §9.1 — hook de persistencia: registra la consulta como :EventoOperativo
    # (tipo="consulta_realizada") en el grafo del tenant. Best-effort: un fallo de
    # persistencia NO debe degradar la respuesta de la consulta. La consulta real
    # con clasificador completo es B8; esto es la persistencia mínima para Playbook.
    try:
        from app.eventos import registrar_consulta_realizada

        primer = resultados[0] if resultados else None
        entidad_id = primer.get("id") if isinstance(primer, dict) else None
        registrar_consulta_realizada(
            tenant_id=ctx["org_id"],
            usuario_id=ctx.get("user_id"),
            consulta_texto=request.query,
            respuesta_resumen=str(resultados)[:500],
            entidad_consultada_id=entidad_id,
        )
    except Exception:  # noqa: BLE001
        pass

    return {
        "query": request.query,
        "resultados": resultados,
        "total": len(resultados)
    }
