from app.core.intent import DOCUMENT_TYPES, DocumentIntentAnalyzer, QueryIntentAnalyzer


class TestDocumentTypes:
    def test_all_types_have_required_keys(self):
        for dtype, config in DOCUMENT_TYPES.items():
            assert "descripcion" in config
            assert "entidades_clave" in config
            assert "prompt_extra" in config
            assert isinstance(config["entidades_clave"], list)

    def test_general_type_exists(self):
        assert "general" in DOCUMENT_TYPES

    def test_known_types(self):
        expected = {"contrato", "factura", "reglamento",
                    "estado_de_cuenta", "propuesta", "general"}
        assert expected == set(DOCUMENT_TYPES.keys())


class TestDocumentIntentAnalyzer:
    def test_instantiation(self):
        dia = DocumentIntentAnalyzer()
        assert dia is not None


class TestQueryIntentAnalyzer:
    def test_instantiation(self):
        qia = QueryIntentAnalyzer()
        assert qia is not None
