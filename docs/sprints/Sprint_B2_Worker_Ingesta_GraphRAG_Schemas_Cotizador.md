# Sprint Contract B2 — Worker de ingesta + GraphRAG-SDK + librería de schemas + cotizador pre-ingesta

**Producto:** DOCYAN LDE — Live Document Environment by XCID
**Bloque:** B2 | **Ejecutor:** Opus 4.8 vía Claude Code CLI
**Modo:** Una aprobación + ejecución completa + un reporte final.
**Repo:** `docyan-lde-core` | **Branch de trabajo:** `sprint/B2-ingest-engine`

---

## Prerequisitos

B0 + B0.5 + B1 + B1.5 completados y mergeados a `main`. Estado actual:

- Backend Fly `docyan-lde-api` ✅ deployed, health 200.
- FalkorDB Fly `docyan-lde-graph` ✅ deployed con volumen persistente.
- BGE-M3 Fly `docyan-lde-embedder` ✅ deployed con flycast, 8 GB RAM, offline mode.
- Frontend Vercel `docyan-lde.vercel.app` ✅ HTTP 200.
- CI los 3 jobs verdes (backend, gen-types, frontend) sostenidos en main.
- 103 tests backend passing.
- Ontología DKG implementada con multi-tenancy por `graph_name` y versionado in-place.
- Adapter BGE-M3 para GraphRAG-SDK validado (`app/graph/embedder_adapter.py`) — cableado funciona, ingesta real es este sprint.
- Fachada del grafo: `app/graph/dkg_client.py`.
- Pendientes técnicos B0 resueltos en B1: `genai.Client()` lazy init, pin de litellm. Pendiente `cryptography==46` — verificar estado al inicio de este sprint.

## Contexto para Opus

B1 construyó **la infraestructura de grafo** (FalkorDB + BGE-M3 + ontología + multi-tenancy + versionado). Este sprint construye **el motor de ingesta que la alimenta**. Decisión arquitectónica central, ratificada por el fundador:

**Topología de 4 procesos en producción.** Tres ya existen (api, graph, embedder). Este sprint agrega el cuarto: `docyan-lde-ingest`, Fly app aparte, dedicada al worker de ingesta con su propio stack pesado (Docling + LlamaIndex + GraphRAG-SDK + LiteLLM). Razones:

- Imagen del backend principal se mantiene en <1 GB (716 MB hoy), evitando el bloqueo de 8 GB unpack de Fly que B0.5 resolvió.
- Docling y modelos OCR pesan varios GB; no deben contaminar el backend que sirve consultas con baja latencia.
- Escalado independiente: jobs de ingesta son largos y pesados; consultas son cortas y rápidas. Perfiles de recursos distintos.
- Aislamiento de fallos: si Docling crashea en un PDF malformado, no tira el backend de consultas.

**El incidente del PoC del 28 may 2026** ($5,000 en costos de Gemini por timeout 600s, escritura parcial, sin control de costo) **es la justificación operativa del cotizador pre-ingesta como componente no negociable de este sprint**. Sin cotizador, no hay ingesta. Adenda §8 lo marca CRÍTICO.

**Decisiones inviolables que rigen este sprint:**

- **GraphRAG-SDK 1.1.1 reemplaza al DII** (Adenda §2). DII queda `@deprecated` en B1; aquí se construye su sustituto operativo.
- **BGE-M3 self-hosted vía adapter** ya validado en B1. Sin cambio.
- **Multi-tenancy por `graph_name`** sigue siendo regla absoluta. Toda ingesta se escribe en el grafo del tenant correspondiente, nunca cross-tenant.
- **Stack de ingesta del PoC validado**: Gemini 2.5 Flash extracción (`gemini/gemini-2.5-flash` vía LiteLLM, prefijo obligatorio) + gpt-4o-mini QA + Gemini 2.5 Flash Resolution (LLMVerifiedResolution) + `deduplicate_entities(fuzzy=True)` con `await` correcto.
- **Librería de schemas por TIPO de documento** (Adenda §6, hallazgo central del PoC: schema NOM-052 extrajo 0 relaciones de LGPGIR; el tipo del documento define el schema). Mercado alfa: 5 tipos.
- **Modos de fuente de ingesta** según Adenda §6.1: manual (default) + conectado (Google Drive / OneDrive / FTP / SharePoint / Notion). Conectores documentales ya reposicionados en `app/ingest_sources/` desde B0.5.

