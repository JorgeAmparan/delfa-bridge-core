from unittest.mock import patch, MagicMock
from app.core.edb import EntityDataBrain


class TestEDBInit:
    @patch("app.core.edb.create_client")
    def test_instantiation(self, mock_supabase):
        mock_supabase.return_value = MagicMock()
        edb = EntityDataBrain(org_id="test-org")
        assert edb.org_id == "test-org"
        assert edb.embedding_dims == 1024

    @patch("app.core.edb.create_client")
    def test_uses_bge_client(self, mock_supabase):
        mock_supabase.return_value = MagicMock()
        edb = EntityDataBrain(org_id="test-org")
        from app.embeddings.bge_client import bge_client
        assert edb.embedder is bge_client


class TestEDBEmbedding:
    @patch("app.core.edb.create_client")
    @patch("app.embeddings.bge_client.bge_client.embed")
    def test_generar_embedding_calls_bge(self, mock_embed, mock_supabase):
        mock_supabase.return_value = MagicMock()
        mock_embed.return_value = [0.1] * 1024
        edb = EntityDataBrain(org_id="test-org")
        result = edb._generar_embedding("test text")
        mock_embed.assert_called_once_with("test text")
        assert len(result) == 1024


class TestEDBSearch:
    @patch("app.core.edb.create_client")
    def test_search_by_class_calls_supabase(self, mock_supabase):
        mock_client = MagicMock()
        mock_supabase.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
        edb = EntityDataBrain(org_id="test-org")
        result = edb.search_by_class("entidad_nombre", limit=5)
        assert result == []
