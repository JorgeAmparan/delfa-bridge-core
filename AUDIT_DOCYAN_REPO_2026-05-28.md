# Auditoría de Estado del Repo — DOCYAN (ex-Panohayan / delfa-bridge-core)

**Fecha:** 2026-05-28
**Commit:** `81a6f8eb2271b2e2b11afd050022c0fe16ea3444`
**Rama:** `main`

**Resumen en 3 líneas:**
El repo tiene un backend Python/FastAPI funcional con 5 módulos core (DII, EDB, GRG, MR, RI/Intent), 37 conectores, auth JWT, y 61 tests pytest pasando. No existe ningún código de GraphRAG-SDK, no existe frontend, no existen los componentes planificados post-B0 (PKG schema, PTM, QR tokens, lock terminológico, UIs, WhatsApp, alineadores). El PoC NOM-052/LGPGIR dejó solo un documento de decisiones (`CLAUDE_8.md`) — cero código materializado en el repo.

---

## Eje 1 — Inventario estructural

### Estructura de directorios (3 niveles, excluidos venv/.git/__pycache__)

```
.
├── .github/workflows/          # CI/CD
│   ├── ci.yml
│   └── deploy.yml
├── app/
│   ├── api/
│   │   ├── auth.py
│   │   ├── main.py
│   │   └── routers/            # 7 routers
│   ├── cache/
│   │   └── redis_client.py
│   ├── connectors/             # 37 connector files
│   ├── core/
│   │   ├── dii.py
│   │   ├── edb.py
│   │   ├── grg.py
│   │   ├── intent.py
│   │   ├── matrix.py
│   │   ├── mr.py
│   │   └── ri.py
│   ├── demo/
│   │   └── index.html
│   ├── embeddings/
│   │   └── bge_client.py
│   ├── graph/
│   │   └── falkor_client.py
│   ├── main.py                 # PanohayanOrchestrator
│   ├── mcp_server.py
│   └── static/assets/
├── data/                       # 1 test PDF
├── docs/                       # 3 markdown docs
├── migrations/                 # 1 SQL migration
├── scripts/
│   └── sync-docker-reqs.sh
├── tests/                      # 10 test files
├── CLAUDE.md
├── CLAUDE_8.md                 # Post-PoC decisions (untracked)
├── DEPLOYMENT.md
├── Dockerfile
├── docker-compose.yml
├── fly.toml
├── mcp_config.json
├── railway.toml                # Legacy — Railway config still present
├── requirements.txt
└── requirements.docker.txt
```

### Conteo de archivos por lenguaje

| Extensión | Archivos |
|-----------|----------|
| .py       | 77       |
| .md       | 8        |
| .yml      | 3        |
| .html     | 1        |
| .sql      | 1        |
| .sh       | 1        |
| .json     | 2        |
| .toml     | 2        |

### Frameworks y versiones declaradas (de `requirements.txt`)

| Framework/Lib  | Versión        |
|----------------|----------------|
| FastAPI        | 0.135.3        |
| Pydantic       | 2.12.5         |
| uvicorn        | 0.42.0         |
| Docling        | 2.84.0         |
| LlamaIndex     | 0.14.19        |
| LangExtract    | 1.2.0          |
| Anthropic SDK  | 0.87.0         |
| Google GenAI   | 1.70.0         |
| OpenAI SDK     | 2.30.0         |
| Supabase       | 2.28.3         |
| torch          | 2.11.0         |
| transformers   | 5.4.0          |
| MCP            | 1.27.0         |

**No existe `pyproject.toml`.** Dependencias gestionadas solo vía `requirements.txt` (214 líneas, frozen pins).

### Archivos de configuración presentes

| Archivo | Presente |
|---------|----------|
| `pyproject.toml` | **NO** |
| `package.json` | **NO** |
| `Dockerfile` | Sí — multi-stage build |
| `fly.toml` | Sí — app `panohayan-dle-api`, region `mia` |
| `vercel.json` | **NO** |
| `.env.example` | Sí — 31 variables |
| `railway.toml` | Sí — legacy, aún presente |
| `.github/workflows/ci.yml` | Sí |
| `.github/workflows/deploy.yml` | Sí |

