from unittest.mock import MagicMock, patch

from app.core.dii import (
    EXTENSIONES_SOPORTADAS,
    DigestInputIntelligence,
    clasificar_documento,
)


class TestClasificadorDocumento:
    def test_tabla_detection_with_pipes(self):
        texto = "| Col1 | Col2 |\n| --- | --- |\n" + "| a | b |\n" * 10
        result = clasificar_documento(texto, "txt")
        assert result["tiene_tablas"] is True
        assert result["usar_llamaindex"] is True

    def test_xlsx_always_has_tables(self):
        result = clasificar_documento("some text", "xlsx")
        assert result["tiene_tablas"] is True

    def test_narrative_text(self):
        texto = "Lorem ipsum. " * 100
        result = clasificar_documento(texto, "pdf")
        assert result["es_narrativo"] is True
        assert result["usar_langextract"] is True

    def test_short_text_no_narrative(self):
        result = clasificar_documento("Hello", "txt")
        assert result["es_narrativo"] is False

    def test_chars_count(self):
        texto = "a" * 500
        result = clasificar_documento(texto, "pdf")
        assert result["chars"] == 500


class TestExtensiones:
    def test_pdf_supported(self):
        assert "pdf" in EXTENSIONES_SOPORTADAS

    def test_docx_supported(self):
        assert "docx" in EXTENSIONES_SOPORTADAS

    def test_xlsx_supported(self):
        assert "xlsx" in EXTENSIONES_SOPORTADAS

    def test_unsupported_extension(self):
        assert "exe" not in EXTENSIONES_SOPORTADAS


class TestDIIInit:
    @patch("app.core.dii.create_client")
    @patch("app.core.dii.DocumentConverter")
    def test_instantiation(self, mock_converter, mock_supabase):
        mock_supabase.return_value = MagicMock()
        dii = DigestInputIntelligence(org_id="test")
        assert dii.org_id == "test"

    @patch("app.core.dii.create_client")
    @patch("app.core.dii.DocumentConverter")
    def test_hash_deterministic(self, mock_converter, mock_supabase):
        mock_supabase.return_value = MagicMock()
        dii = DigestInputIntelligence(org_id="test")
        h1 = dii._calcular_hash("hello world")
        h2 = dii._calcular_hash("hello world")
        assert h1 == h2

    @patch("app.core.dii.create_client")
    @patch("app.core.dii.DocumentConverter")
    def test_hash_different_inputs(self, mock_converter, mock_supabase):
        mock_supabase.return_value = MagicMock()
        dii = DigestInputIntelligence(org_id="test")
        h1 = dii._calcular_hash("hello")
        h2 = dii._calcular_hash("world")
        assert h1 != h2
