#!/usr/bin/env bash
# ============================================================================
# restore_falkordb.sh — Restauración de FalkorDB (docyan-lde-graph). B1 §11.2.
# ============================================================================
# Wrapper deployable del motor portable `scripts/falkordb_backup.py`. Restaura
# cada grafo con Redis RESTORE (REPLACE) — en caliente, sin detener el proceso
# ni tocar el filesystem. Verifica integridad al final (PING + conteo de grafos).
#
# Uso:
#   ./scripts/restore_falkordb.sh --in /tmp/bundle.json     # desde archivo local
#   ./scripts/restore_falkordb.sh --date 20260530T120000Z   # descarga de Supabase
#
# Env: FALKOR_HOST, FALKOR_PORT, SUPABASE_URL, SUPABASE_SERVICE_KEY, BACKUP_BUCKET
# ============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON_BIN:-python3}"

MODE=""; ARG=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --in)   MODE="in";   ARG="${2:?}"; shift 2 ;;
    --date) MODE="date"; ARG="${2:?}"; shift 2 ;;
    *) echo "Argumento desconocido: $1" >&2; exit 2 ;;
  esac
done

cd "${REPO_ROOT}"
if [[ "${MODE}" == "in" ]]; then
  PYTHONPATH="${REPO_ROOT}" "${PY}" -m scripts.falkordb_backup restore --in "${ARG}"
elif [[ "${MODE}" == "date" ]]; then
  PYTHONPATH="${REPO_ROOT}" "${PY}" -m scripts.falkordb_backup restore --download "${ARG}"
else
  echo "Uso: $0 --in <bundle.json> | --date <TS>" >&2
  exit 2
fi

# Verificación de integridad post-restore (B1 §11.2).
PYTHONPATH="${REPO_ROOT}" "${PY}" - <<'PYEOF'
import os, redis
r = redis.Redis(host=os.getenv("FALKOR_HOST") or os.getenv("FALKORDB_HOST","localhost"),
                port=int(os.getenv("FALKOR_PORT") or os.getenv("FALKORDB_PORT","6379")))
assert r.ping(), "FalkorDB no responde PING tras restore"
n = sum(1 for _ in r.scan_iter(match="docyan_tenant_*"))
print(f"[restore] integridad OK — PING=True, grafos de tenant: {n}")
PYEOF
echo "[restore] OK"
