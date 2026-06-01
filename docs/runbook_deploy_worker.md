# Runbook — Deploy del worker de ingesta `docyan-lde-ingest` (B2.2)

> **DOCYAN LDE™ by XCID.** Pasos EXACTOS para que **Jorge** despliegue el worker y
> haga el primer smoke test de ingesta real. Opus preparó y verificó todo
> localmente; aquí solo se ejecuta contra infra real con secrets.
>
> **Antes de empezar:** corre el preflight (no gasta nada):
> ```bash
> ./venv/bin/python scripts/preflight_worker.py   # debe salir "PREFLIGHT VERDE", exit 0
> ```
> Si el preflight no está verde, NO sigas: arregla lo que reporte primero.

Cada paso tiene: **comando exacto**, **qué esperar**, **si falla**.

---

## Pre-requisitos

- `flyctl` autenticado (`flyctl auth whoami` → tu cuenta).
- Las otras 4 apps ya desplegadas: `docyan-lde-api`, `docyan-lde-graph`,
  `docyan-lde-embedder`, `docyan-lde-redis` (`flyctl apps list`).
- Secrets reales a mano: `GEMINI_API_KEY`, `OPENAI_API_KEY`.
- Estar en la **raíz del repo** (`docyan-lde-core/`) para todos los comandos
  salvo donde se indique.

---

## Paso 1 — Crear la app Fly `docyan-lde-ingest`

```bash
flyctl apps create docyan-lde-ingest
```
- **Esperar:** `New app created: docyan-lde-ingest`.
- **Si falla** (`already exists`): ya existe, continúa al Paso 2. Verifica con
  `flyctl apps list | grep docyan-lde-ingest`.

---

## Paso 2 — Crear el bucket Supabase Storage `ingest-tmp`

El backend sube el documento y el worker lo descarga por referencia (apps Fly
separadas, sin filesystem compartido).

**Vía dashboard (recomendado):** Supabase → Storage → New bucket →
nombre `ingest-tmp`, **Private** (no público). Create.

**Vía CLI (alternativa):**
```bash
# Requiere SUPABASE_ACCESS_TOKEN y el project-ref.
curl -s -X POST "https://<PROJECT_REF>.supabase.co/storage/v1/bucket" \
  -H "Authorization: Bearer <SUPABASE_SERVICE_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"id":"ingest-tmp","name":"ingest-tmp","public":false}'
```
- **Esperar:** el bucket `ingest-tmp` aparece en Storage (privado).
- **Si falla** (`Duplicate`): ya existe, continúa.
- **Nota:** si prefieres no usar Storage aún, el worker acepta `INGEST_STORAGE_DIR`
  (filesystem) — pero eso requiere volumen compartido, que NO existe entre apps
  Fly. Para producción usa el bucket.

---

## Paso 3 — Setear los secrets del worker

Reemplaza `<...>` por los valores reales. `REDIS_QUEUE_URL` apunta a la app
`docyan-lde-redis` (B2.1).

```bash
flyctl secrets set \
  GEMINI_API_KEY="<tu-gemini-api-key>" \
  OPENAI_API_KEY="<tu-openai-api-key>" \
  FALKOR_HOST="docyan-lde-graph.internal" \
  FALKOR_PORT="6379" \
  EMBEDDER_URL="http://docyan-lde-embedder.internal:8000" \
  REDIS_QUEUE_URL="redis://docyan-lde-redis.internal:6379/0" \
  SUPABASE_URL="<tu-supabase-url>" \
  SUPABASE_SERVICE_KEY="<tu-supabase-service-key>" \
  INGEST_STORAGE_BUCKET="ingest-tmp" \
  --app docyan-lde-ingest
```
- **Esperar:** `Secrets are staged for the first deployment`.
- **Si falla:** revisa que estás logueado y que el nombre de app es exacto.
- **Importante:** `GEMINI_API_KEY` (NO `GOOGLE_API_KEY`). Sin el secret correcto,
  la extracción Gemini falla en runtime.

El backend también necesita la cola (para encolar) — si no lo tiene ya:
```bash
flyctl secrets set \
  REDIS_QUEUE_URL="redis://docyan-lde-redis.internal:6379/0" \
  INGEST_STORAGE_BUCKET="ingest-tmp" \
  --app docyan-lde-api
```

---

## Paso 4 — Aplicar las migraciones 008 y 009 en Supabase

Crean `tenant_budget` (cotizador) y `tenant_schemas` (registry).

**Vía Supabase SQL Editor (recomendado):** abre el SQL Editor y pega el contenido
de, en orden:
1. `migrations/008_tenant_budget.sql`
2. `migrations/009_tenant_schemas.sql`
Ejecuta cada uno (Run).

**Vía psql (alternativa):**
```bash
psql "<SUPABASE_DB_URL>" -f migrations/008_tenant_budget.sql
psql "<SUPABASE_DB_URL>" -f migrations/009_tenant_schemas.sql
```
- **Esperar:** `CREATE TABLE` / `CREATE POLICY` sin error.
- **Si falla** (`already exists`): la tabla ya está; verifica columnas con
  `\d tenant_budget` / `\d tenant_schemas`.
- **Verificación:** debe haber un `tenant_budget` con saldo para el tenant de
  prueba ANTES del smoke test (Paso 7 lo crea si no existe).

---

## Paso 5 — Deploy del worker (build context = RAÍZ)

> **CLAVE (aprendizaje B2.1/B2.2):** el worker hace `COPY app/` y `COPY worker/`,
> así que el build context debe ser la **raíz del repo**. Se despliega DESDE LA
> RAÍZ con `--config worker/fly.toml`. NO hagas `cd worker` (rompería `COPY app`).
> Verificado con build local: con context=raíz los COPY resuelven; con
> context=worker/ `COPY app` falla con `"/app": not found`.

