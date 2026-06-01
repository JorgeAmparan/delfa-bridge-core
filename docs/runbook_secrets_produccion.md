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

### 1.1. Secrets FALTANTES (los 2 de Supabase)

> **B0.7 (Adenda MVP, 31-may-2026):** el backend usa **SOLO `service_role`**. La
> anon key (`SUPABASE_KEY`) fue **eliminada del stack** — ya no se setea. El
> aislamiento multi-tenant es a nivel de query (Doc 09) y la integridad del FAT
> la da el hash chain SHA-256 (Doc 08), no las RLS. Por eso son **2 secrets, no 3**.

Estado actual: la app tiene 11 secrets (`ANTHROPIC_API_KEY`, `GEMINI_API_KEY`,
`JWT_SECRET`, `OPENAI_API_KEY`, `ALLOWED_ORIGINS`, `EMBEDDER_URL`, `FALKOR_HOST`,
`FALKOR_PORT`, `BGE_M3_TIMEOUT`, `REDIS_QUEUE_URL`, `REDIS_URL`) y **ninguno de
Supabase**. Faltan exactamente estos dos:

| Secret | Fuente del valor |
|---|---|
| `SUPABASE_URL` | Supabase Dashboard → tu proyecto → **Project Settings → API** → *Project URL* (`https://<ref>.supabase.co`). |
| `SUPABASE_SERVICE_KEY` | Mismo panel → *Project API keys* → **`service_role`** (⚠️ secreta, bypassa RLS). La usan edb, grg, matrix, auth, y los módulos fuera de alcance al reactivarse. |

**Comando (pegar con valores reales):**

```bash
flyctl secrets set --app docyan-lde-api \
  SUPABASE_URL="https://<tu-ref>.supabase.co" \
  SUPABASE_SERVICE_KEY="<service-role-key>"
```

> **NO** setees `SUPABASE_KEY` (anon). Si quedó de un intento previo, quítala:
> `flyctl secrets unset --app docyan-lde-api SUPABASE_KEY`

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

El smoke test (`scripts/smoke_test_backend.py`) verifica, sin tocar el worker,
**solo el camino service_role** (B0.7 eliminó el camino anon):

1. `/health` responde 200.
2. El backend construye el cliente Supabase service_role sin `RuntimeError`
   (vía `/auth/login` con credenciales bogus: 401 = config OK; 500 = secret
   ausente, revisar `flyctl logs`). No destructivo.
3. FAT/audit_trail inserta+lee (con `DOCYAN_SMOKE_TOKEN`: un GET autenticado
   lee el trail y el request queda auditado). SKIP si no hay token.
4. El cotizador (`tenant_budget`) se reporta **SKIP** hasta que B2 mergee
   (`app/ingesta` no está en el árbol todavía). Ver §4.

**Resultado esperado:** `SMOKE OK` con todos los checks en `PASS` (o `SKIP`
justificado). Cualquier `FAIL` imprime el secret/condición que falta.

---

## 3.1. Alcance MVP del backend (B0.7) — qué módulos operan y cuáles no

Por la **Adenda de Alcance MVP Consulta Viva** (31-may-2026,
`docs/DOCYAN_Adenda_Alcance_MVP_ConsultaViva.md`), el backend MVP usa **solo
service_role en los módulos del camino crítico**. El resto queda
**explícitamente deshabilitado** hasta su sprint de activación — no es un
pendiente oculto, es alcance declarado.

**EN alcance MVP (operan contra Supabase service_role):**
`app/core/edb.py`, `app/core/grg.py`, `app/core/matrix.py`, `app/core/ri.py`
(vía edb), `app/api/auth.py`. (+ `app/ingesta/budget_manager.py` y
`document_store.py` al mergear B2 — ver `docs/TODO_B0.7_service_role_en_B2.md`.)

**FUERA de alcance MVP (guardados con `require_module_enabled`, fallan loud salvo
flag):** `app/core/dii.py` (`DOCYAN_ENABLE_DII`), `app/api/routers/billing.py`
(`DOCYAN_ENABLE_BILLING`), `app/api/routers/governance.py`
(`DOCYAN_ENABLE_GOVERNANCE`), `app/api/routers/documents.py`
(`DOCYAN_ENABLE_DOCUMENTS`), `app/mcp_server.py` (`DOCYAN_ENABLE_MCP_SERVER`).

> En producción MVP **no se setea ningún `DOCYAN_ENABLE_*`** → esos módulos
> quedan deshabilitados. Para reactivar uno en su sprint, set su flag = `1`.

---

## 4. Nota operativa importante (verdad operacional)

El Sprint Contract referenció `app/ingesta/budget_manager.py`,
`app/ingesta/document_store.py`, `worker/` y `scripts/smoke_test_ingesta.py`.
**Esos archivos viven en las ramas `sprint/B2-ingest-engine` /
`sprint/B2.1-redis-app`, aún NO mergeadas a `main`.** En la rama de B0.7
(derivada de `main` con B0.6) no existen todavía.

Implicaciones:

- El gap de secrets es **real y aplica a `main`**: `edb`, `grg`, `matrix`,
  `auth` (camino crítico) SÍ están en `main` y SÍ dependen de Supabase.
- El cotizador (`budget_manager` / `tenant_budget`) y `document_store` adoptarán
  service_role al mergear B2 — acción registrada en
  `docs/TODO_B0.7_service_role_en_B2.md`. El helper ya está listo.
- El smoke test trata el check del cotizador como **SKIP** mientras el módulo no
  esté en el árbol, para no reportar un falso `FAIL`.

---

## 5. Resumen ejecutable (TL;DR)

```bash
# 1) Backend — los 2 secrets que faltan (B0.7: solo service_role, sin anon):
flyctl secrets set --app docyan-lde-api \
  SUPABASE_URL="https://<tu-ref>.supabase.co" \
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
