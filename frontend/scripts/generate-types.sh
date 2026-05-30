#!/usr/bin/env bash
# ==============================================================================
# generate-types.sh — Pipeline contrato OpenAPI 3.1 (Pydantic v2) → TypeScript
# ==============================================================================
# 1. Exporta el OpenAPI 3.1 del backend FastAPI (schemas Pydantic v2) a openapi.json.
# 2. Corre openapi-typescript sobre ese contrato → frontend/src/types/api.ts.
#
# Regla (CLAUDE.md §2.5): los tipos del frontend SIEMPRE se derivan del contrato
# del backend; nunca se hardcodean. Regenerar en CI antes del build del frontend.
#
# Uso:  bash frontend/scripts/generate-types.sh
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT_DIR="$(cd "$FRONTEND_DIR/.." && pwd)"
OPENAPI_JSON="$ROOT_DIR/openapi.json"
OUT_TS="$FRONTEND_DIR/src/types/api.ts"

# Intérprete: venv del repo si existe, si no python3 del sistema.
PY="python3"
if [[ -x "$ROOT_DIR/venv/bin/python" ]]; then
  PY="$ROOT_DIR/venv/bin/python"
fi

echo "[gen-types] Exportando OpenAPI 3.1 desde el backend FastAPI…"
# Env mínimo para poder importar la app sin un entorno real.
JWT_SECRET="${JWT_SECRET:-gen-types-dummy-secret-not-used-at-runtime}" \
ALLOWED_ORIGINS="${ALLOWED_ORIGINS:-http://localhost:3000}" \
SUPABASE_URL="${SUPABASE_URL:-https://example.supabase.co}" \
SUPABASE_KEY="${SUPABASE_KEY:-dummy}" \
SUPABASE_SERVICE_KEY="${SUPABASE_SERVICE_KEY:-dummy}" \
ORG_ID="${ORG_ID:-gen-types}" \
GEMINI_API_KEY="${GEMINI_API_KEY:-gen-types-dummy}" \
OPENAI_API_KEY="${OPENAI_API_KEY:-gen-types-dummy}" \
BGE_M3_URL="${BGE_M3_URL:-http://localhost:8080}" \
REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}" \
FALKORDB_HOST="${FALKORDB_HOST:-localhost}" \
"$PY" - "$OPENAPI_JSON" <<'PY'
import json
import sys

from app.api.main import app

spec = app.openapi()
with open(sys.argv[1], "w", encoding="utf-8") as fh:
    json.dump(spec, fh, ensure_ascii=False, indent=2)
print(f"[gen-types] OpenAPI {spec.get('openapi')} con {len(spec.get('paths', {}))} paths → {sys.argv[1]}")
PY

echo "[gen-types] Generando tipos TypeScript con openapi-typescript…"
cd "$FRONTEND_DIR"
npx --yes openapi-typescript "$OPENAPI_JSON" -o "$OUT_TS"

echo "[gen-types] OK → $OUT_TS"
