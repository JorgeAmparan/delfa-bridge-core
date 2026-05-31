"""
B1 §2.1 — Inicialización perezosa de genai.Client.

Verifica que `app.core.ri` y `app.core.intent` se importan SIN `GEMINI_API_KEY`
en el entorno (el cliente Gemini ya no se construye a nivel de módulo), y que
`get_genai_client()` es un singleton cacheado que solo se construye al invocarse.
"""
import subprocess
import sys

import pytest

# Módulos que B0 inicializaba con genai.Client() en import-time.
MODULES_LAZY = ["app.core.ri", "app.core.intent"]


@pytest.mark.parametrize("module_name", MODULES_LAZY)
def test_module_imports_without_gemini_api_key(module_name):
    """
    El módulo debe importar en un proceso limpio SIN GEMINI_API_KEY / GOOGLE_API_KEY.
    Antes de B1 esto fallaba: genai.Client() corría en import-time.
    """
    code = (
        "import os;"
        "os.environ.pop('GEMINI_API_KEY', None);"
        "os.environ.pop('GOOGLE_API_KEY', None);"
        f"import {module_name};"
        f"print('imported {module_name}')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Importar {module_name} sin GEMINI_API_KEY falló:\n{result.stderr}"
    )
    assert f"imported {module_name}" in result.stdout


def test_get_genai_client_is_cached_singleton(monkeypatch):
    """get_genai_client() cachea la instancia (lru_cache maxsize=1)."""
    from app.core import ri

    ri.get_genai_client.cache_clear()
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-lazy-test")

    c1 = ri.get_genai_client()
    c2 = ri.get_genai_client()
    assert c1 is c2  # mismo objeto: singleton cacheado


def test_intent_get_genai_client_is_cached_singleton(monkeypatch):
    from app.core import intent

    intent.get_genai_client.cache_clear()
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-lazy-test")

    assert intent.get_genai_client() is intent.get_genai_client()


def test_no_module_level_client_attribute():
    """
    Garantía de regresión: ya no existe el `client` global que requería la
    env var en import-time. Si reaparece, este test lo atrapa.
    """
    from app.core import intent, ri

    assert not hasattr(ri, "client"), "ri.py reintrodujo un client global (import-time)"
    assert not hasattr(intent, "client"), "intent.py reintrodujo un client global"
