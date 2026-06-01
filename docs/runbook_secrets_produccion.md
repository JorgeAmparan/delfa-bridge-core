# Runbook — Secrets de producción (B0.6)

> **Objetivo.** Cerrar el hueco de secrets del backend `docyan-lde-api` que
> quedó abierto desde B0: el backend se desplegó **sin** los secrets de Supabase,
> y cualquier endpoint que toque EDB / GRG / FAT / documents / governance /
> billing / auth falla en runtime al primer request real.
>
> Este runbook lista **cada secret faltante**, **en qué app**, y **de dónde sacar
> el valor**. Los comandos `flyctl secrets set` están listos para pegar con tus
> valores reales (placeholders `<...>`). Orden: primero backend, luego worker.
>
> **Quién ejecuta:** Jorge (requiere credenciales reales). Opus NO corre estos
> comandos.
>
> Verificado contra Fly y el repo el **31 mayo 2026**.

---

## 0. Pre-requisitos

```bash
flyctl auth whoami          # confirmar sesión
flyctl secrets list --app docyan-lde-api      # estado actual (11 secrets, sin Supabase)
flyctl secrets list --app docyan-lde-ingest   # estado actual del worker
```

> `flyctl secrets set` **reinicia la app** al aplicar (rolling). Es esperado.
> Puedes setear varios secrets en un solo comando (un solo restart).

---

## 1. Backend — `docyan-lde-api`

### 1.1. Secrets FALTANTES (los 3 críticos)

Estado actual: la app tiene 11 secrets (`ANTHROPIC_API_KEY`, `GEMINI_API_KEY`,
`JWT_SECRET`, `OPENAI_API_KEY`, `ALLOWED_ORIGINS`, `EMBEDDER_URL`, `FALKOR_HOST`,
`FALKOR_PORT`, `BGE_M3_TIMEOUT`, `REDIS_QUEUE_URL`, `REDIS_URL`) y **ninguno de
Supabase**. Faltan exactamente estos tres:

| Secret | Fuente del valor |
|---|---|
| `SUPABASE_URL` | Supabase Dashboard → tu proyecto → **Project Settings → API** → *Project URL* (`https://<ref>.supabase.co`). |
| `SUPABASE_KEY` | Mismo panel → *Project API keys* → **`anon` / `public`**. Es la key con RLS aplicado (la usan edb, grg, matrix, documents, governance, billing, mcp_server). |
| `SUPABASE_SERVICE_KEY` | Mismo panel → *Project API keys* → **`service_role`** (⚠️ secreta, bypassa RLS; solo la usa `auth.py`). |

**Comando (pegar con valores reales):**

```bash
flyctl secrets set --app docyan-lde-api \
  SUPABASE_URL="https://<tu-ref>.supabase.co" \
  SUPABASE_KEY="<anon-public-key>" \
  SUPABASE_SERVICE_KEY="<service-role-key>"
```

### 1.2. Env vars no-secret (ya resueltas en `fly.toml`, acción opcional)

B0.6 movió los endpoints internos NO sensibles al bloque `[env]` del `fly.toml`
raíz (lugar canónico, igual que `worker/fly.toml`):

```
FALKOR_HOST   = "docyan-lde-graph.internal"
FALKOR_PORT   = "6379"
EMBEDDER_URL  = "http://docyan-lde-embedder.internal:8000"
BGE_M3_TIMEOUT = "30"
```

Hoy esos 4 también existen como **secrets** (precedencia: el secret gana sobre
`[env]`). No hay conflicto funcional. **Opcional**, para dejar la config limpia y
visible en el toml, puedes quitarlos como secrets tras el próximo deploy:

```bash
# OPCIONAL — solo si quieres que los tome de fly.toml [env] en vez de secrets.
# Verifica primero que los valores en fly.toml [env] son los correctos para prod.
flyctl secrets unset --app docyan-lde-api FALKOR_HOST FALKOR_PORT EMBEDDER_URL BGE_M3_TIMEOUT
```

> Si los dejas como secrets, **todo sigue funcionando** — son idénticos. Esto es
> solo higiene de configuración.

### 1.3. Secrets opcionales del backend (setear solo si se usan)

| Secret | Cuándo |
|---|---|
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | Si se activa billing (router `/billing`). |
| `WA_360DIALOG_API_KEY`, `WA_360DIALOG_WEBHOOK_SECRET` | B9 (WhatsApp), aún no cableado. |
| `API_KEY` | Solo si se quiere auth por `X-API-Key` (dev). |

---

## 2. Worker — `docyan-lde-ingest`