**Lo que este sprint NO hace** (para no exceder alcance):

- **No construye MO ni Tokens QR.** Eso es B4.
- **No construye DTM.** Eso es B3.
- **No construye Session Manager ni Scheduler.** Esos son parte de B4.
- **No construye el clasificador de intención.** Eso es B8.
- **No construye UIs de consulta.** Esas son B9 en adelante.
- **No elimina DII todavía.** Sigue `@deprecated`; su eliminación es post-B6 (cuando ya no haya callers).

## Alcance específico

### 1. Crear branch de trabajo

```bash
git checkout main
git pull origin main
git checkout -b sprint/B2-ingest-engine
```

Todo el trabajo en `sprint/B2-ingest-engine`. Push final + reporte; merge a main lo hace el fundador tras revisión.

### 2. Resolver pendiente técnico residual de B0

**2.1 Evaluar `cryptography==46`.**
Verificar si sigue causando conflicto con `msal` u otra dep instalada en B1. Si no estorba, pinear a versión actual. Si estorba, reportar PENDIENTE DE JORGE con análisis del conflicto y opciones. No bloqueador del sprint.

### 3. Investigación técnica Docling / PyTorch (decisión vinculante para el sprint)

Antes de construir el Dockerfile del worker, **Opus investiga y reporta**:

- ¿Docling 2.84.0 requiere PyTorch en runtime, o puede operar con backend ONNX?
- ¿Qué componentes específicos de Docling activan PyTorch (layout, OCR, table extraction, etc.)?
- ¿La extracción de tablas complejas y gráficos del PoC funcionaría con backend ONNX?

**Decisión vinculante para este sprint:** si Docling puede operar sin PyTorch para los casos de uso del mercado alfa (manual técnico, MSDS, calibración, especificación, ficha técnica), **PyTorch se retira del worker**. Si requiere PyTorch para algún caso documentado, se conserva y se justifica.

Reportar la decisión con argumento técnico en el reporte final. Si Opus determina que se necesita PyTorch pero solo para casos avanzados (algunos OCRs específicos), considerar conservarlo pero pinear versión específica CPU-only.

### 4. Worker de ingesta como Fly app aparte (`docyan-lde-ingest`)

**4.1 Estructura del directorio.**

Crear directorio `worker/` en raíz del repo (paralelo a `embedder/`) con:

- `worker/Dockerfile` — base `python:3.11-slim`. Stack: Docling, LlamaIndex, GraphRAG-SDK 1.1.1, LiteLLM, google-genai, openai, tiktoken, sentence-transformers (cliente HTTP al embedder externo), redis-py (para cola de jobs), pydantic v2. PyTorch solo si la investigación §3 lo justifica.
- `worker/main.py` — entry point del worker. Consume jobs de la cola Redis (o invocación HTTP, según §8), procesa documentos, escribe al grafo vía `dkg_client`.
- `worker/ingest_pipeline.py` — orquestación del pipeline: clasificar tipo de documento → seleccionar schema → cotizar → confirmar → procesar con Docling/LlamaIndex → GraphRAG-SDK extrae al grafo → BGE-M3 genera embeddings → deduplicate → finalize.
- `worker/requirements.txt` — solo lo necesario para el worker.
- `worker/fly.toml` — config Fly app: `docyan-lde-ingest`, región `dfw`, perfil de recursos según resultado de §3 (recomendación inicial: `shared-cpu-4x` / 4 GB RAM; ajustar según peso de Docling), volumen persistente NO requerido (worker stateless), sin `http_service` público (solo `*.flycast` para recibir jobs del backend principal).

**4.2 Crear app en Fly y deploy:**

```bash
flyctl apps create docyan-lde-ingest
cd worker
flyctl deploy --app docyan-lde-ingest
cd ..
```

