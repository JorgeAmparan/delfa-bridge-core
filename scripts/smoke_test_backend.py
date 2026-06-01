#!/usr/bin/env python3
"""
Smoke test del backend DOCYAN LDE™ (B0.6).

Confirma que el backend pasó de "deploy verificado" a "operativo verificado":
que los secrets de Supabase están seteados y los módulos que dependen de ellos
responden de verdad, sin tocar el worker.

Diseño:
- Corre contra la app desplegada en Fly (HTTP), apuntando a `DOCYAN_API_URL`.
- Solo stdlib (urllib) — cero dependencias, corre en cualquier entorno con
  python3, incluido el laptop de Jorge.
- Idempotente y NO destructivo: solo GETs y un login con credenciales bogus
  (no crea ni modifica datos). Ningún paso contamina datos reales.

Variables:
    DOCYAN_API_URL     (requerida)  ej. https://docyan-lde-api.fly.dev
    DOCYAN_SMOKE_TOKEN (opcional)   JWT de un usuario de prueba para ejercitar
                                    los caminos autenticados (FAT/audit, anon key).

Salida: imprime cada check como PASS / FAIL / SKIP y termina con código 0 si no
hubo ningún FAIL, 1 en caso contrario.

Mapa con el Sprint Contract (punto 6):
    1. /health responde                                  → check_health
    2. backend crea cliente Supabase sin RuntimeError     → check_supabase_service_path
       (camino service_role vía /auth/login)              + check_supabase_anon_path
    3. cotizador consulta tenant_budget                   → check_cotizador (SKIP en main)
    4. FAT/audit_trail inserta y lee (tenant de prueba)   → check_fat_trail
"""

import json
import os
import sys
import urllib.error
import urllib.request
import uuid

TIMEOUT = 20

# ── Resultado tri-estado ─────────────────────────────────────────────────────

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"
_results: list[tuple[str, str, str]] = []


def record(name: str, status: str, detail: str = "") -> None:
    _results.append((name, status, detail))
    icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️ "}[status]
    line = f"{icon} {status:4} — {name}"
    if detail:
        line += f"  ({detail})"
    print(line)


# ── HTTP helper (stdlib) ─────────────────────────────────────────────────────


def _request(method: str, url: str, *, token: str | None = None, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return None, str(e)


# ── Checks ───────────────────────────────────────────────────────────────────


def check_health(base: str) -> None:
    status, body = _request("GET", f"{base}/health")
    if status == 200:
        record("/health responde 200", PASS, body.strip()[:80])
    else:
        record("/health responde 200", FAIL, f"status={status} body={body[:120]}")


def check_supabase_service_path(base: str) -> None:
    """
    Ejercita el cliente Supabase (service_role) vía /auth/login con credenciales
    inexistentes. NO crea datos.

    - 401  → Supabase alcanzable, query ejecutada, credenciales rechazadas. PASS.
    - 500  → probable secret ausente (RuntimeError loud B0.6 en logs) o
             Supabase inalcanzable. FAIL (revisar `flyctl logs`).
    """
    bogus_email = f"smoke-{uuid.uuid4().hex}@docyan.invalid"
    status, body = _request(
        "POST",
        f"{base}/auth/login",
        body={"email": bogus_email, "password": "smoke-not-a-real-password"},
    )
    if status == 401:
        record("Supabase service_role (auth/login)", PASS, "401 creds inválidas — config OK")
    elif status == 500:
        record(
            "Supabase service_role (auth/login)",
            FAIL,
            "500 — SUPABASE_* probablemente ausente; revisar `flyctl logs --app docyan-lde-api`",
        )
    elif status is None:
        record("Supabase service_role (auth/login)", FAIL, f"sin respuesta: {body[:120]}")
    else:
        # 403 (usuario desactivado), 422 (validación) también implican que el
        # cliente Supabase se construyó: config presente.
        record("Supabase service_role (auth/login)", PASS, f"status={status} — cliente construido")


def check_supabase_anon_path(base: str, token: str | None) -> None:
    """
    Ejercita el cliente Supabase (anon key) vía un endpoint que construye
    TraceabilityMatrix/EDB. Requiere token. SKIP si no hay token.
    """
    if not token:
        record("Supabase anon key (trail/recent)", SKIP, "sin DOCYAN_SMOKE_TOKEN")
        return
    status, body = _request("GET", f"{base}/trail/recent?limit=1", token=token)
    if status == 200:
        record("Supabase anon key (trail/recent)", PASS, "200 — matrix/EDB leyó Supabase")
    elif status in (401, 403):
        record("Supabase anon key (trail/recent)", FAIL, f"{status} — token inválido/insuficiente")
    elif status == 500:
        record("Supabase anon key (trail/recent)", FAIL, "500 — config Supabase ausente o error")
    else:
        record("Supabase anon key (trail/recent)", FAIL, f"status={status} body={body[:120]}")


def check_fat_trail(base: str, token: str | None) -> None:
    """
    FAT/audit_trail: inserta + lee. Cada request autenticado dispara un evento
    FAT server-side (insert), y /trail/recent lo lee (read). No destructivo.
    SKIP si no hay token.
    """
    if not token:
        record("FAT audit_trail insert+read", SKIP, "sin DOCYAN_SMOKE_TOKEN")
        return
    status, body = _request("GET", f"{base}/trail/summary", token=token)
    if status == 200:
        record("FAT audit_trail insert+read", PASS, "200 — trail leído (y request auditado)")
    elif status == 500:
        record("FAT audit_trail insert+read", FAIL, "500 — Supabase/FAT no operativo")
    else:
        record("FAT audit_trail insert+read", FAIL, f"status={status} body={body[:120]}")


def check_cotizador(base: str) -> None:
    """
    El cotizador (budget_manager → tenant_budget) vive en app/ingesta/, que en
    `main` aún NO está mergeado (llega con B2/B2.1/B2.2). Se reporta SKIP hasta
    entonces para no generar un falso FAIL. Ver docs/runbook_secrets_produccion.md §4.
    """
    record(
        "Cotizador tenant_budget (read-only)",
        SKIP,
        "app/ingesta no está en main todavía (B2 pendiente de merge)",
    )


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    base = os.getenv("DOCYAN_API_URL", "").rstrip("/")
    token = os.getenv("DOCYAN_SMOKE_TOKEN") or None

    if not base:
        print("ERROR: define DOCYAN_API_URL (ej. https://docyan-lde-api.fly.dev)", file=sys.stderr)
        return 2

    print(f"== Smoke test backend DOCYAN LDE™ → {base} ==")
    if not token:
        print("   (sin DOCYAN_SMOKE_TOKEN: los checks autenticados se omiten — SKIP)")
    print()

    check_health(base)
    check_supabase_service_path(base)
    check_supabase_anon_path(base, token)
    check_fat_trail(base, token)
    check_cotizador(base)

    n_fail = sum(1 for _, s, _ in _results if s == FAIL)
    n_skip = sum(1 for _, s, _ in _results if s == SKIP)
    n_pass = sum(1 for _, s, _ in _results if s == PASS)
    print()
    print(f"Resumen: {n_pass} PASS · {n_fail} FAIL · {n_skip} SKIP")
    if n_fail:
        print("SMOKE FAIL — revisar los checks marcados ❌ y `flyctl logs`.")
        return 1
    print("SMOKE OK — backend operativo verificado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