---

## Eje 2 — Componentes core

### 1. DII — Document Ingestion Intelligence

- **Estado:** Presente.
- **Ruta:** `app/core/dii.py`
- **LOC reales:** 352 (non-comment, non-blank).
- **Referencia previa:** Auditoría 25-abr-2026 reportó 1,759 líneas. La diferencia se debe a que el conteo previo probablemente incluía comentarios, docstrings y líneas en blanco, o el archivo fue refactorizado. Verificado: el archivo actual tiene 446 líneas totales incluyendo todo.
- **Estado funcional:** Pipeline completo: Docling → clasificador → Intent-A → LangExtract + LlamaIndex → enrichment LLM → Supabase. **Depende de Supabase (tables: documents, entities), Google GenAI, y LangExtract.** Tiene tests (12 tests en `test_dii.py`) que cubren clasificador, extensiones e init con mocks. **No hay test de pipeline end-to-end.**
- **El PoC post-28-mayo (`CLAUDE_8.md`) declara que DII se reemplaza por GraphRAG-SDK.** Este reemplazo no se ha ejecutado en código.

### 2. GRG — Guardrail Governance

- **Estado:** Presente.
- **Ruta:** `app/core/grg.py`
- **LOC reales:** 252.
- **Referencia previa:** 307 líneas (auditoría). Consistente (diferencia es comentarios/blanks).
- **Estado funcional:** Evalúa entidades contra reglas configurables (block, flag, require_approval, redact). Cache TTL para reglas. **Depende de Supabase (tables: governance_rules, entities, quarantine).** Sin tests propios. Sin TODOs.

### 3. FAT — Foundation Audit Trail

- **Estado:** Presente, bajo el nombre `TraceabilityMatrix`.
- **Ruta:** `app/core/matrix.py`
- **LOC reales:** 159.
- **Referencia previa:** 196 líneas. Consistente.
- **Estado funcional:** Log centralizado en Supabase tabla `audit_trail`. Consultas por documento, entidad, actividad reciente. **Depende de Supabase.** Sin tests propios. No implementa hash chain SHA-256 mencionado en el plan (B6).

### 4. MR — Model Router

- **Estado:** Presente.
- **Ruta:** `app/core/mr.py`
- **LOC reales:** 98.
- **Referencia previa:** 135 líneas. Consistente.
- **Estado funcional:** 4 tiers (Gemini Flash, Gemini Flash, Claude Sonnet 4.6, Claude Opus 4.6). Override vía env var. **No depende de servicios externos — solo selecciona, no invoca.** Tiene tests completos (10 tests en `test_mr.py`). Funcional.

### 5. Master Orchestrator

- **Estado:** Presente, básico.
- **Ruta:** `app/main.py` (clase `PanohayanOrchestrator`)
- **LOC reales:** 129.
- **Estado funcional:** Orquesta DII → EDB → GRG → TM secuencialmente. Modo CLI para procesar o buscar. **No es el Master Orchestrator del plan B3** (que incluye QR tokens, sesiones Redis, pipelines por intención). Es un script de coordinación simple.

### 6. Integración con FalkorDB

- **Estado:** Skeleton only.
- **Ruta:** `app/graph/falkor_client.py`
- **LOC reales:** 34.
- **Estado funcional:** Client wrapper con `connect()`, `query()`, `health()`. **No es usado por ningún otro módulo.** Nada escribe ni lee del grafo. No hay schema PKG ni PTM. Solo se referencia en tests de conectividad.

### 7. Integración con GraphRAG-SDK

- **Estado:** **AUSENTE.**
- `graphrag-sdk` no está en `requirements.txt` ni en `requirements.docker.txt`.
- No existe ningún archivo `.py` que importe o referencie GraphRAG-SDK.
- `CLAUDE_8.md` documenta la decisión de usar GraphRAG-SDK 1.1.1 para reemplazar DII, pero **cero código materializado**.
- No existen scripts del PoC en el repo.

### 8. Integración con Supabase / PostgreSQL

