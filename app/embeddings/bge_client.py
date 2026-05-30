import os

import httpx
from dotenv import load_dotenv

load_dotenv()

BGE_M3_URL = os.getenv("BGE_M3_URL", "http://localhost:8080")
BGE_M3_TIMEOUT = float(os.getenv("BGE_M3_TIMEOUT", "30"))
BGE_M3_DIMS = 1024


class BGEEmbeddingClient:
    """Client for self-hosted BGE-M3 embedding service."""

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        self.base_url = (base_url or BGE_M3_URL).rstrip("/")
        self.timeout = timeout or BGE_M3_TIMEOUT
        self.dims = BGE_M3_DIMS

    def embed(self, text: str) -> list[float]:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url}/embed",
                json={"text": text.strip()},
            )
            resp.raise_for_status()
            return resp.json()["embedding"]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        cleaned = [t.strip() for t in texts]
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url}/embed_batch",
                json={"texts": cleaned},
            )
            resp.raise_for_status()
            return resp.json()["embeddings"]

    def health(self) -> bool:
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False


bge_client = BGEEmbeddingClient()
