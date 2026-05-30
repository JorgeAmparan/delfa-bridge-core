#!/usr/bin/env bash
# ==============================================================================
# rename_panohayan_to_docyan.sh — Rebrand auditable Panohayan → DOCYAN (B0)
# ==============================================================================
# Renombra marca, siglas y strings de Panohayan a DOCYAN LDE en el código,
# infraestructura, strings, comentarios y documentación de PRODUCTO.
#
# NO toca (referencias históricas intencionales del propio rebrand):
#   - CLAUDE.md                       (glosario "Antes PKG/PTM", "❌ Panohayan")
#   - docs/adenda_postPoC_28mayo2026.md   (§1 "Rebrand: Panohayan → DOCYAN")
#   - docs/Plan_Desarrollo_MVP_DOCYAN_v2_postPoC.md  (registro de migración)
#   - docs/sprints/*.md               (Sprint Contracts — registro histórico)
#   - .claude/settings.local.json     (rutas/permisos locales de máquina)
#
# Idempotente: correr dos veces no cambia nada tras la primera pasada.
# Uso:   bash scripts/rename_panohayan_to_docyan.sh
#        bash scripts/rename_panohayan_to_docyan.sh --check   # solo reporta
# ==============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CHECK_ONLY=0
[[ "${1:-}" == "--check" ]] && CHECK_ONLY=1

# Lista curada de archivos a renombrar (producto, no registros históricos).
# Portable a bash 3.2 (macOS) — sin mapfile.
TARGETS=()
while IFS= read -r line; do
  TARGETS+=("$line")
done < <(
  {
    find app tests -type f \( -name '*.py' -o -name '*.html' -o -name '*.css' -o -name '*.js' \)
    printf '%s\n' \
      README.md DEPLOYMENT.md \
      docker-compose.yml fly.toml mcp_config.json .env.example \
      docs/quickstart.md docs/no-devs-guide.md docs/connectors_inventory.md
  } | sort -u
)

# Reemplazos ordenados: más específico → más genérico (se aplican en secuencia).
apply_subs() {
  perl -i -pe '
    s/PanohayanOrchestrator/DocyanOrchestrator/g;
    s/PanohayanDLE/DocyanLDE/g;
    s/Panohayan DLE\x{2122}/DOCYAN LDE\x{2122}/g;   # ™
    s/Panohayan DLE/DOCYAN LDE/g;
    s/Panohayan\x{2122}/DOCYAN\x{2122}/g;
    s/panohayan-dle-core/docyan-lde-core/g;
    s/panohayan-dle-api/docyan-lde-api/g;
    s/panohayan-dle/docyan-lde/g;
    s/panohayan-demo/docyan-demo/g;
    s/app\.panohayan\.com/app.docyan.com/g;
    s/\bpdle_/dlde_/g;                              # prefijo API key
    s/PANOHAYAN/DOCYAN/g;
    s/Panohayan/DOCYAN/g;
    s/panohayan/docyan/g;
  ' "$1"
}

changed=0
for f in "${TARGETS[@]}"; do
  [[ -f "$f" ]] || continue
  before="$(grep -ci panohayan "$f" || true)"
  if [[ "$before" -gt 0 ]]; then
    if [[ "$CHECK_ONLY" -eq 1 ]]; then
      echo "WOULD CHANGE ($before): $f"
    else
      apply_subs "$f"
      after="$(grep -ci panohayan "$f" || true)"
      echo "rebranded ($before → $after): $f"
    fi
    changed=$((changed + 1))
  fi
done

echo "----------------------------------------------------------------------"
if [[ "$CHECK_ONLY" -eq 1 ]]; then
  echo "Archivos pendientes de rebrand: $changed"
else
  echo "Archivos rebrandeados: $changed"
  remaining="$(grep -rli panohayan app tests README.md DEPLOYMENT.md \
      docker-compose.yml fly.toml mcp_config.json .env.example \
      docs/quickstart.md docs/no-devs-guide.md docs/connectors_inventory.md 2>/dev/null | wc -l | tr -d ' ')"
  echo "Ocurrencias residuales en targets de producto: $remaining (esperado 0)"
fi
