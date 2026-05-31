"""
Cliente HTTP del servicio BGE-M3 self-hosted (`docyan-lde-embedder`).

DOCYAN LDE™ by XCID — B1 §4.2.

Cliente PURO HTTP (no embebe torch ni el modelo): habla con el proceso Fly
`docyan-lde-embedder` por la red privada (EMBEDDER_URL). Esto mantiene la
imagen del backend ligera (decisión #1, topología de 4 procesos).

Interfaz canónica:
    get_embeddings(texts: list[str]) -> list[list[float]]   # B1 §4.2 / §9.3

`embed()` y `embed_batch()` se conservan como envoltorios de compatibilidad
sobre `get_embeddings()`.
"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

# EMBEDDER_URL es la variable canónica B1 (apunta al servicio Fly). BGE_M3_URL
# se mantiene como alias para compatibilidad con configuración previa (B0).
EMBEDDER_URL = os.getenv("EMBEDDER_URL") or os.getenv("BGE_M3_URL", "http://localhost:8080")
BGE_M3_TIMEOUT = float(os.getenv("BGE_M3_TIMEOUT", "30"))
BGE_M3_DIMS = 1024


class BGEEmbeddingClient:
    """Cliente HTTP del servicio self-hosted BGE-M3 (1024 dim)."""

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        self.base_url = (base_url or EMBEDDER_URL).rstrip("/")
        self.timeout = timeout or BGE_M3_TIMEOUT
        self.dims = BGE_M3_DIMS

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Interfaz canónica (B1 §4.2). Embebe una lista de textos y devuelve una
        lista de vectores de 1024 dim. POST /embed {"texts": [...]}.
        """
        cleaned = [t.strip() for t in texts]
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{self.base_url}/embed", json={"texts": cleaned})
            resp.raise_for_status()
            return resp.json()["embeddings"]

    def embed(self, text: str) -> list[float]:
        """Compat: embebe un solo texto y devuelve su vector."""
        return self.get_embeddings([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Compat: alias de get_embeddings."""
        return self.get_embeddings(texts)

    def health(self) -> bool:
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False


bge_client = BGEEmbeddingClient()
