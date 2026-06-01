# Worker de ingesta — `docyan-lde-ingest` (B2)

> **DOCYAN LDE™ by XCID.** Cuarto proceso de la topología Fly. Construido en B2.
> Stack pesado de ingesta aislado del backend de consultas.

## Por qué un proceso aparte

La ingesta arrastra un stack que NO puede vivir en el backend (que se mantiene
<1 GB para no toparse con el límite de unpack de 8 GB de Fly que B0.5 resolvió):

- **Docling** + `docling-ibm-models` (layout + TableFormer) → **PyTorch** (~3 GB).
- **GraphRAG-SDK 1.1.1** → `gliner` → **PyTorch** (inevitable, ver §PyTorch).
- **LiteLLM**, google-genai, openai, tiktoken.

Razones (Sprint B2 §Contexto):

1. Imagen del backend <1 GB (716 MB hoy); el worker carga torch sin contaminarlo.
2. OCR y modelos de layout pesan varios GB; no deben tocar la latencia de consulta.
3. Escalado independiente: jobs largos y pesados vs consultas cortas y rápidas.
4. Aislamiento de fallos: un PDF malformado que tumbe Docling no tira el backend.

## Decisión PyTorch vs ONNX (§3 — vinculante)

**PyTorch se queda en el worker (CPU-only).** Evidencia (metadata real instalada):

- `docling-ibm-models` exige `torch<3.0.0,>=2.2.2` + `torchvision` de forma
  **incondicional** (no es extra opcional). El layout model y **TableFormer**
  (estructura de tablas complejas, núcleo del PoC: tablas de MSDS, mediciones de
  calibración, parámetros de especificación, ratings/torques del manual de
  seccionador) son PyTorch. **No existe TableFormer en ONNX en Docling 2.x.**
- `graphrag-sdk` exige `gliner` → `torch>=2.0.0`. **Torch es inevitable en el
  worker aunque se desactivara Docling.**

Mitigaciones aplicadas:

- **Torch CPU-only**: se instala desde `https://download.pytorch.org/whl/cpu`
  ANTES del resto, para que pip no arrastre la build CUDA (~3 GB nvidia).
- **OCR con Tesseract** (apt, sin torch) en vez de EasyOCR, para no sumar modelos
  torch extra. Layout/tabla siguen en torch; OCR no.
- Si la imagen descomprimida supera 4 GB, evaluar multi-stage / base slim (§14).

## Dispatcher de jobs — Opción A (cola Redis) (§8)

Elegida sobre HTTP directo (B) y Fly machine API (C):