- **Estado:** Presente, extensa.
- **Archivos que usan `create_client` o `.table()`:** `app/core/dii.py`, `app/core/edb.py`, `app/core/grg.py`, `app/core/matrix.py`, `app/api/auth.py`, `app/main.py`, `app/mcp_server.py`, y al menos 6 conectores.
- **Tablas referenciadas en código:** `documents`, `entities`, `audit_trail`, `governance_rules`, `quarantine`, `users`, `refresh_tokens`, `api_keys`.
- **Migración:** 1 archivo: `migrations/001_users_and_refresh_tokens.sql` (tablas `users` y `refresh_tokens` con RLS).
- **Estado funcional:** La integración funciona pero las tablas `documents`, `entities`, `audit_trail`, `governance_rules`, `quarantine`, `api_keys` no tienen migraciones en el repo. Se presumen creadas manualmente en Supabase.

### 9. Integración con Redis

- **Estado:** Skeleton only.
- **Ruta:** `app/cache/redis_client.py`
- **LOC reales:** 38.
- **Estado funcional:** Client wrapper con get/set/json/health. **No es usado por ningún otro módulo.** No hay sesiones MO implementadas. No hay APScheduler.

### 10. Integración con BGE-M3

- **Estado:** Client creado, wired into EDB.
- **Ruta:** `app/embeddings/bge_client.py`
- **LOC reales:** 38.
- **Estado funcional:** HTTP client que apunta a `BGE_M3_URL` env var. `app/core/edb.py` importa y usa `bge_client` para generar embeddings. **Reemplaza la dependencia de OpenAI `text-embedding-3-small` que existía antes del Sprint B0.** Sin embargo, `requirements.txt` aún lista `openai==2.30.0` y `llama-index-embeddings-openai==0.6.0`. El import `from openai import OpenAI` fue eliminado de `edb.py` pero `openai` sigue como dependencia instalada.

### 11. Alineadores bilingües (Vecalign, Hunalign)

- **Estado:** **AUSENTE.**
- `grep` para vecalign, hunalign, fuzzywuzzy, rapidfuzz, thefuzz: 0 resultados en todo el repo.

### 12. Matching fuzzy (Levenshtein, híbrido)

- **Estado:** **AUSENTE.**
- 0 resultados para levenshtein, fuzzywuzzy, rapidfuzz, thefuzz.

### 13. Frontend Next.js / React

- **Estado:** **AUSENTE.**
- No existe `package.json`, carpeta `frontend/`, carpeta `apps/`, ni `next.config.*`.
- El único HTML es `app/demo/index.html` (portal demo server-rendered, ~900 líneas).

---

## Eje 3 — Estado de tests

- **Total de tests automatizados:** 61 (todos pytest).
- **Cobertura medida:** No hay configuración de coverage (`pytest-cov` no está en dependencies, no hay `pytest.ini`, `setup.cfg` ni `pyproject.toml` con coverage config). **No medida.**
- **Ratio backend/frontend:** 100% backend / 0% frontend (no existe frontend).
- **¿Corre sin errores?** Sí.
  ```
  /opt/homebrew/bin/python3.11 -m pytest tests/ -v --tb=short
  61 passed, 9 warnings in 78.69s
  ```
- **Las 9 warnings son:** 7x `InsecureKeyLengthWarning` del JWT test (key de prueba corta, esperado) y 1x `PydanticDeprecatedSince20` en `connectors.py` (class-based `Config` → `ConfigDict`).
- **CI configurado:** Sí, `.github/workflows/ci.yml` existe. **No hay evidencia de que haya corrido** (el archivo fue creado en el commit del Sprint B0 que aún no se ha pusheado).

### Distribución de tests por archivo

| Archivo | Tests | Componente cubierto |
|---------|-------|---------------------|
| test_mr.py | 10 | Model Router — tiers, override, enrichment |
| test_dii.py | 12 | DII — clasificador, extensiones, hash |
| test_intent.py | 5 | Intent — tipos de documento |
| test_edb.py | 4 | EDB — init, BGE-M3 wiring |
| test_ri.py | 6 | RI — suficiencia, fallback, contexto |
| test_auth.py | 7 | JWT — create, expire, reject |
| test_cors.py | 4 | CORS, health, root endpoint |
| test_connectivity.py | 8 | BGE-M3, FalkorDB, Redis clients |
| test_sql_connector.py | 5 | SQL connector, bug fix verification |

