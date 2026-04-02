from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.api.auth import verificar_api_key
from app.core.edb import EntityDataBrain

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    limit: int = 5


@router.post("/")
async def buscar(
    request: SearchRequest,
    ctx: dict = Depends(verificar_api_key)
):
    """
    Búsqueda semántica con Intent-B integrado.
    Acepta lenguaje natural y retorna entidades relevantes.
    """
    import os
    os.environ["ORG_ID"] = ctx["org_id"]

    edb = EntityDataBrain()
    resultados = edb.search_semantic(request.query, limit=request.limit)

    return {
        "query": request.query,
        "resultados": resultados,
        "total": len(resultados)
    }