"""
B1 §9.4 / §13 — GraphRAG-SDK usa BGE-M3 como embedder, NO OpenAI. Bloqueador.

Verifica el CABLEADO (no ingiere documentos — eso es B2): que el adapter BGE-M3
cumple la interfaz `Embedder` del SDK 1.1.1 y que GraphRAG lo acepta con
dimensión 1024 (BGE-M3) y NO 1536 (OpenAI text-embedding-3).
"""
from unittest.mock import MagicMock

import pytest

# El SDK es pesado (torch/onnxruntime) y choca con docling en el mismo entorno;
# en CI no se instala. Donde esté disponible (local/worker B2), el test corre.
pytest.importorskip("graphrag_sdk")


def _fake_bge():
    bge = MagicMock()
    bge.get_embeddings.side_effect = lambda texts: [[0.01] * 1024 for _ in texts]
    return bge


def test_adapter_implements_sdk_embedder_interface():
    from graphrag_sdk import Embedder

    from app.graph.embedder_adapter import make_bge_m3_adapter

    adapter = make_bge_m3_adapter(_fake_bge())
    assert isinstance(adapter, Embedder)
    assert adapter.model_name == "BAAI/bge-m3"
    assert adapter.dimension == 1024


def test_adapter_embeds_with_bge_dimension_not_openai():
    from app.graph.embedder_adapter import make_bge_m3_adapter

    adapter = make_bge_m3_adapter(_fake_bge())
    vec = adapter.embed_query("hola mundo")
    assert len(vec) == 1024, "BGE-M3 = 1024 dim, NO 1536 (OpenAI)"

    batch = adapter.embed_documents(["a", "b", "c"])
    assert len(batch) == 3 and all(len(v) == 1024 for v in batch)


def test_graphrag_accepts_bge_adapter():
    """GraphRAG(...) acepta el adapter BGE-M3 como su embedder (dim 1024)."""
    from graphrag_sdk import ConnectionConfig, GraphRAG, LiteLLM

    from app.graph.embedder_adapter import make_bge_m3_adapter

    adapter = make_bge_m3_adapter(_fake_bge())
    # No conecta a FalkorDB ni hace llamadas: solo construye el objeto y valida
    # que el embedder encaja con embedding_dimension=1024.
    rag = GraphRAG(
        connection=ConnectionConfig(host="localhost", port=6379, graph_name="docyan_tenant_sdk_probe"),
        llm=LiteLLM("gemini/gemini-2.5-flash", api_key="fake-key-no-call"),
        embedder=adapter,
        embedding_dimension=adapter.dimension,
    )
    assert rag.embedder.dimension == 1024
    assert rag.embedder is adapter
