"""
B0.6 + B0.7 — Verifica que la ausencia de secrets de Supabase produce un fallo
LOUD y accionable (RuntimeError con mensaje claro), NO un error críptico ni un
bug silencioso que solo aparece en el primer request real en producción.

B0.7: el backend usa SOLO `SUPABASE_SERVICE_KEY` (service_role) en el camino
crítico MVP. La anon key (`SUPABASE_KEY`) quedó eliminada del stack. Por eso los
módulos críticos ahora fallan loud por ausencia de `SUPABASE_SERVICE_KEY`.
Además, los módulos FUERA DE ALCANCE MVP (dii, billing, governance, documents,
mcp_server) están guardados con `require_module_enabled` y fallan loud salvo que
se setee `DOCYAN_ENABLE_<MODULE>=1`.

Histórico (por qué CI seguía verde): los tests existentes (a) inyectan fakes vía
`conftest.py` y (b) parchean `create_client`, ocultando la dependencia real.
Estos tests cierran ese hueco.
"""

import pytest

# Importados a nivel de módulo a propósito: cada uno corre su `load_dotenv()` de
# import UNA vez, en colección. Así, cuando un test hace `monkeypatch.delenv`,
# no se vuelve a importar el módulo y el `.env` local (si existe) no repuebla la
# variable. En CI no hay `.env`, por lo que el comportamiento es idéntico.
from app.api import auth
from app.core.edb import EntityDataBrain
from app.core.grg import GovernanceGuardrails
from app.core.matrix import TraceabilityMatrix
from app.core.supabase_client import require_module_enabled, require_supabase_config

# ── Helper require_supabase_config (default service_role en B0.7) ────────────


class TestRequireSupabaseConfig:
    def test_default_is_service_role(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-key")
        url, key = require_supabase_config("EDB")  # sin service= → default True
        assert url == "https://x.supabase.co"
        assert key == "service-key"

    def test_service_true_uses_service_key(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-key")
        _, key = require_supabase_config("auth", service=True)
        assert key == "service-key"

    def test_service_false_uses_anon_key_legacy(self, monkeypatch):
        # Modo legacy sin callers en MVP, pero el helper aún lo soporta.
        monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "anon-key")
        _, key = require_supabase_config("legacy", service=False)
        assert key == "anon-key"

    def test_missing_url_raises_clear_runtime_error(self, monkeypatch):
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-key")
        with pytest.raises(RuntimeError) as exc:
            require_supabase_config("EDB")
        msg = str(exc.value)
        assert "SUPABASE_URL" in msg
        assert "EDB" in msg
        assert "required" in msg.lower()

    def test_missing_service_key_raises(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
        monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
        with pytest.raises(RuntimeError) as exc:
            require_supabase_config("GRG")
        msg = str(exc.value)
        assert "SUPABASE_SERVICE_KEY" in msg
        assert "GRG" in msg

    def test_missing_anon_key_raises_only_in_legacy_mode(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
        monkeypatch.delenv("SUPABASE_KEY", raising=False)
        with pytest.raises(RuntimeError) as exc:
            require_supabase_config("legacy", service=False)
        assert "SUPABASE_KEY" in str(exc.value)

    def test_empty_string_treated_as_missing(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "")
        with pytest.raises(RuntimeError):
            require_supabase_config("matrix")


# ── Guard require_module_enabled (módulos fuera de alcance MVP) ──────────────


class TestRequireModuleEnabled:
    def test_disabled_by_default_raises(self, monkeypatch):
        monkeypatch.delenv("DOCYAN_ENABLE_DII", raising=False)
        with pytest.raises(RuntimeError) as exc:
            require_module_enabled("dii")
        msg = str(exc.value)
        assert "FUERA DE ALCANCE MVP" in msg
        assert "DOCYAN_ENABLE_DII" in msg
        assert "Adenda" in msg

    def test_enabled_with_flag_passes(self, monkeypatch):
        monkeypatch.setenv("DOCYAN_ENABLE_BILLING", "1")
        # No debe lanzar.
        require_module_enabled("billing")

    def test_flag_must_be_exactly_one(self, monkeypatch):
        monkeypatch.setenv("DOCYAN_ENABLE_GOVERNANCE", "true")
        with pytest.raises(RuntimeError):
            require_module_enabled("governance")


# ── Módulos críticos MVP: fallan loud al construirse sin service_role ────────


class TestCriticalModulesFailLoud:
    """
    edb / grg / matrix deben lanzar RuntimeError (no AttributeError ni error de
    red diferido) cuando falta SUPABASE_URL o SUPABASE_SERVICE_KEY al instanciarse.
    """

    def test_matrix_fails_loud_without_url(self, monkeypatch):
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        with pytest.raises(RuntimeError, match="SUPABASE_URL.*matrix"):
            TraceabilityMatrix(org_id="test")

    def test_grg_fails_loud_without_url(self, monkeypatch):
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        with pytest.raises(RuntimeError, match="SUPABASE_URL.*GRG"):
            GovernanceGuardrails(org_id="test")

    def test_edb_fails_loud_without_url(self, monkeypatch):
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        with pytest.raises(RuntimeError, match="SUPABASE_URL.*EDB"):
            EntityDataBrain(org_id="test")

    def test_edb_fails_loud_without_service_key(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
        monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
        with pytest.raises(RuntimeError, match="SUPABASE_SERVICE_KEY.*EDB"):
            EntityDataBrain(org_id="test")

    def test_matrix_fails_loud_without_service_key(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
        monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
        with pytest.raises(RuntimeError, match="SUPABASE_SERVICE_KEY.*matrix"):
            TraceabilityMatrix(org_id="test")

    def test_auth_supabase_fails_loud_without_service_key(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
        monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
        with pytest.raises(RuntimeError, match="SUPABASE_SERVICE_KEY.*auth"):
            auth._supabase()
