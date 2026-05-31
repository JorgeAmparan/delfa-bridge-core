"""
docyan-lde-embedder — Servicio HTTP de embeddings BGE-M3 self-hosted.

DOCYAN LDE™ by XCID — B1 §4.

Proceso Fly INDEPENDIENTE del backend principal (decisión #1, topología de 4
procesos B1). Carga el modelo BAAI/bge-m3 (1024 dim) en memoria una sola vez
y expone un único endpoint de embeddings sobre la red privada de Fly
(`docyan-lde-embedder.internal:8000`). No es público.

Por qué aparte: BGE-M3 arrastra PyTorch + sentence-transformers (~3 GB) que NO
deben contaminar la imagen del backend (<1 GB, tope de unpack de Fly). El
backend habla con este servicio vía `app/embeddings/bge_client.py` (cliente
HTTP puro, sin torch).

Contrato de API (B1 §4.1):
    POST /embed   {"texts": ["...", "..."]}
                → {"embeddings": [[...1024...], [...1024...]], "dim": 1024}
    GET  /health → {"status": "healthy", "model": "...", "dim": 1024, "ready": bool}
"""
import os
import threading

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

MODEL_NAME = os.getenv("BGE_MODEL_NAME", "BAAI/bge-m3")
EMBED_DIM = 1024  # BGE-M3 — dimensión fija (decisión #1). NO 1536 (OpenAI).

app = FastAPI(
    title="DOCYAN LDE™ — BGE-M3 Embedder",
    description="Servicio self-hosted de embeddings BGE-M3 (1024 dim). DOCYAN LDE™ by XCID.",
    version="1.0.0",
)

# El modelo se carga perezosamente bajo lock en el primer request, no en import,
# para que el proceso arranque y responda /health rápido mientras carga.
_model = None
_model_lock = threading.Lock()


def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                _model = SentenceTransformer(MODEL_NAME)
    return _model


class EmbedRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, description="Textos a embeddir (≥1).")


class EmbedResponse(BaseModel):
    embeddings: list[list[float]]
    dim: int


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "model": MODEL_NAME,
        "dim": EMBED_DIM,
        "ready": _model is not None,
    }


@app.post("/embed", response_model=EmbedResponse)
async def embed(req: EmbedRequest):
    cleaned = [t.strip() for t in req.texts]
    if not any(cleaned):
        raise HTTPException(status_code=400, detail="Todos los textos están vacíos.")
    model = _get_model()
    vectors = model.encode(cleaned, normalize_embeddings=True)
    embeddings = [v.tolist() for v in vectors]
    dim = len(embeddings[0]) if embeddings else EMBED_DIM
    if dim != EMBED_DIM:
        raise HTTPException(
            status_code=500,
            detail=f"Dimensión inesperada {dim}, se esperaba {EMBED_DIM} (BGE-M3).",
        )
    return {"embeddings": embeddings, "dim": dim}
