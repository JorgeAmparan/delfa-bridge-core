"""
Validación centralizada de la configuración de Supabase | DOCYAN™ (B0.6).

Histórico: múltiples módulos del backend (`edb`, `grg`, `matrix`, los routers de
API, `mcp_server`, etc.) construían el cliente Supabase con
`create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))`. Cuando esos
secrets faltan en producción, `os.getenv` devuelve `None` y el cliente termina
fallando con un error de la librería de Supabase poco accionable — o, peor, falla
recién en la primera operación de red. El gap quedaba SILENCIOSO hasta el primer
request real (incidente B0.6: el backend nunca se ejercitó más allá de `/health`).

Este helper convierte ese bug silencioso en un fallo LOUD y accionable, al estilo
de cómo `auth.py` valida `JWT_SECRET`. Cada módulo valida ANTES de construir el
cliente y obtiene un mensaje que dice exactamente qué variable falta y para qué
módulo.

Uso:

    from app.core.supabase_client import require_supabase_config
    from supabase import create_client

    url, key = require_supabase_config("EDB")
    self.supabase = create_client(url, key)

Para operaciones que necesitan service_role (bypass de RLS, p. ej. `auth`):

    url, key = require_supabase_config("auth", service=True)

Nota: se devuelve `(url, key)` y el módulo sigue llamando a su propio
`create_client` importado localmente. Esto preserva la testabilidad existente
(los tests parchean `app.core.<modulo>.create_client`) y mantiene el helper sin
dependencia de red.
"""

import os

# Variable de key por modo. SUPABASE_KEY = anon key (RLS aplicado);
# SUPABASE_SERVICE_KEY = service_role (bypass de RLS, solo backend de confianza).
_ANON_KEY_VAR = "SUPABASE_KEY"
_SERVICE_KEY_VAR = "SUPABASE_SERVICE_KEY"


def require_supabase_config(module: str, *, service: bool = False) -> tuple[str, str]:
    """
    Valida que la configuración de Supabase esté presente y la devuelve.

    Args:
        module: nombre legible del módulo que pide el cliente (para el mensaje
            de error, p. ej. "EDB", "GRG", "matrix", "auth").
        service: si True usa `SUPABASE_SERVICE_KEY` (service_role, bypass RLS);
            si False usa `SUPABASE_KEY` (anon).

    Returns:
        Tupla `(url, key)` lista para pasar a `create_client`.

    Raises:
        RuntimeError: si falta `SUPABASE_URL` o la key correspondiente. El
            mensaje nombra la variable exacta y el módulo afectado.
    """
    url = os.getenv("SUPABASE_URL")
    key_var = _SERVICE_KEY_VAR if service else _ANON_KEY_VAR
    key = os.getenv(key_var)

    if not url:
        raise RuntimeError(
            f"SUPABASE_URL is required for {module} but is not set. "
            f"Configure it as a Fly secret on docyan-lde-api "
            f"(ver docs/runbook_secrets_produccion.md)."
        )
    if not key:
        raise RuntimeError(
            f"{key_var} is required for {module} but is not set. "
            f"Configure it as a Fly secret on docyan-lde-api "
            f"(ver docs/runbook_secrets_produccion.md)."
        )

    return url, key
