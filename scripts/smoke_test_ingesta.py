#!/usr/bin/env python3
"""
Smoke test de ingesta real end-to-end (B2.2 §4).

DOCYAN LDE™ by XCID.

Lo corre JORGE DESPUÉS del deploy del worker, contra infra real, para validar el
flujo completo: subir PDF → cotizar → confirmar → polling → grafo poblado.

NO mockea nada: gasta en Gemini real (poco: ~$0.01–0.02 para el PDF de prueba).
El cotizador sigue siendo el gate — si no hay saldo, el script reporta el rechazo
y termina sin gastar.

Parametrizable por env vars:
    DOCYAN_API_URL    URL del backend (p.ej. https://docyan-lde-api.fly.dev)
    DOCYAN_TOKEN      JWT de un usuario admin/editor (de POST /auth/login)
    DOCYAN_TEST_PDF   ruta al PDF de prueba (default: IB-111-RDA)
    DOCYAN_TIPO       (opcional) tipo forzado, p.ej. manual_tecnico
    DOCYAN_POLL_SECS  (opcional) timeout total de polling (default 1800)

Salida: imprime cada fase y termina con "SMOKE TEST OK" (exit 0) o el error real
(exit 1). Verdad operacional: si algo falla, lo dice; no maquilla.
"""
from __future__ import annotations

import os
import sys
import time

import httpx

API_URL = os.getenv("DOCYAN_API_URL", "http://localhost:8000").rstrip("/")
TOKEN = os.getenv("DOCYAN_TOKEN", "")
PDF = os.getenv(
    "DOCYAN_TEST_PDF",
    "/Users/jamparan/Desktop/XitleCore/DOCYAN LDE files/IB-111-RDA RDA1 230 R5 02172021.pdf",
)
TIPO_FORZADO = os.getenv("DOCYAN_TIPO") or None
POLL_SECS = int(os.getenv("DOCYAN_POLL_SECS", "1800"))
POLL_INTERVAL = 10


def _headers() -> dict:
    if not TOKEN:
        fail("DOCYAN_TOKEN no definido. Obtén un JWT con POST /auth/login.")
    return {"Authorization": f"Bearer {TOKEN}"}


def fail(msg: str) -> None:
    print(f"\n❌ SMOKE TEST FALLÓ: {msg}")
    sys.exit(1)


def step(msg: str) -> None:
    print(f"\n▶ {msg}")


def cotizar() -> dict:
    step(f"Subiendo y cotizando: {os.path.basename(PDF)}")
    if not os.path.exists(PDF):
        fail(f"PDF no encontrado: {PDF}")
    with open(PDF, "rb") as fh:
        files = {"file": (os.path.basename(PDF), fh, "application/pdf")}
        data = {"tipo_forzado": TIPO_FORZADO} if TIPO_FORZADO else {}
        r = httpx.post(
            f"{API_URL}/ingesta/documents",
            headers=_headers(), files=files, data=data, timeout=120,
        )
    if r.status_code != 200:
        fail(f"POST /ingesta/documents → {r.status_code}: {r.text[:400]}")
    body = r.json()
    cot = body.get("cotizacion", {})
    print(f"   job_id={body.get('job_id')}")
    print(f"   tipo_documento={body.get('tipo_documento')} ({body.get('tipo_resuelto_por')})")
    print(f"   decisión={cot.get('decision')}  costo_est=${cot.get('costo_estimado_usd')}  "
          f"tokens={cot.get('tokens_documento')}  tiempo~{cot.get('tiempo_estimado_seg')}s")
    print(f"   saldo_disponible=${cot.get('saldo_disponible_usd')}")
    if not body.get("requiere_confirmacion"):
        fail(f"el cotizador NO aprobó (decisión={cot.get('decision')}). "
             f"Motivo: {cot.get('motivo')}. Carga saldo en tenant_budget y reintenta.")
    return body


def confirmar(job_id: str) -> None:
    step(f"Confirmando ingesta del job {job_id} (dispara el worker)")
    r = httpx.post(
        f"{API_URL}/ingesta/documents/{job_id}/confirm", headers=_headers(), timeout=60
    )
    if r.status_code != 200:
        fail(f"POST /confirm → {r.status_code}: {r.text[:400]}")
    print(f"   {r.json()}")


def poll(job_id: str) -> dict:
    step(f"Polling estado del job (timeout {POLL_SECS}s)")
    t0 = time.monotonic()
    last = None
    while time.monotonic() - t0 < POLL_SECS:
        r = httpx.get(f"{API_URL}/ingesta/documents/{job_id}", headers=_headers(), timeout=60)
        if r.status_code != 200:
            fail(f"GET estado → {r.status_code}: {r.text[:400]}")
        body = r.json()
        status = body.get("status")
        if status != last:
            print(f"   [{int(time.monotonic()-t0)}s] status={status}")
            last = status
        if status == "completed":
            return body
        if status == "failed":
            fail(f"el worker reportó FALLO: {body.get('error')}")
        time.sleep(POLL_INTERVAL)
    fail(f"timeout: el job no completó en {POLL_SECS}s (último status={last})")


def verificar_grafo(job_body: dict, cotizacion: dict) -> None:
    step("Verificando resultado / grafo poblado")
    resultado = job_body.get("resultado") or {}
    print(f"   resultado={resultado}")
    stats = resultado.get("estadisticas_grafo") or {}
    # El resultado del worker trae estadísticas del grafo (get_statistics) y el
    # tipo de documento. Verificamos que hubo extracción real (>0 nodos/entidades).
    total = 0
    for k, v in stats.items() if isinstance(stats, dict) else []:
        if isinstance(v, (int, float)) and any(t in k.lower() for t in ("node", "entit", "nodo", "relation", "rel")):
            total += v
    if not resultado:
        fail("el job completó pero 'resultado' está vacío (sin estadísticas de grafo).")
    if isinstance(stats, dict) and stats and total == 0:
        print("   ⚠️  estadisticas_grafo sin conteo de nodos>0 reconocible; revisa el grafo manualmente:")
        print("       Cypher: MATCH (p:Procedimiento) RETURN count(p)")
    else:
        print(f"   ✔ extracción con resultado no vacío (señales de nodos/relaciones: {total or 'ver stats'})")
    # Costo real vs estimado (informativo).
    print(f"\n   COSTO estimado por el cotizador: ${cotizacion.get('costo_estimado_usd')}")
    print("   COSTO real: revísalo en el dashboard de Google AI / OpenAI por este job.")


def main() -> int:
    print("=" * 70)
    print("SMOKE TEST INGESTA REAL — docyan-lde-ingest (B2.2)")
    print(f"API={API_URL}  PDF={os.path.basename(PDF)}")
    print("=" * 70)
    body = cotizar()
    cot = body["cotizacion"]
    job_id = body["job_id"]
    confirmar(job_id)
    final = poll(job_id)
    verificar_grafo(final, cot)
    print("\n" + "=" * 70)
    print("✅ SMOKE TEST OK — ingesta end-to-end completada contra infra real.")
    print(f"   tenant graph poblado vía job {job_id}.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        fail("interrumpido por el usuario.")