```bash
# DESDE LA RAÍZ del repo:
flyctl deploy --app docyan-lde-ingest --config worker/fly.toml
```
- **Esperar:** el build instala PyTorch CPU + Docling + GraphRAG-SDK (varios
  minutos la 1ª vez), precarga modelos Docling, y termina con
  `successfully deployed` / una máquina `started`. **Tamaño de imagen medido en
  build local: ~7.5 GB** (es el worker, no el backend de 243 MB). Margen al límite
  de unpack de Fly (~8 GB) es delgado (~0.5 GB).
- **Si falla por TAMAÑO (>8 GB unpack):** aplica la mitigación de menor riesgo —
  quita `llama-index-core` de `worker/requirements.txt` (no se usa en el path
  activo) y reconstruye. Ver `docs/worker_architecture.md` §Tamaño de imagen.
- **Si falla en `COPY app` (`"/app": not found`):** estás deployando con el
  context equivocado. Asegúrate de ejecutar el comando **desde la raíz** y con
  `--config worker/fly.toml` (no `cd worker`).
- **Si falla en `worker/worker/Dockerfile not found`:** el `[build].dockerfile`
  del toml quedó mal; debe ser `"Dockerfile"` (ver `scripts/preflight_worker.py`).
- **Si el build se queda sin RAM/disco:** la imagen con torch es grande; sube el
  perfil de `[[vm]]` temporalmente o usa `--build-only` para diagnosticar.

---

## Paso 6 — Verificación post-deploy

```bash
flyctl status --app docyan-lde-ingest          # máquina 'started'
flyctl logs --app docyan-lde-ingest            # buscar: "worker de ingesta iniciado; esperando jobs…"
```
Health por flycast (desde una máquina en la red privada de Fly, p.ej. SSH al backend):
```bash
flyctl ssh console --app docyan-lde-api -C \
  "curl -s http://docyan-lde-ingest.internal:8000/health"
```
- **Esperar:** JSON `{"status":"healthy","service":"docyan-lde-ingest",
  "falkordb":true,"embedder":..., "consumer_running":true}`.
- **`consumer_running:true`** confirma que el loop de la cola arrancó (necesita
  `REDIS_QUEUE_URL`). Si es `false`, falta el secret de la cola (Paso 3).
- **`falkordb:false`:** revisa `FALKOR_HOST` y que `docyan-lde-graph` esté arriba.

---

## Paso 7 — Smoke test de ingesta real (PDF → grafo)

Usa el script preparado. Sube el PDF de prueba (manual técnico en inglés,
IB-111-RDA), cotiza, confirma, hace polling y verifica el grafo.

```bash
export DOCYAN_API_URL="https://docyan-lde-api.fly.dev"
export DOCYAN_TOKEN="<JWT de un usuario admin/editor>"   # de POST /auth/login
export DOCYAN_TEST_PDF="/ruta/al/IB-111-RDA RDA1 230 R5 02172021.pdf"
# Opcional: asegura saldo del tenant antes (si no, el cotizador rechaza):
#   inserta/actualiza tenant_budget.saldo_actual_usd para tu org_id.

./venv/bin/python scripts/smoke_test_ingesta.py
```
- **Esperar (salida del script):**
  - `COTIZACIÓN: costo ~$0.01–0.02 USD, job_id=...` (decisión `aprobado_requiere_confirmacion`).
  - `CONFIRMADO → encolado`.
  - `POLLING ... status=processing → completed`.
  - `GRAFO: :Procedimiento=N (>0), :Paso=M (>0)`.
  - `COSTO real vs estimado` (informativo).
  - `SMOKE TEST OK`.
- **Si el cotizador RECHAZA por saldo:** carga saldo en `tenant_budget` para tu
  `org_id` y reintenta (es el gate funcionando, no un bug).
- **Si `status=failed`:** `flyctl logs --app docyan-lde-ingest` — causas típicas:
  `GEMINI_API_KEY` inválida, embedder caído, o el bucket `ingest-tmp` inexistente.

---

## Rollback por paso

| Paso | Si algo sale mal | Rollback |
|---|---|---|
| 1 (crear app) | App a medias | `flyctl apps destroy docyan-lde-ingest` y reintentar. |
| 2 (bucket) | Bucket mal creado | Borrarlo en el dashboard y recrearlo privado. |
| 3 (secrets) | Secret equivocado | `flyctl secrets set` de nuevo (re-stagea); `flyctl secrets list` para ver cuáles hay. |
| 4 (migraciones) | Migración parcial | Las migraciones son `CREATE`; si falló a medias, revisa con `\d`; no hay datos que perder en alfa. |
| 5 (deploy) | Deploy roto | `flyctl releases --app docyan-lde-ingest` y `flyctl deploy --image <release-anterior>` o re-deploy tras corregir. La app no sirve tráfico público, así que un deploy roto no afecta a usuarios. |
| 6 (health) | No responde | `flyctl machine restart <id> --app docyan-lde-ingest`; revisa logs. |
| 7 (smoke) | Ingesta falla | El job queda `failed` en Redis; no corrompe el grafo (escritura transaccional del SDK). Corrige la causa y reintenta con otro documento. |

---

## Notas

- **El cotizador es un gate sin bypass:** ninguna ingesta ocurre sin cotización
  aprobada + confirmación. Si el smoke test no llega a `confirmar`, no se gastó en
  Gemini.
- **Multi-tenant:** el worker escribe en `docyan_tenant_<org_id>`. El smoke test
  usa tu tenant; no toca otros.
- **Costo esperado del PDF de prueba:** ~$0.01–0.02 USD (≈9.4k tokens). El de
  ingeniería (Becerril, 252pp) costaría más; cotízalo antes de ingerirlo.
