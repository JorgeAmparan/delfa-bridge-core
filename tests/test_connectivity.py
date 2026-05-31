from unittest.mock import MagicMock, patch


class TestBGEClientConnectivity:
    def test_bge_client_instantiation(self):
        from app.embeddings.bge_client import BGEEmbeddingClient
        client = BGEEmbeddingClient(base_url="http://test:8080")
        assert client.base_url == "http://test:8080"
        assert client.dims == 1024

    @patch("app.embeddings.bge_client.httpx.Client")
    def test_embed_calls_endpoint(self, mock_httpx):
        from app.embeddings.bge_client import BGEEmbeddingClient

        # B1: protocolo de un solo endpoint /embed {"texts"} → {"embeddings", "dim"}.
        mock_response = MagicMock()
        mock_response.json.return_value = {"embeddings": [[0.1] * 1024], "dim": 1024}
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_httpx.return_value = mock_client_instance

        client = BGEEmbeddingClient(base_url="http://test:8080")
        result = client.embed("hello world")
        assert len(result) == 1024

    @patch("app.embeddings.bge_client.httpx.Client")
    def test_get_embeddings_canonical(self, mock_httpx):
        from app.embeddings.bge_client import BGEEmbeddingClient

        mock_response = MagicMock()
        mock_response.json.return_value = {"embeddings": [[0.1] * 1024, [0.2] * 1024], "dim": 1024}
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_httpx.return_value = mock_client_instance

        client = BGEEmbeddingClient(base_url="http://test:8080")
        result = client.get_embeddings(["hola", "mundo"])
        assert len(result) == 2
        assert len(result[0]) == 1024
        # Verifica que pega a /embed con el shape {"texts": [...]}
        _, kwargs = mock_client_instance.post.call_args
        assert kwargs["json"] == {"texts": ["hola", "mundo"]}

    @patch("app.embeddings.bge_client.httpx.Client")
    def test_embed_batch(self, mock_httpx):
        from app.embeddings.bge_client import BGEEmbeddingClient

        mock_response = MagicMock()
        mock_response.json.return_value = {"embeddings": [[0.1] * 1024, [0.2] * 1024]}
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_httpx.return_value = mock_client_instance

        client = BGEEmbeddingClient(base_url="http://test:8080")
        result = client.embed_batch(["hello", "world"])
        assert len(result) == 2

    def test_bge_health_unreachable(self):
        from app.embeddings.bge_client import BGEEmbeddingClient
        client = BGEEmbeddingClient(base_url="http://unreachable:9999")
        assert client.health() is False


class TestDKGClientConnectivity:
    # B1 §5: falkor_client.py (skeleton) → app/graph/dkg_client.py (fachada DKG).
    def test_dkg_client_instantiation(self):
        from app.graph.dkg_client import DKGClient
        client = DKGClient(host="test-host", port=6379)
        assert client.host == "test-host"
        assert client.port == 6379

    def test_dkg_health_unreachable(self):
        from app.graph.dkg_client import DKGClient
        client = DKGClient(host="unreachable", port=9999)
        assert client.health() is False


class TestRedisConnectivity:
    def test_redis_client_instantiation(self):
        from app.cache.redis_client import RedisClient
        client = RedisClient(url="redis://test:6379/0")
        assert client.url == "redis://test:6379/0"

    def test_redis_health_unreachable(self):
        from app.cache.redis_client import RedisClient
        client = RedisClient(url="redis://unreachable:9999/0")
        assert client.health() is False