**4.3 Variables de entorno del worker** (vía Fly secrets):

```bash
flyctl secrets set \
  GEMINI_API_KEY="<misma del backend>" \
  OPENAI_API_KEY="<misma del backend>" \
  FALKOR_HOST="docyan-lde-graph.internal" \
  FALKOR_PORT="6379" \
  EMBEDDER_URL="http://docyan-lde-embedder.internal:8000" \
  REDIS_QUEUE_URL="<según decisión §8>" \
  --app docyan-lde-ingest
```

### 5. Integración GraphRAG-SDK 1.1.1 — operativa (ingesta real al grafo)

**5.1 Verificar instalación en el worker.**

GraphRAG-SDK ya se agregó a `requirements.txt` en B1, pero NO al `requirements.docker.txt` del backend principal (correcto, no debe ir ahí). Para el worker, agregar al `worker/requirements.txt`.

**5.2 Resolver conflictos de versiones** con `pip install --dry-run`. Si hay conflicto con `google-genai`, `openai`, `litellm` (los tres ya están en el repo), reportar y resolver con el resolver real, no inventar pins.

**5.3 Configuración de modelos validada del PoC** (Adenda §3):

```python
# worker/llm_config.py
LLM_CONFIG = {
    "extraction_model": "gemini/gemini-2.5-flash",  # prefijo gemini/ OBLIGATORIO
    "qa_model": "gpt-4o-mini",
    "resolution_model": "gemini/gemini-2.5-flash",  # LLMVerifiedResolution
    "deduplicate_fuzzy": True,
    "force_spanish_in_extraction_prompt": True,
    "retry_with_tenacity": True,
}
```

**5.4 Adapter BGE-M3 desde B1 — reutilizar.**

`app/graph/embedder_adapter.py` ya existe (B1, 67 líneas). El worker importa y usa el mismo adapter para que GraphRAG-SDK genere embeddings vía BGE-M3, NO vía OpenAI ni Gemini. La verificación de dim=1024 ya está validada.

**5.5 Bug PoC #1 corregido.**

`deduplicate_entities(fuzzy=True)` se invoca con `await` correcto (no como llamada síncrona). El PoC dejó 653 residuos sin dedup por no ejecutarlo. Test de regresión obligatorio.

**5.6 `finalize_sync()` vs `finalize()`.**

GraphRAG-SDK tiene `finalize_sync()` pero NO `deduplicate_entities_sync()`. Manejar el async correctamente con `asyncio.run` o `await` según contexto.

### 6. Librería de schemas por tipo documental (mercado alfa)

**6.1 Estructura.**

Crear `app/schemas_documentales/` (en el backend principal, no en el worker — el worker la importa, pero la librería es del proyecto compartido):

```
app/schemas_documentales/
  __init__.py
  catalogo/
    __init__.py
    manual_tecnico.py
    msds.py
    calibracion.py
    especificacion.py
    ficha_tecnica.py
  generador.py
  registry.py
  selector.py
```

**6.2 Cinco tipos del mercado alfa** — cada uno define en código:

- **Entidades específicas** que el schema espera extraer (ejemplo MSDS: `:Sustancia`, `:Riesgo`, `:MedidaProteccion`, `:EquipoProteccion`, `:NumeroCAS`).
- **Relaciones específicas** (ejemplo MSDS: `:Sustancia -[:TIENE_RIESGO]-> :Riesgo`, `:Riesgo -[:REQUIERE_MEDIDA]-> :MedidaProteccion`).
- **Prompt de extracción** ajustado al tipo (qué buscar, qué ignorar, en qué idioma forzar la respuesta).
- **Mapeo a visualización** (qué tipo de intención del catálogo de 11 lo consume — para B9 y B5).

