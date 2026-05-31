#!/usr/bin/env bash
# ============================================================================
# backup_falkordb.sh — Respaldo de FalkorDB (docyan-lde-graph). DOCYAN LDE™ — B1 §11.
# ============================================================================
# Wrapper deployable del motor portable `scripts/falkordb_backup.py` (redis-py
# DUMP por grafo — NO requiere redis-cli ni acceso al filesystem de la máquina).
#
# Almacenamiento externo (B1 §11.1): Supabase Storage — cero vendor nuevo, reusa
# SUPABASE_SERVICE_KEY; retención por lifecycle del bucket (7a/3a, decisión #12).
# Apto para cron cada 15 min (RPO 15 min, #12) desde el backend o un Fly machine.
#
# Uso:
#   ./scripts/backup_falkordb.sh                       # bundle local + upload Supabase
#   ./scripts/backup_falkordb.sh --out /tmp/b.json     # solo local (tests/CI)
#
# Env: FALKOR_HOST, FALKOR_PORT, SUPABASE_URL, SUPABASE_SERVICE_KEY, BACKUP_BUCKET
# ============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON_BIN:-python3}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"

OUT=""
UPLOAD=1
while [[ $# -gt 0 ]]; do
  case "$1" in
    --out) OUT="${2:?}"; UPLOAD=0; shift 2 ;;
    --no-upload) UPLOAD=0; shift ;;
    *) echo "Argumento desconocido: $1" >&2; exit 2 ;;
  esac
done
OUT="${OUT:-/tmp/docyan-falkordb-${TS}.json}"

cd "${REPO_ROOT}"
if [[ "${UPLOAD}" -eq 1 ]]; then
  PYTHONPATH="${REPO_ROOT}" "${PY}" -m scripts.falkordb_backup backup --out "${OUT}" --upload
else
  PYTHONPATH="${REPO_ROOT}" "${PY}" -m scripts.falkordb_backup backup --out "${OUT}"
fi
echo "[backup] OK → ${OUT}"
