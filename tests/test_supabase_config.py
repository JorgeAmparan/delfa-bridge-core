"""
B0.6 — Verifica que la ausencia de secrets de Supabase produce un fallo LOUD y
accionable (RuntimeError con mensaje claro), NO un error críptico ni un bug
silencioso que solo aparece en el primer request real en producción.

Histórico: el backend `docyan-lde-api` se desplegó sin `SUPABASE_URL` /
`SUPABASE_KEY` / `SUPABASE_SERVICE_KEY`. Como los tests existentes (a) inyectan
fakes vía `conftest.py` y (b) parchean `create_client`, la dependencia real
quedaba oculta y CI seguía verde. Estos tests cierran ese hueco: ejercitan el
camino sin secrets y exigen un error explícito.
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
from app.core.supabase_client import require_supabase_config

# ── Helper directo ───────────────────────────────────────────────────────────


class TestRequireSupabaseConfig:
    def test_returns_url_and_key_when_present(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
        monkeypatch.setenv("SUPABASE_KEY", "anon-key")
        url, key = require_supabase_config("TestModule")
        assert url == "https://x.supabase.co"
        assert key == "anon-key"

    def test_returns_service_key_when_service_true(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-key")
        url, key = require_supabase_config("auth", service=True)
        assert key == "service-key"

    def test_missing_url_raises_clear_runtime_error(self, monkeypatch):
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.setenv("SUPABASE_KEY", "anon-key")
        with pytest.raises(RuntimeError) as exc:
            require_supabase_config("EDB")
        msg = str(exc.value)
        assert "SUPABASE_URL" in msg
        assert "EDB" in msg
        # Mensaje accionable, no AttributeError críptico
        assert "required" in msg.lower()

    def test_missing_anon_key_raises_clear_runtime_error(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
        monkeypatch.delenv("SUPABASE_KEY", raising=False)
        with pytest.raises(RuntimeError) as exc:
            require_supabase_config("GRG")
        msg = str(exc.value)
        assert "SUPABASE_KEY" in msg
        assert "GRG" in msg

    def test_missing_service_key_names_service_var(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
        monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
        with pytest.raises(RuntimeError) as exc:
            require_supabase_config("auth", service=True)
        msg = str(exc.value)
        assert "SUPABASE_SERVICE_KEY" in msg
        assert "auth" in msg

    def test_empty_string_treated_as_missing(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "")
        monkeypatch.setenv("SUPABASE_KEY", "anon-key")
        with pytest.raises(RuntimeError):
            require_supabase_config("matrix")


# ── Módulos críticos: fallan loud al construirse sin secrets ─────────────────


class TestCriticalModulesFailLoud:
    """
    Cada módulo crítico debe lanzar RuntimeError (no AttributeError ni un error
    de red diferido) cuando falta SUPABASE_URL al instanciarse.
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

    def test_edb_fails_loud_without_key(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
        monkeypatch.delenv("SUPABASE_KEY", raising=False)
        with pytest.raises(RuntimeError, match="SUPABASE_KEY.*EDB"):
            EntityDataBrain(org_id="test")

    def test_auth_supabase_fails_loud_without_service_key(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
        monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
        with pytest.raises(RuntimeError, match="SUPABASE_SERVICE_KEY.*auth"):
            auth._supabase()
