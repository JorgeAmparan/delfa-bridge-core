# Sprint Contract B0 — Fundación, migración y rebrand

**Producto:** DOCYAN LDE — Live Document Environment by XCID
**Bloque:** B0 | **Ejecutor:** Opus 4.8 vía Claude Code CLI
**Modo:** Una aprobación + ejecución completa + un reporte final.
**Repo:** `panohayan-dle-core` → `docyan-lde-core`

---

## Prerequisitos
Ninguno. Bloque fundacional.

## Contexto para Opus
Estado del repo según auditoría 28 mayo 2026: backend Python/FastAPI funcional (DII 352 LOC, EDB, GRG 252, MR 98, RI/Intent, matrix/FAT 159), 37 conectores, auth JWT, 61 tests pytest pasando **en local sin pushear**, BGE-M3 client wired into EDB, `fly.toml` (app `panohayan-dle-api`), 1 migración SQL, CI workflow sin evidencia de correr, `railway.toml` legacy presente, CERO frontend, 221 ocurrencias de "Panohayan". Deuda de auditoría abril aún presente: JWT_SECRET default inseguro, dev API key hardcodeada, bug `sql.py:38` (`int()` sobre string vacío), CORS wildcard, Dockerfile `sed` frágil.

Este sprint cierra la fundación. Alcance completo — no se difiere nada.

## Alcance específico

1. **Push del trabajo previo.** Commitear y pushear a `main` el commit del Sprint B0 previo (61 tests, BGE-M3 client, fly.toml, migración).

2. **Rebrand completo** (221 ocurrencias). Decisiones confirmadas por Jorge:
   - Repo: `docyan-lde-core`. App Fly.io: `docyan-lde-api`. Grafo FalkorDB: `docyan`.
   - Clase `PanohayanOrchestrator` → `DocyanOrchestrator`.
   - Siglas: **PKG→DKG, PTM→DTM** en todo el código, strings, comentarios, docs.
   - Strings literales (~20), comentarios (~80), HTML demo (17), CLAUDE.md (74), DEPLOYMENT.md, fly.toml.
   - Script auditable `scripts/rename_panohayan_to_docyan.sh`. Los imports usan `from app.*` (no rompe imports).

3. **Eliminar Railway:** `railway.toml` + referencias residuales.

4. **Deuda de seguridad auditoría abril (corregir, no diferir):** eliminar JWT_SECRET default y dev API key hardcodeada; corregir bug `sql.py:38`; CORS por dominio (no wildcard); revisar Dockerfile `sed` frágil.

5. **Variables de entorno** en `.env.example`: `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`.

6. **6 migraciones SQL faltantes:** `002`-`007` para `documents`, `entities`, `audit_trail`, `governance_rules`, `quarantine`, `api_keys` (RLS multi-tenant donde aplique, consistente con `001`).

7. **`pyproject.toml`** migrando dependencias desde `requirements.txt`.

8. **Bootstrap completo del workspace frontend** (`frontend/`): Next.js 15 App Router + React 19 + Tailwind + shadcn/ui sobre Radix + react-i18next (ES-MX e inglés) + ESLint + Prettier + Vitest + Playwright. `package.json` raíz con scripts orquestadores. Página `/` placeholder "DOCYAN — boot OK" deployable.

9. **`vercel.json`** para deploy de `frontend/`.

10. **Pipeline OpenAPI 3.1 → TypeScript:** schemas Pydantic v2 exportan `openapi.json`; `frontend/scripts/generate-types.sh` genera `frontend/src/types/api.ts` con `openapi-typescript`.

11. **Deploy real verificado:** backend Fly.io (health 200), frontend Vercel (placeholder accesible HTTPS).

12. **CI ejecutado en GitHub Actions:** backend + frontend + lint en cada PR, verde verificado en CI (no solo local).

## Componentes a construir
- `scripts/rename_panohayan_to_docyan.sh`
- `migrations/002_documents.sql` a `007_api_keys.sql`
- `pyproject.toml`
- `frontend/` (estructura completa)
- `vercel.json`, `frontend/scripts/generate-types.sh`
- `.env.example` actualizado
- `DocyanOrchestrator` (rename)

## Tests automatizados requeridos
- Los 61 tests backend siguen pasando.
- 1 test de migración por tabla nueva (6) sobre DB limpia.
- Frontend: 1 test Vitest (import de componente shadcn/ui + toolchain corre).
- Frontend: 1 test E2E Playwright (`/` renderiza "DOCYAN — boot OK").
- CI: workflow ejecuta backend + frontend + lint en cada PR.

## Salida verificable
- `git ls-remote` → `docyan-lde-core`.
- `grep -ri "panohayan" .` = 0 (excluyendo `.git/`).
- `grep -rE "\bPKG\b|\bPTM\b" app/` = 0.
- `fly status` → `docyan-lde-api` running, health 200.
- `curl https://<vercel-url>/` → "DOCYAN — boot OK".
- `pytest tests/ -v` → 61+ pasando.
- `cd frontend && npm test` → 2+ pasando.
- CI último PR verde.
- 8 tablas con migraciones aplicadas.

## Notas para Opus sobre integración con código existente
- Paquete Python es `app`, no `panohayan` — rename es string-literal, no toca imports.
- NO eliminar los 37 conectores (no foco MVP, no se retiran en esta fase).
- NO tocar lógica de DII todavía — su retiro es B1.
- BGE-M3 client ya existe (`app/embeddings/bge_client.py`); no recrear.
- Corregir las 9 warnings de pytest si es trivial (7x InsecureKeyLengthWarning del JWT test, 1x PydanticDeprecatedSince20 en connectors.py); no son bloqueador.

## Reglas de ejecución
- No stubs, no mocks (excepto tests), no hardcoded. El placeholder "boot OK" es verificación de toolchain, legítimo.
- Tests desde este sprint. Sin tests = sprint no terminado.
- Verdad operacional. Bloqueador real → reportarlo, seguir con lo demás.
- Pendiente de modelado → PENDIENTE DE JORGE, continuar.

**Referencias:** doc 10 (Stack), doc 09 (Multi-tenant/RLS), Adenda secciones 1 y 3, auditoría 28 mayo 2026.