> El worker **NO usa Supabase**. Solo Docling + GraphRAG-SDK + FalkorDB + LLM.
> El cotizador (que sí toca Supabase / `tenant_budget`) vive en el **backend**.

### 2.1. Secrets del worker

| Secret | Fuente |
|---|---|
| `GEMINI_API_KEY` | Misma key que el backend (Google AI Studio). Extracción + resolution. |
| `OPENAI_API_KEY` | Misma key que el backend. QA gpt-4o-mini. |
| `REDIS_QUEUE_URL` | URL de la cola Redis: `redis://docyan-lde-redis.internal:6379/0`. |

```bash
flyctl secrets set --app docyan-lde-ingest \
  GEMINI_API_KEY="<gemini-key>" \
  OPENAI_API_KEY="<openai-key>" \
  REDIS_QUEUE_URL="redis://docyan-lde-redis.internal:6379/0"
```

### 2.2. Env vars del worker (ya en `worker/fly.toml [env]`, no tocar)

`FALKOR_HOST`, `FALKOR_PORT`, `EMBEDDER_URL`, `HF_HUB_OFFLINE`,
`TRANSFORMERS_OFFLINE`, `DOCLING_ARTIFACTS_PATH`. No son secrets.

---

## 3. Verificación post-set (backend)

Tras setear los secrets del backend (§1.1), corre el smoke test contra la app
desplegada (no localmente):

```bash
export DOCYAN_API_URL="https://docyan-lde-api.fly.dev"
# Opcional: token JWT de un usuario de prueba para endpoints autenticados
# export DOCYAN_SMOKE_TOKEN="<jwt>"
python scripts/smoke_test_backend.py
```

El smoke test (`scripts/smoke_test_backend.py`) verifica, sin tocar el worker:

1. `/health` responde 200.
2. Los módulos que dependen de Supabase **ya no fallan** por config ausente
   (si faltara un secret, el endpoint devolvería el `RuntimeError` loud de B0.6,
   no un 200 silencioso ni un 500 críptico).
3. El cotizador puede consultar `tenant_budget` (lectura inocua) — **solo si el
   código del cotizador ya está mergeado** (ver §4); si no, el paso se reporta
   como SKIPPED, no como fallo.
4. Una operación de FAT/audit_trail de prueba con un tenant de test
   (`__smoke_test__`), no destructiva, sin contaminar datos reales.

**Resultado esperado:** `SMOKE OK` con todos los checks en `PASS` (o `SKIP`
justificado). Cualquier `FAIL` imprime el secret/condición que falta.

---

## 4. Nota operativa importante (verdad operacional)

El Sprint Contract B0.6 referenció `app/ingesta/budget_manager.py`,
`app/ingesta/document_store.py`, `worker/` y `scripts/smoke_test_ingesta.py`.
**Esos archivos viven en las ramas `sprint/B2-ingest-engine` /
`sprint/B2.1-redis-app`, aún NO mergeadas a `main`.** En `main` (base de B0.6) no
existen todavía.

Implicaciones:

- El gap de secrets que B0.6 cierra es **real y aplica a `main`**: los módulos
  `edb`, `grg`, `matrix`, `auth`, `documents`, `governance`, `billing`,
  `mcp_server` SÍ están en `main` y SÍ dependen de Supabase. Esos son los que
  ahora fallan loud.
- El cotizador (`budget_manager` / `tenant_budget`) y el worker se cablearán
  cuando B2/B2.1/B2.2 mergeen. El helper de validación loud
  (`app/core/supabase_client.require_supabase_config`) ya queda disponible para
  que esos módulos lo adopten al integrarse.
- El smoke test trata el check del cotizador como **opcional/SKIP** mientras el
  módulo no esté en el árbol, para no reportar un falso `FAIL`.

---

## 5. Resumen ejecutable (TL;DR)

```bash
# 1) Backend — los 3 secrets que faltan:
flyctl secrets set --app docyan-lde-api \
  SUPABASE_URL="https://<tu-ref>.supabase.co" \
  SUPABASE_KEY="<anon-public-key>" \
  SUPABASE_SERVICE_KEY="<service-role-key>"

# 2) Worker — cuando se despliegue B2.2:
flyctl secrets set --app docyan-lde-ingest \
  GEMINI_API_KEY="<gemini-key>" \
  OPENAI_API_KEY="<openai-key>" \
  REDIS_QUEUE_URL="redis://docyan-lde-redis.internal:6379/0"

# 3) Verificar backend:
export DOCYAN_API_URL="https://docyan-lde-api.fly.dev"
python scripts/smoke_test_backend.py
```
