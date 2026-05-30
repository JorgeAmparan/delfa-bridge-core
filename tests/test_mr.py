from app.core.mr import MODELOS, ModelRouter


class TestModelRouter:
    def setup_method(self):
        self.mr = ModelRouter()

    def test_tier1_simple_document(self):
        result = self.mr.seleccionar(
            chars=5000, tiene_tablas=False,
            source_type="pdf", doc_type="general"
        )
        assert result["tier"] == 1
        assert result["proveedor"] == "google"

    def test_tier2_with_tables(self):
        result = self.mr.seleccionar(
            chars=10000, tiene_tablas=True,
            source_type="xlsx", doc_type="general"
        )
        assert result["tier"] == 2

    def test_tier2_medium_document(self):
        result = self.mr.seleccionar(
            chars=25000, tiene_tablas=False,
            source_type="pdf", doc_type="general"
        )
        assert result["tier"] == 2

    def test_tier3_legal_dense(self):
        result = self.mr.seleccionar(
            chars=55000, tiene_tablas=False,
            source_type="pdf", doc_type="contrato"
        )
        assert result["tier"] == 3
        assert result["proveedor"] == "anthropic"

    def test_tier4_very_large(self):
        result = self.mr.seleccionar(
            chars=120000, tiene_tablas=False,
            source_type="pdf", doc_type="general"
        )
        assert result["tier"] == 4

    def test_intent_always_tier1(self):
        result = self.mr.seleccionar_para_intent()
        assert result["tier"] == 1

    def test_enrichment_legal_uses_tier3(self):
        result = self.mr.seleccionar_para_enriquecimiento(
            doc_type="contrato", chars=25000
        )
        assert result["tier"] == 3

    def test_enrichment_general_uses_tier2(self):
        result = self.mr.seleccionar_para_enriquecimiento(
            doc_type="general", chars=5000
        )
        assert result["tier"] == 2

    def test_override_model(self, monkeypatch):
        monkeypatch.setenv("MR_OVERRIDE_MODEL", "claude-opus-4-6")
        mr = ModelRouter()
        result = mr.seleccionar(
            chars=100, tiene_tablas=False,
            source_type="txt", doc_type="general"
        )
        assert result["modelo"] == "claude-opus-4-6"
        assert result.get("override") is True

    def test_all_tiers_have_required_fields(self):
        for tier_name, info in MODELOS.items():
            assert "modelo" in info
            assert "proveedor" in info
            assert "tier" in info
            assert "descripcion" in info
