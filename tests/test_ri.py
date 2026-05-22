from unittest.mock import patch, MagicMock
from app.core.ri import ResponseIntelligence


class TestRIInit:
    @patch("app.core.ri.EntityDataBrain")
    @patch("app.core.ri.TraceabilityMatrix")
    def test_instantiation(self, mock_tm, mock_edb):
        ri = ResponseIntelligence(org_id="test-org")
        assert ri.org_id == "test-org"


class TestRIHelpers:
    @patch("app.core.ri.EntityDataBrain")
    @patch("app.core.ri.TraceabilityMatrix")
    def test_instruccion_alta(self, mock_tm, mock_edb):
        ri = ResponseIntelligence(org_id="test-org")
        result = ri._instruccion_por_suficiencia("alta")
        assert "confianza" in result

    @patch("app.core.ri.EntityDataBrain")
    @patch("app.core.ri.TraceabilityMatrix")
    def test_instruccion_baja(self, mock_tm, mock_edb):
        ri = ResponseIntelligence(org_id="test-org")
        result = ri._instruccion_por_suficiencia("baja")
        assert "cautela" in result

    @patch("app.core.ri.EntityDataBrain")
    @patch("app.core.ri.TraceabilityMatrix")
    def test_respuesta_fallback(self, mock_tm, mock_edb):
        ri = ResponseIntelligence(org_id="test-org")
        entidades = [
            {"entity_value": "ABC Corp", "similarity": 0.8},
            {"entity_value": "$50,000", "similarity": 0.7},
        ]
        result = ri._respuesta_fallback(entidades, "media")
        assert "2 entidades" in result
        assert "media" in result

    @patch("app.core.ri.EntityDataBrain")
    @patch("app.core.ri.TraceabilityMatrix")
    def test_construir_contexto(self, mock_tm, mock_edb):
        ri = ResponseIntelligence(org_id="test-org")
        entidades = [
            {
                "entity_class": "monto_total",
                "entity_type": "monto",
                "entity_value": "$25,000",
                "data_text": "Monto total del contrato",
                "knowledge_triple": {"subject": "contrato", "predicate": "vale", "object": "$25,000"},
                "similarity": 0.85,
            }
        ]
        result = ri._construir_contexto(entidades)
        assert "monto_total" in result
        assert "$25,000" in result


class TestRIResponder:
    @patch("app.core.ri.EntityDataBrain")
    @patch("app.core.ri.TraceabilityMatrix")
    def test_no_entities_returns_sin_datos(self, mock_tm, mock_edb):
        mock_edb_instance = MagicMock()
        mock_edb.return_value = mock_edb_instance
        mock_edb_instance.search_semantic.return_value = []
        mock_tm_instance = MagicMock()
        mock_tm.return_value = mock_tm_instance

        ri = ResponseIntelligence(org_id="test-org")
        result = ri.responder("test query")
        assert result["suficiencia"] == "sin_datos"
        assert result["fuentes"] == []
