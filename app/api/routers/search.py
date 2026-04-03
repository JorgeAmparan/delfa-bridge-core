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

    return {
        "query": request.query,
        "resultados": resultados,
        "total": len(resultados)
    }