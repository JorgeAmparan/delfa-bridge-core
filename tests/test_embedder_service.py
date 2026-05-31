"""
B1 §13 — El backend llama al embedder y recibe un vector de 1024 dim. Bloqueador.

Dos modos:
  - Si EMBEDDER_URL apunta a un servicio BGE-M3 alcanzable → llamada REAL y se
    exige dim 1024 (BGE-M3), NO 1536 (OpenAI).
  - Si no hay servicio (CI / dev sin embedder) → se verifica el CONTRATO del
    cliente con un mock: pega a POST /embed con {"texts": [...]} y parsea
    {"embeddings", "dim"} devolviendo vectores de 1024 dim.
"""
import os
from unittest.mock import MagicMock, patch

import pytest


def _embedder_reachable() -> bool:
    from app.embeddings.bge_client import bge_client

    return bge_client.health()


@pytest.mark.skipif(not _embedder_reachable(), reason="docyan-lde-embedder no alcanzable")
def test_embedder_real_returns_1024():
    from app.embeddings.bge_client import BGEEmbeddingClient

    client = BGEEmbeddingClient(base_url=os.getenv("EMBEDDER_URL") or os.getenv("BGE_M3_URL"))
    vecs = client.get_embeddings(["hola mundo"])
    assert len(vecs) == 1
    assert len(vecs[0]) == 1024, "BGE-M3 = 1024 dim, NO 1536 (OpenAI)"


@patch("app.embeddings.bge_client.httpx.Client")
def test_embedder_client_contract_mocked(mock_httpx):
    """Verifica wire-protocol del cliente sin servicio (siempre corre)."""
    from app.embeddings.bge_client import BGEEmbeddingClient

    resp = MagicMock()
    resp.json.return_value = {"embeddings": [[0.5] * 1024], "dim": 1024}
    resp.raise_for_status = MagicMock()
    inst = MagicMock()
    inst.post.return_value = resp
    inst.__enter__ = MagicMock(return_value=inst)
    inst.__exit__ = MagicMock(return_value=False)
    mock_httpx.return_value = inst

    client = BGEEmbeddingClient(base_url="http://embedder:8000")
    vecs = client.get_embeddings(["hola"])
    assert len(vecs[0]) == 1024

    args, kwargs = inst.post.call_args
    assert args[0].endswith("/embed")
    assert kwargs["json"] == {"texts": ["hola"]}
