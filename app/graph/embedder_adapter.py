"""
Adapter BGE-M3 → interfaz Embedder de GraphRAG-SDK 1.1.1.

DOCYAN LDE™ by XCID — B1 §9.3.

Decisión #1 (firme): BGE-M3 self-hosted es el embedder de DOCYAN. La PoC usó
`LiteLLMEmbedder("text-embedding-3-small", dim=1536)` por simplicidad; esto NO
invalida la decisión. Aquí se cumple la interfaz REAL del SDK (`graphrag_sdk.
Embedder`, ABC con `model_name` + `embed_query`) envolviendo el cliente HTTP
`bge_client`, que habla con el servicio self-hosted `docyan-lde-embedder`.

La firma del contrato (`embed()` / `dimension`) era una hipótesis; el SDK 1.1.1
expone `Embedder` con `model_name` + `embed_query(text)` + `embed_documents(texts)`.
Per contrato §9.3: "BGE-M3 se mantiene, el adapter se ajusta".

Importante (topología B1): este módulo importa `graphrag_sdk`, que NO está en la
imagen del backend (vive en el worker de ingesta B2). Por eso el import del SDK
es perezoso dentro de la clase: el backend puede importar este módulo sin tener
el SDK instalado; solo falla si realmente se instancia el adapter (camino B2).
"""
from __future__ import annotations

from app.embeddings.bge_client import bge_client as default_bge_client

BGE_M3_DIMENSION = 1024  # decisión #1 — NO 1536 (OpenAI text-embedding-3).
BGE_M3_MODEL_NAME = "BAAI/bge-m3"


def _embedder_base():
    """Importa la ABC del SDK de forma perezosa (ver docstring del módulo)."""
    from graphrag_sdk import Embedder

    return Embedder


def make_bge_m3_adapter(bge_client=None):
    """
    Factory del adapter. Devuelve una instancia de una subclase de
    `graphrag_sdk.Embedder` que delega en `bge_client.get_embeddings`.

    Se usa una factory (en vez de definir la clase a nivel de módulo) porque la
    clase base solo existe si `graphrag_sdk` está instalado.
    """
    Embedder = _embedder_base()
    client = bge_client or default_bge_client

    class BGE_M3_Adapter(Embedder):
        """Adaptador que envuelve `bge_client` para la interfaz del SDK."""

        def __init__(self, bge):
            self.bge_client = bge

        @property
        def model_name(self) -> str:
            return BGE_M3_MODEL_NAME

        @property
        def dimension(self) -> int:
            return BGE_M3_DIMENSION

        def embed_query(self, text: str, **kwargs) -> list[float]:
            return self.bge_client.get_embeddings([text])[0]

        def embed_documents(self, texts: list[str], **kwargs) -> list[list[float]]:
            return self.bge_client.get_embeddings(list(texts))

    return BGE_M3_Adapter(client)
