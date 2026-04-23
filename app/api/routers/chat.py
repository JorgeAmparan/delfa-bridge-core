from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.api.auth import requiere_rol
from app.core.ri import ResponseIntelligence

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    query: str
    limit: int = Field(default=10, ge=1, le=30)


@router.post("/ask")
async def chat_ask(
    request: ChatRequest,
    ctx: dict = Depends(requiere_rol("admin", "editor", "viewer")),
):
    """
    Consulta inteligente sobre documentos procesados.
    Usa el pipeline completo: EDB (Intent-B + vector) → RI (análisis + síntesis).
    """
    ri = ResponseIntelligence(org_id=ctx["org_id"])
    return ri.responder(query=request.query, limit=request.limit)