**Manual técnico:** `:Procedimiento`, `:Paso`, `:Advertencia`, `:Herramienta`, `:EPP`. Mapeo: Tipo 2 (procedimientos paso a paso).
**MSDS:** `:Sustancia`, `:Riesgo`, `:MedidaProteccion`, `:NumeroCAS`. Mapeo: Tipo 6 (eventos operativos + alertas) y Tipo 7 (alertas administrativas).
**Calibración:** `:Instrumento`, `:CertificadoCalibracion`, `:MedicionRegistrada`, `:FechaVencimiento`, `:Tecnico`. Mapeo: Tipo 6 y Tipo 7.
**Especificación:** `:Especificacion`, `:ParametroTecnico`, `:Tolerancia`, `:UnidadMedida`. Mapeo: Tipo 1 (datos puntuales) y Tipo 8 (comparativos entre versiones).
**Ficha técnica:** `:Producto`, `:CaracteristicaTecnica`, `:Modelo`, `:Fabricante`. Mapeo: Tipo 1 y Tipo 3 (recursos visuales/etiquetas).

Todos los nodos extraídos por estos schemas se conectan al grafo objetivo del doc 01 (a `:DocumentoSource`, `:EntidadOperativa`, etc.) — la librería no construye un grafo paralelo; controla **cómo se extrae** hacia el grafo unificado.

**6.3 Generador dinámico Gemini para schemas fuera de catálogo.**

`app/schemas_documentales/generador.py`:

- Recibe documento + contexto (industria, operación, par lingüístico, tier, idioma).
- Analiza muestra del documento con Gemini 2.5 Flash.
- Deriva schema candidato (entidades + relaciones + prompt + mapeo de visualización tentativo).
- Retorna schema operable para esa sesión de ingesta.

**Caso de uso documentado:** un cliente de Pista B sube un tipo no contemplado (ej. acta de inspección regulatoria de un país nuevo); el generador produce schema en runtime.

**6.4 Registry vivo.**

`app/schemas_documentales/registry.py`:

- Registro de schemas activos por tenant (catálogo + generados dinámicamente).
- Schemas generados que demuestran utilidad (frecuencia de uso, extracción exitosa) se proponen como candidatos a integrar al catálogo permanente.
- Persistencia en Supabase (tabla `tenant_schemas` con `tenant_id`, `tipo_documento`, `schema_def` JSONB, `es_generado_dinamicamente`, `uso_contador`).

**6.5 Selector de schema.**

`app/schemas_documentales/selector.py`:

- Recibe documento + metadata.
- Estrategia: clasificación heurística primero (nombre del archivo, primeras N páginas, palabras clave) → si no calza con catálogo del tenant → invoca generador dinámico.
- Decisión técnica del sprint: si la clasificación heurística no es confiable (precision <90% en tests), usar Gemini 2.5 Flash para clasificar tipo de documento como paso previo a seleccionar schema. Reportar la decisión con argumento.

### 7. Cotizador pre-ingesta con tiktoken (CRÍTICO — Adenda §8)

**7.1 Funcionalidad.**

Antes de cualquier ingesta al grafo, el cotizador:

1. Mide tokens del documento con tiktoken (ya en deps desde B0).
2. Estima costo:
   - Extracción (Gemini 2.5 Flash): tokens × precio Gemini Flash input + estimación de tokens output × precio output.
   - QA (gpt-4o-mini): tokens × precio gpt-4o-mini input + tokens output × precio output.
   - Embeddings (BGE-M3 self-hosted): costo computacional interno, marginal pero reportable.
3. **Baselines del PoC** para validación de coherencia: NOM 32 pp ~$0.036 USD, Ley 61 pp ~$0.046 USD, corpus 50 normas + 10 leyes ~$2.26 USD.
4. Estima **tiempo de procesamiento** además de costo. PoC: Gemini Flash 642 s para una NOM + 1,506 retries por rate limiting en multi-doc.
5. **Verifica presupuesto disponible del tenant** (no solo estima). Lee tabla `tenant_budget` en Supabase con saldo prepagado.
6. **Si presupuesto insuficiente, rechaza con explicación clara** (no ingiere y notifica al PM con cuánto falta).
7. **Si presupuesto suficiente, presenta estimación + pide confirmación**. Sin confirmación, no ingiere.
8. Opera el **Token Budget por plan** definido en project instructions.

**7.2 Protección financiera multinivel.**