### Delta vs auditoría 25-abr-2026

La auditoría previa reportó **cero tests**. Ahora hay **61 tests pasando**. Todos fueron creados en el Sprint B0 (commit `81a6f8e`, no pusheado aún al momento de esta auditoría — son cambios locales no commiteados).

---

## Eje 4 — Deuda del PoC sobre NOM-052 y LGPGIR

### Archivos que tocó el PoC

**Cero archivos de código.** El PoC existe únicamente como:
- `CLAUDE_8.md` (untracked, 119 líneas): documento de decisiones técnicas post-PoC.

No hay scripts, notebooks, ni archivos Python del PoC en el repo.

### `finalize()` y `deduplicate_entities()` async sin await

`CLAUDE_8.md` línea 111 reporta: *"`finalize()` y `deduplicate_entities()` quedaron como async sin await en el script de PoC — corregir en la integración."*

**Verificación:** `grep` para `finalize` y `deduplicate_entities` en todo el repo: **0 resultados**. Estas funciones no existen en el código actual. El problema es teórico — se refiere a un script de PoC que no fue commiteado. Se convierte en deuda cuando se integre GraphRAG-SDK.

### GraphRAG-SDK y BGE-M3 como embedder custom

`CLAUDE_8.md` sección 4 dice: *"Configurar GraphRAG-SDK con embedder BGE-M3 self-hosted vía la interfaz de embedder del SDK."*

**Verificación:** GraphRAG-SDK no está en el repo (ni en dependencias, ni en código, ni en configuración). No hay archivo de configuración de embedder para GraphRAG-SDK. La cuestión de si acepta BGE-M3 self-hosted es **no verificable con los medios disponibles** porque el SDK no está integrado.

### Los 5 contratos del PoC

`CLAUDE_8.md` referencia pruebas sobre NOM-052 y LGPGIR.

**Verificación:** `data/` contiene un solo archivo: `contrato_prueba_delfa_bridge.pdf`. No hay archivos NOM-052 ni LGPGIR. Los documentos del PoC **no están en el repo**.

---

## Eje 5 — Rebrand pendiente

### Conteo de ocurrencias

| Término | En .py (archivos) | En .py (ocurrencias) | En .html | En config | En .md | Total |
|---------|--------------------|-----------------------|----------|-----------|--------|-------|
| Panohayan (case-insensitive) | 53 archivos | 103 | 17 | 27 | 74 | **221** |
| delfa | — | — | — | — | 2 | **2** |
| DOCYAN | — | — | — | — | 6 | **6** |

### Desglose de "Panohayan" en código Python

| Categoría | Ubicaciones |
|-----------|-------------|
| **Nombre de clase** | `PanohayanOrchestrator` en `app/main.py:21` — 1 clase |
| **Nombre de paquete/import** | Ninguno — los imports son `from app.core.*`, no `from panohayan.*` |
| **Strings literales** | ~20 ocurrencias: títulos de API ("Panohayan DLE™ API"), prints de logs ("Panohayan™"), nombres MCP, defaults de env var (`panohayan-demo`), CORS example |
| **Comentarios** | ~80+ en comment headers de archivos ("SQL Connector \| Panohayan™") |
| **Configuración** | `fly.toml`: `app = "panohayan-dle-api"`, `FALKORDB_GRAPH = "panohayan"` |

### Evaluación: ¿find/replace global o decisión estructural?

**No es un simple find/replace.** Requiere decisión en:

1. **`fly.toml` app name** (`panohayan-dle-api`): cambiar requiere `fly apps create` nuevo o rename.
2. **FalkorDB graph name default** (`panohayan`): cambiar requiere migrar datos si ya hay grafos.
3. **Clase `PanohayanOrchestrator`**: rename trivial pero implica commit.
4. **Strings en demo HTML**: 17 ocurrencias front-facing.
5. **Nombre del repo** (`panohayan-dle-core`): está fuera del código pero afecta CI, URLs, imports externos.
6. **CLAUDE.md**: 74 ocurrencias — se puede reescribir pero es un doc operativo activo.

