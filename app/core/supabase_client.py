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

# B0.7: el backend usa SOLO `SUPABASE_SERVICE_KEY` (service_role). El aislamiento
# multi-tenant es a nivel de query (Doc 09) y la integridad del FAT la protege el
# hash chain SHA-256 (Doc 08), no las RLS de Supabase. La anon key
# (`SUPABASE_KEY`) quedó ELIMINADA del stack del backend — el frontend nunca
# habla directo con Supabase. Ver docs/DOCYAN_Adenda_Alcance_MVP_ConsultaViva.md.
_SERVICE_KEY_VAR = "SUPABASE_SERVICE_KEY"
_ANON_KEY_VAR = "SUPABASE_KEY"  # legacy; solo si service=False (no usado en MVP).


def require_supabase_config(module: str, *, service: bool = True) -> tuple[str, str]:
    """
    Valida que la configuración de Supabase esté presente y la devuelve.

    Args:
        module: nombre legible del módulo que pide el cliente (para el mensaje
            de error, p. ej. "EDB", "GRG", "matrix", "auth").
        service: B0.7 default True → usa `SUPABASE_SERVICE_KEY` (service_role).
            `service=False` (anon `SUPABASE_KEY`) queda como modo legacy sin
            callers en el backend MVP.

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


def require_module_enabled(module: str) -> None:
    """
    Guard para módulos FUERA DE ALCANCE MVP Consulta Viva (Adenda 31-may-2026).

    Estos módulos (`dii`, `billing`, `governance`, `documents`, `mcp_server`) no
    son parte del MVP de validación. Quedan en el árbol pero NO deben ejecutarse
    en producción MVP. Si se invocan sin habilitarlos explícitamente, fallan loud
    con un mensaje accionable en vez de correr con configuración no diseñada para
    ese flujo.

    Para reactivar un módulo en su sprint específico (o en un test que lo
    ejercite a propósito), set `DOCYAN_ENABLE_<MODULE>=1` en el entorno.

    Args:
        module: identificador del módulo (p. ej. "dii", "billing"). El flag es
            `DOCYAN_ENABLE_<MODULE-EN-MAYÚSCULAS>`.

    Raises:
        RuntimeError: si el flag de habilitación no está en "1".
    """
    flag = f"DOCYAN_ENABLE_{module.upper()}"
    if os.getenv(flag) != "1":
        raise RuntimeError(
            f"{module} está FUERA DE ALCANCE MVP Consulta Viva "
            f"(Adenda 31-may-2026) y está deshabilitado en producción. "
            f"Para reactivarlo en su sprint, set {flag}=1. "
            f"Ver docs/DOCYAN_Adenda_Alcance_MVP_ConsultaViva.md."
        )