- Saldo prepagado finito sin auto-recharge (cliente debe recargar manualmente).
- Hard cap por documento (umbral configurable por tenant, default $5 USD para alfa).
- Hard cap por sesión de ingesta (default $20 USD para alfa).
- Cotizador como guard previo a invocar GraphRAG-SDK.

**7.3 Componentes.**

```
app/ingesta/
  cotizador.py          # estimación + verificación de presupuesto
  budget_manager.py     # operaciones sobre tenant_budget
  pricing_table.py      # precios actuales de Gemini Flash, gpt-4o-mini
```

**7.4 Migración Supabase para budget.**

Crear `migrations/008_tenant_budget.sql` con tabla `tenant_budget` (tenant_id, saldo_actual_usd, hard_cap_por_documento, hard_cap_por_sesion, ultima_recarga, fecha_creacion, RLS multi-tenant).

### 8. Dispatcher de jobs backend → worker

**8.1 Decisión técnica del sprint** (Opus elige y justifica):

**Opción A — Cola Redis con `rq` o similar.** Backend principal encola jobs en Redis (`docyan-lde-graph` ya tiene Redis-compatible API por ser FalkorDB sobre Redis; alternativa: una segunda Fly app `docyan-lde-redis` o usar el Redis de Supabase si está disponible). Worker consume de la cola con polling o blocking pop.

**Opción B — Invocación HTTP directa.** Backend principal hace `POST` a un endpoint interno del worker (`http://docyan-lde-ingest.internal:8000/jobs`). Worker procesa síncrono y responde con job_id; estado se consulta vía polling al worker o vía evento en grafo.

**Opción C — Fly machine API.** Backend principal lanza una Fly machine ephemeral cada vez que hay job. Worker queda como imagen "fría" que se invoca on-demand.

**Mi recomendación inicial: A (cola Redis con rq).** Razones: separación clean de concerns, retry nativo, monitoring fácil, escalable horizontal (múltiples workers si crece la carga), Redis ya en stack por decisión #6 Paso C. Pero Opus puede argumentar otra opción si encuentra razón técnica.

Si Opus elige A, asegurar que Redis existe como recurso accesible. Si no existe Redis aparte, levantar `docyan-lde-redis` como Fly app aparte en este sprint o usar Redis Cloud / Upstash. Documentar la decisión.

**8.2 Componentes en backend principal:**

```
app/jobs/
  dispatcher.py         # encola jobs hacia el worker
  job_models.py         # Pydantic models de jobs (ingest_document, etc.)
  job_status.py         # consulta de estado de jobs
```

**8.3 Endpoint del backend principal para iniciar ingesta:**

`POST /ingesta/documents` que recibe un documento (multipart/form-data), llama al cotizador, retorna estimación + job_id pendiente de confirmación; luego `POST /ingesta/documents/{job_id}/confirm` que dispara el dispatcher al worker.

### 9. Persistencia inicial de `consulta_realizada` y `:Observacion`

**Preparación para Playbook Nivel A futuro (B7+/B8+), sin construir lógica de Playbook todavía.**

El schema DKG de B1 ya soporta:
- `:EventoOperativo` con `tipo = "consulta_realizada"` (verificar en `app/graph/schemas/dkg_ontology.py` de B1).
- `:Observacion` para anotaciones (verificar).

Este sprint añade:

**9.1 Hook básico en el flujo de consulta (placeholder funcional).**

Cuando el backend principal sirva una consulta (vía endpoint existente, aunque la consulta real con clasificador completo es B8), persistir un `:EventoOperativo` con:
- `tipo = "consulta_realizada"`
- `tenant_id`
- `usuario_id` (de la sesión JWT)
- `consulta_texto`
- `timestamp`
- `entidad_consultada_id` (si aplica, sino null)
- `respuesta_resumen` (primeras 500 chars de la respuesta)

**9.2 Endpoint para registrar `:Observacion` por usuario.**

`POST /entities/{entity_id}/observations` que crea un `:Observacion` vinculado a la entidad. Cubre el caso de un operador anotando algo sobre una entidad operativa. Stub funcional — la UI que lo consume es B9.