Los imports Python (`from app.*`) **no** usan "panohayan" en el path — el paquete es `app`, no `panohayan`. Esto hace que el rename en Python sea string-literal only, sin ruptura de imports.

---

## Eje 6 — Configuración de infraestructura

### Fly.io

- `fly.toml` presente. App name: `panohayan-dle-api`. Region: `mia`.
- **No hay evidencia de deploy real** — no hay screenshots de health check, no hay `fly.lock`, no hay deploy logs.

### Vercel

- **No existe `vercel.json`.** No hay frontend desplegado.

### Railway (legacy)

- `railway.toml` aún presente en el repo. Apunta al Dockerfile.

### Variables de entorno (.env.example)

31 variables declaradas:

```
JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS,
ALLOWED_ORIGINS, SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY,
GOOGLE_API_KEY, ORG_ID, DATA_DIR,
BGE_M3_URL, BGE_M3_TIMEOUT,
FALKORDB_HOST, FALKORDB_PORT, FALKORDB_GRAPH,
REDIS_URL,
SQL_DB_TYPE, SQL_HOST, SQL_PORT, SQL_DATABASE, SQL_USER, SQL_PASSWORD,
MICROSIP_URL, MICROSIP_USER, MICROSIP_PASSWORD, MICROSIP_DB,
STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET,
STRIPE_PRICE_STARTER, STRIPE_PRICE_PROFESSIONAL, STRIPE_PRICE_ENTERPRISE
```

**Ausentes vs `CLAUDE_8.md`:** `GEMINI_API_KEY` (requerido por GraphRAG-SDK según PoC), `OPENAI_API_KEY` (requerido por GraphRAG-SDK para QA), `ANTHROPIC_API_KEY` (listado en CLAUDE.md pero no en .env.example).

### Migraciones

- **1 migración:** `migrations/001_users_and_refresh_tokens.sql`
- **Herramienta:** SQL raw, sin ORM ni herramienta de migración (no hay Alembic, no hay dbmate, no hay esquema de versionado).
- **Tablas cubiertas por migraciones:** `users`, `refresh_tokens` (2 de 8 tablas usadas en código).
- **Tablas sin migración en el repo:** `documents`, `entities`, `audit_trail`, `governance_rules`, `quarantine`, `api_keys`.

---

## Eje 7 — Lo que NO existe pero debería según el plan

| Componente planificado | Bloque | Estado |
|------------------------|--------|--------|
| Schema PKG en FalkorDB con multi-tenant y versionado | B1 | **AUSENTE.** FalkorDB client es skeleton, no hay schema. |
| Schema PTM con segregación por par lingüístico y TM dual | B2 | **AUSENTE.** |
| Tokens QR (escaneable resuelve a contexto) | B3 | **AUSENTE.** |
| Lock terminológico como función técnica | B4 | **AUSENTE.** |
| Cotizador pre-ingesta con tiktoken | Post-PoC | **AUSENTE.** tiktoken no está en dependencias. |
| Librería de schemas por tipo documental | Post-PoC | **AUSENTE.** `intent.py` tiene 6 tipos hardcoded (contrato, factura, etc.) pero no son schemas de extracción para grafo. |
| Motor de Traducción Rigurosa (6 fases, Pista A) | B4 | **AUSENTE.** |
| Ingesta bilingüe (TMX/XLIFF, Pista B) | B5 | **AUSENTE.** |
| Vecalign + Hunalign | B5 | **AUSENTE.** |
| Matching fuzzy híbrido (Levenshtein + BGE-M3) | Decisión #2 | **AUSENTE.** |
| Clasificador de intención (Tipos 1-8) | B7 | **PARCIAL.** `intent.py` clasifica tipo de documento y query, pero no implementa los 8 tipos de intención del plan. |
| Hash chain SHA-256 en FAT | B6 | **AUSENTE.** `matrix.py` logea en Supabase pero sin cadena criptográfica. |
| GRG hardening (5 protecciones + cuarentena + FAT logging) | B6 | **PARCIAL.** GRG tiene block/flag/quarantine/redact pero sin las 5 protecciones del plan. |
| GraphRAG-SDK integrado | Post-PoC | **AUSENTE.** |
| UI #1 Consulta Operativa PWA | B8 | **AUSENTE.** Solo existe `demo/index.html` (portal admin, no PWA). |
| UI #2 Revisión Lingüística | B10 | **AUSENTE.** |
| UI #3 PM Dashboard | B11 | **AUSENTE.** |
| UI #4 Onboarding | B12 | **AUSENTE.** |
| Adaptador WhatsApp / 360dialog | B9 | **AUSENTE.** `app/connectors/whatsapp.py` existe pero es un stub genérico, no integra 360dialog. |
| APScheduler + Redis backend | Decisión #3 | **AUSENTE.** |
| Sesiones MO en Redis | Decisión #6 | **AUSENTE.** |
| Chat persistente en contexto (multi-turno) | Post-PoC | **AUSENTE.** |
| BGE-M3 self-hosted como servicio | Decisión #1 | **PARCIAL.** Client HTTP existe. El servicio en sí no está containerizado/desplegado. |
| `pyproject.toml` | — | **AUSENTE.** Deps solo vía `requirements.txt`. |