- Separación limpia de concerns; retry/monitoring naturales; escalado horizontal
  (más workers si crece la carga); **Redis ya está en el stack** (decisión #6).
- Implementada como **cola ligera sobre `redis-py`** (LIST + `RPUSH`/`BLPOP`) en
  vez de `rq`: no añade dependencia nueva al backend ni acopla su modelo de
  worker. El backend solo usa `redis` (ya en deps); el SDK pesado nunca lo toca.

**Recurso Redis (DECIDIDO, B2.1):** un solo Redis compartido, levantado como Fly
app aparte **`docyan-lde-redis`** (dir `redis/`), con doble propósito: cola de
ingesta (B2, `REDIS_QUEUE_URL`) + Session Manager/APScheduler (B4, `REDIS_URL`,
decisión #6). Coherente con la topología de procesos separados. Config: AOF +
`maxmemory-policy noeviction` (la cola/sesiones nunca se evictan en silencio).
Deploy y secrets en [`../redis/README.md`](../redis/README.md) — el `flyctl
deploy` queda PENDIENTE DE JORGE (igual que el del worker).

### Flujo del gate (sin bypass)

```
POST /ingesta/documents
   → cotizador mide tokens, estima costo/tiempo, verifica presupuesto+hard caps
   → RECHAZADO (saldo/cap): job 'rejected'           [NO se encola]
   → APROBADO: job 'pending_confirmation'            [NO se encola todavía]
POST /ingesta/documents/{job_id}/confirm
   → si confirmable: status 'queued' + RPUSH a la cola Redis
worker (BLPOP) → 'processing' → pipeline → 'completed' | 'failed'
```

El worker NUNCA ingiere un job sin cotización aprobada (verifica la invariante
como defensa en profundidad). **No hay bypass** (CLAUDE.md §14).

## Almacén de documentos

Backend y worker son apps Fly separadas **sin filesystem compartido**. El backend
guarda el binario y pasa al worker una **referencia** (`documento_ref`); el worker
lo descarga. Implementaciones: `LocalDocumentStore` (dev/tests) y
`SupabaseStorageDocumentStore` (producción, bucket `ingest-tmp`).
**PENDIENTE DE JORGE (ops):** crear el bucket `ingest-tmp` en Supabase Storage.

## Pipeline (`worker/ingest_pipeline.py`)

```
Docling (PDF/docx/xlsx/... → Markdown, OCR + tablas complejas)
  → GraphRAG-SDK: ingest(text=markdown, document_id=job_id)  [provenance nativo:
                  MENTIONED_IN / PART_OF / NEXT_CHUNK + spans de caracteres]
  → await deduplicate_entities(fuzzy=True)   ← bug PoC #1 corregido (es async)
  → await finalize()
  → get_statistics()
```

Multi-tenancy ABSOLUTA: `ConnectionConfig(graph_name=graph_name_for(tenant_id))`
— el mismo grafo aislado que lee el backend. BGE-M3 (1024 dim) como embedder, vía
el `embedder_adapter` de B1; NO OpenAI/Gemini para embeddings (decisión #1).

### Bugs del PoC corregidos

- **#1** `deduplicate_entities(fuzzy=True)` se **awaita** (es coroutine; no hay
  `_sync`). El PoC la llamó sin await → no-op silencioso, 653 residuos. Test de
  regresión: `tests/test_dedup_with_fuzzy.py`.
- **finalize**: se usa `await finalize()` (existe `finalize_sync()` para
  contextos síncronos). El pipeline es `async`, así que awaita.

## Modelos (§5.3 — validado PoC, Adenda §3)

| Fase | Modelo | Nota |
|---|---|---|
| Extracción | `gemini/gemini-2.5-flash` | prefijo `gemini/` OBLIGATORIO (sino → Vertex AI) |
| QA / consulta | `gpt-4o-mini` | |
| Resolution | `gemini/gemini-2.5-flash` | `LLMVerifiedResolution` |
| Embeddings | BGE-M3 self-hosted | 1024 dim, vía adapter |

Secrets del worker: `GEMINI_API_KEY` (NO `GOOGLE_API_KEY`), `OPENAI_API_KEY`,
`FALKOR_HOST/PORT`, `EMBEDDER_URL`, `REDIS_QUEUE_URL`.

## Perfil de recursos y deploy

`fly.toml`: `docyan-lde-ingest`, región `dfw`, `shared-cpu-4x` / 4 GB, **sin
volumen** (stateless), servicio HTTP **privado** (flycast, solo `/health`).

**Build context = RAÍZ del repo** (el Dockerfile hace `COPY app/` y `COPY worker/`).
Por eso se despliega DESDE LA RAÍZ con `--config worker/fly.toml`, y
`[build].dockerfile` en el toml es `"Dockerfile"` (flyctl lo resuelve relativo al
dir del `--config`, worker/ → worker/Dockerfile). Verificado empíricamente (B2.2):
context=raíz → `COPY app`/`COPY worker` resuelven; context=worker/ → `COPY app`
falla con `"/app": not found`. NO hacer `cd worker`. Pasos detallados y verificación:
[`runbook_deploy_worker.md`](runbook_deploy_worker.md). Preflight: `scripts/preflight_worker.py`.

```bash
flyctl apps create docyan-lde-ingest
# DESDE LA RAÍZ del repo (context = raíz):
flyctl deploy --app docyan-lde-ingest --config worker/fly.toml
flyctl secrets set GEMINI_API_KEY=... OPENAI_API_KEY=... \
  FALKOR_HOST=docyan-lde-graph.internal FALKOR_PORT=6379 \
  EMBEDDER_URL=http://docyan-lde-embedder.internal:8000 \
  REDIS_QUEUE_URL=redis://docyan-lde-redis.internal:6379/0 \
  SUPABASE_URL=... SUPABASE_SERVICE_KEY=... INGEST_STORAGE_BUCKET=ingest-tmp \
  --app docyan-lde-ingest
```