**9.3 Sin construir lógica de Playbook todavía.** Solo asegurar que la persistencia mínima ocurre para que cuando B7+ implemente la detección de patrones repetidos (para sugerencia Nivel C del Playbook), tenga datos sobre los cuales detectar.

### 10. Tests automatizados requeridos

Tests bloqueadores (si fallan, sprint no cierra):

- `tests/test_worker_deployment.py` — el worker arranca, conecta a FalkorDB, conecta al embedder.
- `tests/test_ingest_pdf_manual_tecnico.py` — un PDF de manual técnico se ingiere completo, el grafo queda poblado con `:Procedimiento`, `:Paso`, `:Advertencia` esperados, provenance `MENTIONED_IN` + spans presente.
- `tests/test_ingest_pdf_msds.py` — un PDF de MSDS se ingiere con schema MSDS, el grafo queda poblado con `:Sustancia`, `:Riesgo`, `:MedidaProteccion`.
- `tests/test_schema_selector.py` — el selector elige correctamente el schema según tipo de documento (manual técnico vs MSDS vs ficha técnica).
- `tests/test_schema_generator_dinamico.py` — documento fuera del catálogo (replica caso LGPGIR del PoC) → generador produce schema y extrae **>0 relaciones**, NO falla con 0.
- `tests/test_schema_registry.py` — schema generado queda persistido en registry y es reutilizable.
- `tests/test_cotizador_baselines.py` — un documento de tamaño conocido produce estimación cercana a baseline del PoC (±15% tolerancia).
- `tests/test_cotizador_budget_insufficient.py` — si presupuesto insuficiente, rechaza ingesta con mensaje claro, NO procesa.
- `tests/test_cotizador_requires_confirmation.py` — sin confirmación explícita, no se invoca a GraphRAG-SDK.
- `tests/test_dedup_with_fuzzy.py` — regresión del bug PoC #1: `deduplicate_entities(fuzzy=True)` ejecuta con `await` correcto y reduce duplicados.
- `tests/test_dispatcher_job_flow.py` — backend encola job, worker lo recoge, lo procesa, marca como completo.
- `tests/test_consulta_realizada_persisted.py` — al servir una consulta, `:EventoOperativo` con tipo `consulta_realizada` queda persistido en el grafo del tenant.

Tests previos siguen pasando: 103+ del baseline B1.

### 11. Salida verificable (criterio último de cierre)

- ✅ `flyctl apps list` muestra los 4 procesos en estado deployed: `docyan-lde-api`, `docyan-lde-graph`, `docyan-lde-embedder`, `docyan-lde-ingest`.
- ✅ `flyctl status --app docyan-lde-ingest` muestra máquina respondiendo.
- ✅ Desde el backend en producción: `POST /ingesta/documents` con un PDF de manual técnico → retorna estimación de costo + job_id.
- ✅ `POST /ingesta/documents/{job_id}/confirm` → dispatcher encola, worker procesa.
- ✅ Tras procesamiento (esperar a job completo): `GET /entities?tenant_id=X&tipo=Procedimiento` retorna procedimientos extraídos del PDF, con provenance clickeable (campo `documento_fuente_id` apuntando a `:DocumentoSource` y `spans` con offsets).
- ✅ El mismo PDF subido a un segundo tenant produce datos en su graph aislado (test de no-cross-tenant en producción real).
- ✅ Documento del mercado regulatorio (replica caso LGPGIR del PoC) → generador produce schema, extrae >0 relaciones (verificable con Cypher).
- ✅ Cotización rechaza documento que excede `hard_cap_por_documento` del tenant.
- ✅ CI verde en `sprint/B2-ingest-engine`.
- ✅ Las 4 apps Fly siguen respondiendo (api health 200, embedder respondiendo, graph PING, ingest health 200).

Si alguno de estos criterios falla, el sprint no cierra hasta que pase.

### 12. Documentación

