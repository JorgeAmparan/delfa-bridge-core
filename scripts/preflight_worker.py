#!/usr/bin/env python3
"""
Preflight del worker de ingesta (B2.2 §1).

DOCYAN LDE™ by XCID.

Valida, ANTES de gastar en deploy, que todo el cableado del worker
`docyan-lde-ingest` es correcto. NO despliega nada: solo verifica y reporta.

Chequeos:
  1. Imports: worker.main, worker.ingest_pipeline, worker.llm_config sin error.
  2. Dependencias: pip install --dry-run de worker/requirements.txt (reporta conflictos).
  3. Env vars del worker documentadas en .env.example.
  4. worker/fly.toml: app=docyan-lde-ingest, región, SIN http_service público.
  5. worker/Dockerfile + fly.toml: build context correcto (aprendizaje B2.1/B2.2):
     dockerfile relativo al fly.toml ("Dockerfile") y COPY root-relative
     (app/, worker/) → deploy DESDE LA RAÍZ.

Uso:
    python scripts/preflight_worker.py
Sale 0 si todo verde; 1 si hay algún problema crítico.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import tomllib

REPO = pathlib.Path(__file__).resolve().parent.parent
WORKER = REPO / "worker"

# El paquete `worker` (y `app`) viven en la raíz del repo; al ejecutar el script
# por ruta (python scripts/preflight_worker.py) sys.path[0] es scripts/, no la
# raíz. Lo insertamos para que el chequeo [1] de imports funcione.
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# Env vars que el worker espera (Sprint B2 §4.3 / B2.2 §1).
WORKER_ENV_VARS = [
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "FALKOR_HOST",
    "FALKOR_PORT",
    "EMBEDDER_URL",
    "REDIS_QUEUE_URL",
]

OK = "✅"
FAIL = "❌"
WARN = "⚠️"


class Report:
    def __init__(self) -> None:
        self.problems: list[str] = []
        self.warnings: list[str] = []

    def check(self, ok: bool, label: str, detail: str = "") -> None:
        mark = OK if ok else FAIL
        print(f"  {mark} {label}" + (f" — {detail}" if detail else ""))
        if not ok:
            self.problems.append(f"{label}: {detail}")

    def warn(self, label: str, detail: str = "") -> None:
        print(f"  {WARN} {label}" + (f" — {detail}" if detail else ""))
        self.warnings.append(f"{label}: {detail}")


def check_imports(r: Report) -> None:
    print("\n[1] Imports del worker")
    for mod in ("worker.llm_config", "worker.ingest_pipeline", "worker.main"):
        try:
            __import__(mod)
            r.check(True, f"import {mod}")
        except Exception as exc:  # noqa: BLE001
            r.check(False, f"import {mod}", f"{type(exc).__name__}: {exc}")


def check_requirements(r: Report) -> None:
    print("\n[2] Dependencias (pip install --dry-run)")
    req = WORKER / "requirements.txt"
    if not req.exists():
        r.check(False, "worker/requirements.txt existe", "no encontrado")
        return
    r.check(True, "worker/requirements.txt existe")
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--dry-run", "-r", str(req)],
            capture_output=True, text=True, timeout=180,
        )
        out = (proc.stdout + proc.stderr)
        if proc.returncode == 0:
            r.check(True, "resolver pip sin conflictos (--dry-run)")
        else:
            # Extrae las líneas de conflicto para el reporte.
            conflict_lines = [
                ln for ln in out.splitlines()
                if any(k in ln.lower() for k in ("conflict", "incompatible", "error", "cannot install"))
            ]
            r.check(False, "resolver pip", "; ".join(conflict_lines[:4]) or "ver salida pip")
    except subprocess.TimeoutExpired:
        r.warn("resolver pip", "timeout 180s (red lenta); ejecutar manual antes del deploy")
    except Exception as exc:  # noqa: BLE001
        r.warn("resolver pip", f"{type(exc).__name__}: {exc}")


def check_env_example(r: Report) -> None:
    print("\n[3] Env vars del worker en .env.example")
    env = REPO / ".env.example"
    if not env.exists():
        r.check(False, ".env.example existe", "no encontrado")
        return
    text = env.read_text(encoding="utf-8")
    for var in WORKER_ENV_VARS:
        r.check(f"{var}=" in text, f"{var} documentada")


def check_fly_toml(r: Report) -> None:
    print("\n[4] worker/fly.toml")
    toml_path = WORKER / "fly.toml"
    if not toml_path.exists():
        r.check(False, "worker/fly.toml existe", "no encontrado")
        return
    try:
        cfg = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        r.check(False, "worker/fly.toml parsea (TOML válido)", f"{type(exc).__name__}: {exc}")
        return
    r.check(True, "worker/fly.toml parsea (TOML válido)")
    r.check(cfg.get("app") == "docyan-lde-ingest", "app = docyan-lde-ingest", str(cfg.get("app")))
    r.check(bool(cfg.get("primary_region")), "primary_region definido", str(cfg.get("primary_region")))
    # SIN http_service público.
    r.check("http_service" not in cfg, "sin [http_service] público (privado/flycast)")
    # Servicio interno en 8000.
    svcs = cfg.get("services", [])
    port_ok = any(s.get("internal_port") == 8000 for s in svcs)
    r.check(port_ok, "servicio interno en 8000")
    return cfg


def check_build_context(r: Report) -> None:
    print("\n[5] Build context (aprendizaje B2.1/B2.2)")
    toml_path = WORKER / "fly.toml"
    dockerfile = WORKER / "Dockerfile"
    if not toml_path.exists() or not dockerfile.exists():
        r.check(False, "fly.toml y Dockerfile existen", "falta alguno")
        return
    cfg = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    build = cfg.get("build", {})
    df = build.get("dockerfile")
    # Debe ser "Dockerfile" (relativo al fly.toml en worker/), NO "worker/Dockerfile".
    r.check(
        df == "Dockerfile",
        '[build].dockerfile == "Dockerfile" (relativo al fly.toml)',
        f'actual: {df!r} — "worker/Dockerfile" se resolvería a worker/worker/Dockerfile',
    )
    df_text = dockerfile.read_text(encoding="utf-8")
    # COPY root-relative: requiere build context = raíz del repo.
    has_copy_app = "COPY app " in df_text
    has_copy_worker = "COPY worker " in df_text
    r.check(has_copy_app and has_copy_worker,
            "Dockerfile usa COPY app/ y COPY worker/ (context = raíz)")
    # Base correcta.
    r.check("FROM python:3.11-slim" in df_text, "imagen base python:3.11-slim")
    # Que los paths del COPY existan en la raíz (context = raíz).
    r.check((REPO / "app").is_dir(), "directorio app/ existe en la raíz (context)")
    r.check((REPO / "worker" / "requirements.txt").is_file(),
            "worker/requirements.txt existe en la raíz (context)")
    print("    ↳ deploy: flyctl deploy --app docyan-lde-ingest --config worker/fly.toml (DESDE LA RAÍZ)")


def main() -> int:
    print("=" * 70)
    print("PREFLIGHT WORKER docyan-lde-ingest (B2.2) — NO despliega, solo valida")
    print("=" * 70)
    r = Report()
    check_imports(r)
    check_requirements(r)
    check_env_example(r)
    check_fly_toml(r)
    check_build_context(r)

    print("\n" + "=" * 70)
    if r.warnings:
        print(f"{WARN}  {len(r.warnings)} advertencia(s) (no bloquean):")
        for w in r.warnings:
            print(f"     - {w}")
    if r.problems:
        print(f"{FAIL}  PREFLIGHT FALLÓ — {len(r.problems)} problema(s):")
        for p in r.problems:
            print(f"     - {p}")
        print("=" * 70)
        return 1
    print(f"{OK}  PREFLIGHT VERDE — el worker está listo para deploy (lo ejecuta Jorge).")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