---

## Hechos críticos para el fundador

1. **GraphRAG-SDK no existe en el repo.** Ni como dependencia, ni como código, ni como script del PoC. La decisión de reemplazar DII por GraphRAG-SDK (`CLAUDE_8.md`) no tiene ninguna materialización en código. Todo el trabajo del PoC quedó fuera del repo.

2. **DII (352 LOC) sigue siendo el único pipeline de ingesta funcional.** Depende de Supabase + Google GenAI + LangExtract. El plan dice reemplazarlo por GraphRAG-SDK pero no hay código de transición.

3. **No existe frontend.** Cero archivos TypeScript, cero React, cero Next.js, cero package.json. Las 4 UIs (Consulta PWA, Revisión Lingüística, PM Dashboard, Onboarding) no tienen ni scaffolding.

4. **FalkorDB es un skeleton vacío.** No hay schema de grafo, no hay queries Cypher, no hay PKG ni PTM. Ningún módulo del repo usa FalkorDB para leer o escribir datos.

5. **6 de 8 tablas Supabase usadas en código no tienen migraciones.** Las tablas `documents`, `entities`, `audit_trail`, `governance_rules`, `quarantine`, `api_keys` se presumen creadas manualmente. Reproducir el entorno desde cero requiere trabajo manual no documentado.

6. **`openai==2.30.0` sigue en `requirements.txt`.** EDB ya fue migrado a BGE-M3 client, pero OpenAI queda como dependencia fantasma via LlamaIndex embeddings/LLMs (`llama-index-embeddings-openai`, `llama-index-llms-openai`). Estas sub-dependencias lo jalan transitivamente.

7. **El rebrand Panohayan → DOCYAN tiene 221 ocurrencias** distribuidas en strings, comments, config y 1 clase. Los imports Python no usan "panohayan" en paths (el paquete es `app`), así que el rename no rompe imports. Pero requiere decisión sobre fly.toml app name, FalkorDB graph name, y nombre del repo.

8. **Los 37 conectores (5,894 LOC) representan el 54% del código Python.** Son el módulo más grande del repo pero ninguno tiene tests. Muchos son stubs que siguen un patrón generado (API base + DII integration) sin pruebas de funcionamiento.

9. **No existen: alineadores bilingües, matching fuzzy, lock terminológico, cotizador pre-ingesta, tokens QR, APScheduler, sesiones Redis, hash chain FAT.** Estas son funciones core del plan de 14 bloques y de las 15 decisiones del Paso C.

10. **`railway.toml` sigue en el repo.** El Sprint B0 creó `fly.toml` para Fly.io pero no eliminó la config de Railway. No hay evidencia de deploy real en ninguna plataforma.

---

*Fin de la auditoría.*
*XCID SA de CV — 2026-05-28 — Confidencial.*