- `docs/worker_architecture.md` — diseño del worker, decisión técnica de §8 (cola Redis vs HTTP vs Fly machines), perfil de recursos, decisión sobre PyTorch de §3.
- `docs/schemas_documentales.md` — referencia rápida de los 5 schemas del mercado alfa, cómo invocar al generador, cómo el registry persiste.
- `docs/cotizador.md` — funcionamiento del cotizador, baselines del PoC, política de hard caps, cómo el PM ve y maneja el budget.
- Actualizar `README.md` con los 4 procesos.
- Actualizar `CLAUDE.md` con la nueva topología y la advertencia "todo job de ingesta pasa por cotizador, no hay bypass".
- Actualizar `docs/dkg_topology.md` (de B1) para reflejar los 4 procesos.

### 13. Notas para Opus sobre integración con código existente

- B1 ya cerró infraestructura DKG completa. **No tocar `app/graph/`** salvo para usar `dkg_client.py` desde el worker (importación, no modificación).
- `app/graph/embedder_adapter.py` (B1, 67 líneas) — **reutilizar tal cual desde el worker**.
- `app/graph/schemas/dkg_ontology.py` (B1, 306 líneas) — la librería de schemas documentales del §6 NO duplica esta ontología. La ontología es el grafo objetivo; la librería controla cómo extraer hacia ese grafo. Coexisten.
- DII (`app/core/dii.py`) **sigue `@deprecated` desde B1**. No se elimina aún (B6 podría usarlo para bilingüe).
- Docling y LlamaIndex ya en `requirements.txt` desde B0; mover/duplicar a `worker/requirements.txt` para el worker.
- tiktoken ya en deps desde B0; reutilizar.
- `app/ingest_sources/` (B0.5) — stubs de Google Drive, OneDrive, FTP, Notion. **Este sprint NO implementa el modo conectado de ingesta** (Adenda §6.1); se implementa en B12 (Onboarding) o sprint dedicado posterior. Por ahora solo se valida que los stubs siguen presentes y compilan; el flujo activo de B2 es el modo manual (usuario sube archivo).
- `app/api/routers/ingest_sources.py` (B0.5) — los stubs siguen siendo stubs. El nuevo endpoint operativo de este sprint es `app/api/routers/ingesta.py` (manual), separado del router `ingest_sources` (conectado).
- pin de `litellm` ya hecho en B1; verificar versión y mantener.

### 14. Reglas de ejecución

- Trabajar exclusivamente sobre la rama `sprint/B2-ingest-engine`. No commitear a main directamente.
- No stubs ocultos: si algo se difiere a sprint posterior, está deliberadamente y comentado en el código.
- No diferir alcance dentro del sprint. Si algo es genuinamente bloqueador, reportar, continuar con lo demás, marcar PENDIENTE DE JORGE.
- Verdad operacional: reportar estado real de la 4ta app Fly (deploy, health, recursos consumidos), no proyección. Reportar tamaño real de la imagen del worker.
- Tests siguen pasando en cada paso, no solo al final.
- Push de la rama al cierre con todos los commits y reporte completo.
- Si conflicto de versiones entre Docling, LlamaIndex, GraphRAG-SDK, LiteLLM, google-genai, openai: **ejecutar resolver real (`pip install --dry-run`), reportar lo que dice, no inventar pins**.
- Si la investigación §3 indica que PyTorch debe quedarse, **monitorear tamaño de imagen del worker** — si supera 4 GB descomprimida, evaluar reducción agresiva (slim base, multi-stage, etc.) antes de aceptar.
- El cotizador **es un gate**. No hay bypass aceptable bajo ninguna circunstancia — ni para "tests rápidos" ni para "desarrollo local". Si hace falta saltar el cotizador para algún test, el test usa un mock explícito del cotizador, no lo desactiva.

---

**Referencias:** doc 01 (Modelo Datos DKG), doc 02 (Modelo Datos DTM — para entender el destino de los segmentos que B3 construirá), doc 05 (Master Orchestrator — para entender qué orquesta más tarde), doc 09 (Multi-tenant y Roles), doc 10 (Stack Técnico), doc 14 (Plan de Bloques), Adenda secciones 2, 3, 5, 6, 6.1, 8, decisiones #1, #3, #11, #12 del Paso C, reportes de cierre B0, B0.5, B1, B1.5, REPORTE_CONTRATO4 y 5 del PoC del 28 may 2026.

---

*Fin del Sprint Contract B2.*
