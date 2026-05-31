# CLAUDE.md — DOCYAN LDE™ by XCID

> **Archivo de contexto operativo para Claude Code CLI (Opus 4.8).**
> Este archivo se lee al inicio de cada sesión. NO es documentación arquitectónica — para eso existen los Sprint Contracts y los docs 00-14 que Jorge pega en cada sesión cuando aplica. Este archivo es **cómo trabajar en este repo**.
>
> **Actualizado 28 mayo 2026** — post-PoC GraphRAG-SDK + rebrand Panohayan→DOCYAN + siglas DKG/DTM. Incorpora la adenda post-PoC (`docs/adenda_postPoC_28mayo2026.md`) como ley operativa.

---

## 1. Producto

**DOCYAN LDE™ — Live Document Environment — by XCID**
Empresa: XCID SA de CV. Fundador: Jorge Luis Amparán Hernández.

DOCYAN LDE™ es la marca propia; XCID es la empresa matriz; XCID Inside es el motor invisible. "Yan" = "lugar" en náhuatl → "el lugar de los documentos". El nombre anterior **Panohayan** queda obsoleto: toda referencia a "Panohayan" en código o docs es deuda de rebrand y debe limpiarse. En código y assets visibles usar **DOCYAN LDE™**. En código interno (clases, paquetes, módulos) usar `docyan` según contexto. El paquete Python es `app` (no `docyan/` ni `panohayan/`).

**NO es una herramienta CAT.** Es una capa de gobernanza lingüística + documento vivo consultable vía QR + IA con renderización condicional por tipo de intención.

**Dos pistas comerciales paralelas** (no secuenciales):

- **Pista A** — México industrial directo: laboratorios ISO 17025, maquiladoras IMMEX corredor T-MEC. Motor de Traducción Rigurosa de 6 fases.
- **Pista B** — Internacional vía agencias profesionales: ingesta bilingüe (TMX/XLIFF/etc.) + alineamiento Vecalign+Hunalign + consulta multilingüe. **Sin motor de traducción**.

---

## 2. Cómo trabajar en este repo

### 2.1. Un Sprint = una aprobación + ejecución completa + un reporte

1. Jorge pega un Sprint Contract en CLI.
2. Tú (Opus) ejecutas el Sprint Contract **completo**, sin pedir confirmaciones intermedias.
3. Generas **un reporte final** al terminar.
4. Jorge revisa el reporte y aprueba el siguiente sprint.

**NO** iteres en multi-fases dentro del mismo sprint. **NO** preguntes "¿quieres que continúe?" entre componentes del mismo bloque. Si encuentras un bloqueador real, lo documentas en el reporte y sigues con lo que sí puedes ejecutar.

### 2.2. Verdad operacional sobre proyección optimista

Lo aprendiste por las malas en el repo previo (auditoría 25 abril 2026: reportaste "tests pasando" cuando había cero tests). Esto **no se repite**.

En cada reporte final:

- ✅ "X funciona, verificado con test Y que pasa con output Z" → afirmación válida.
- ❌ "X debería funcionar" → afirmación inválida. Verifica o no lo digas.
- ❌ "Pendiente de prueba con datos reales" usado como muletilla para no testear → inválido.

Si algo no se ejecutó, dilo explícito. Si algo se ejecutó parcialmente, di qué parte sí y qué parte no. Si encontraste un bloqueador, di cuál es con detalle técnico.

### 2.3. Tests automatizados desde día 1

**Decisión cerrada (Paso C #14)**: testing balanceado 60-70% backend / 40-50% frontend, GitHub Actions en CI.

- Backend: `pytest` con `pytest-asyncio` + `httpx.AsyncClient` para tests de FastAPI.
- Frontend: `Vitest` (unit) + `Playwright` (E2E).
- **Sin tests = sprint no terminado.** No reportes "completado" si no hay tests escritos y pasando para el componente nuevo.
- Cobertura objetivo ≥75% en módulos nuevos.

### 2.4. No stubs, no mocks, no hardcoded

Todo lo que el Sprint Contract describe se construye **real**. No stubs funcionales, no mocks fuera de tests, no valores hardcodeados que simulen funcionalidad. Un placeholder explícito de verificación de toolchain (ej. "boot OK") es legítimo; un stub que finge una capacidad no lo es.

### 2.5. Disciplina de contratos backend↔frontend

- Backend: schemas Pydantic v2 estrictos exportan OpenAPI 3.1.
- Frontend: tipos TypeScript generados con `openapi-typescript` desde el OpenAPI del backend.
- **Regenerar tipos cada vez que backend cambia** — automatizar en CI antes del build del frontend.
- No hardcodear tipos en frontend; siempre desde el contrato.

### 2.6. Multi-tenant strict

Cada query a FalkorDB, Supabase o Redis lleva `tenant_id` resuelto del usuario logueado. En el grafo, el aislamiento es nativo por `graph_name` de GraphRAG-SDK mapeado a `tenant_id`.

Tests E2E deben verificar que no hay leaks entre tenants. Esta es regla inviolable, no opcional.

### 2.7. PENDIENTE DE JORGE

Cuando encuentres algo no resuelto en el modelado o en el Sprint Contract:

- Marca explícitamente como `PENDIENTE DE JORGE` en el reporte.
- **No inventes la respuesta.** No tomes decisiones de modelado o arquitectura por tu cuenta.
- Sigue ejecutando lo demás que sí puedes.
- En el reporte: lista todos los PENDIENTE DE JORGE en orden de criticidad.

### 2.8. Decisiones cerradas que NO se re-validan

Las 15 decisiones del Paso C están cerradas. La adenda post-PoC está cerrada. **No vuelvas a abrirlas.** Si un Sprint Contract menciona una decisión, asume que está tomada.

Si genuinamente crees que una decisión está mal y tienes argumento técnico concreto: lo escribes en el reporte como "Observación técnica para Jorge" — pero **ejecutas igual** lo que dice el Sprint Contract. La decisión de cambiar es de Jorge, no tuya.

---

## 3. Stack técnico (cerrado, no negociable)

### Backend
- Python 3.11
- FastAPI + Pydantic v2
- httpx + asyncio + uvicorn
- Gestión de dependencias: `pyproject.toml` (+ `requirements.txt` / `requirements.docker.txt` mientras se completa la migración)

### Arquitectura de ingesta — GraphRAG-SDK (CAMBIO MAYOR post-PoC)
- **FalkorDB GraphRAG-SDK 1.1.1** es el motor de ingesta y construcción de grafo. **Reemplaza al DII anterior.**
- El DII causó el incidente de $5,000 con Gemini (timeout 600s, workers reactivándose, escritura parcial, sin control de costo). NO se revive.
- El SDK aporta: ingesta <5min sin timeouts, escritura transaccional, provenance nativo (`MENTIONED_IN`/`PART_OF`/`NEXT_CHUNK` + spans de caracteres), multi-tenancy por `graph_name`, `apply_changes()` incremental crash-safe con SHA-256, estrategias swappables, LLM-agnóstico vía LiteLLM.

### Stack de ingesta multi-formato
```
Formatos diversos (docx, xlsx, pptx, imágenes, CFDI/XML, TMX/XLIFF/TBX/SDLXLIFF/Bilingual DOCX)
    ↓
Docling (conversión universal + OCR + tablas complejas y gráficos)
    +
LlamaIndex (indexación semántica sin schema rígido)
    ↓
GraphRAG-SDK 1.1.1
    ↓
FalkorDB (multi-tenant por graph_name)
```
GraphRAG-SDK ingiere nativamente PDF, Markdown y texto; Docling cubre el resto de formatos.

### Config de modelos de ingesta (validada con PoC sobre NOM-052 — distinta del MR de traducción)
- **Extracción:** Gemini 2.5 Flash — `gemini/gemini-2.5-flash` vía LiteLLM. **El prefijo `gemini/` es OBLIGATORIO**, o LiteLLM defaultea a Vertex AI y falla pidiendo credenciales GCP.
- **QA / consulta:** gpt-4o-mini.
- **Resolution:** Gemini 2.5 Flash (LLMVerifiedResolution).
- **Post-proceso:** `deduplicate_entities(fuzzy=True)` para entidades de alto volumen.
- **Variables:** `GEMINI_API_KEY` (NO `GOOGLE_API_KEY`), `OPENAI_API_KEY`.
- Evidencia: Gemini 2.5 Flash infiere sujetos implícitos de voz pasiva regulatoria ("deberán identificarse..." → Generador). Extrajo 15 obligaciones vs 4 de gpt-4o, a costo de gpt-4o-mini (~$0.04/doc).

### Sistema de esquemas por tipo documental — COMPONENTE CENTRAL
El schema de extracción debe corresponder al **TIPO de documento + contexto del usuario**, no solo al dominio. Evidencia PoC: un schema de norma técnica (NOM-052) extrajo **0 relaciones** de una ley general (LGPGIR). Dos capas:
1. **Catálogo del mercado meta** — todos los tipos presentes desde el diseño (NOM, ley, reglamento, ISO, manual técnico, MSDS, calibración, especificación, ficha técnica, memoria de traducción), todos ajustables por feedback de pilotos. Ninguno se descarta ni se difiere.
2. **Generador dinámico (Gemini 2.5 Flash)** — analiza documento + contexto de usuario y deriva el schema cuando no calza con el catálogo, en vez de fallar. Los schemas generados realimentan el catálogo.
El tipo de documento define tanto el schema de extracción como la visualización (B8).

### LLMs de traducción (vía Model Router existente — 4 tiers)
- Claude Sonnet 4.6 + Gemini 2.5 Pro.
- **Tier medio piloto para todo.** Ruteo por criticidad presente pero desactivado hasta primer cliente.
- Esta config es SOLO para el flujo de traducción Pista A. NO confundir con la config de ingesta de arriba.

### Bases de datos
- **FalkorDB**: DKG (Document Knowledge Graph) + DTM (Document Translation Memory). Self-hosted en Fly.io. Vía GraphRAG-SDK.
- **Supabase (PostgreSQL)**: operacional + FAT spillover + auth.
- **pgvector**: embeddings (extensión Supabase).
- **Redis**: sesiones MO + scheduler backend APScheduler. Self-hosted en Fly.io.

### Embeddings
- **BGE-M3 self-hosted** desde día 1. NO OpenAI text-embedding.
- Se configura como embedder custom de GraphRAG-SDK (vía interfaz ABC del SDK o LiteLLM). El PoC usó OpenAI por simplicidad; NO invalida la decisión de BGE-M3.

### Matching fuzzy
- Híbrido Levenshtein + BGE-M3 dos pasadas.
- Score 70/30 bandas altas, 30/70 bandas bajas.
- Umbral mínimo léxico ≥30% para invocar vectorial.
- Tabulador estándar industria: 100% / 95-99% / 85-94% / 75-84% / 50-74% / 0-49%.

### Alineadores Pista B
- **Vecalign primario + Hunalign fallback.** Ambos día 1.

### Cotizador pre-ingesta — CRÍTICO
- tiktoken mide cada documento ANTES de ingerir, estima costo, verifica presupuesto disponible del tenant, pide confirmación.
- El PoC demostró con incidente controlado (ingesta topó hard cap de Google a MXN 119) que NO es opcional.
- Protección financiera: saldo prepagado finito sin auto-recharge + hard cap + cotizador.

### Frontend
- TypeScript estricto
- Next.js 15 App Router + React 19
- Tailwind CSS
- shadcn/ui sobre Radix Primitives
- react-i18next (independiente del framework)

### Hosting — topología de 5 procesos Fly (B1 + B2/B2.1)
Desde B1 NO es monolítico. Cada componente es una Fly app separada (razón:
imagen backend <1 GB, BGE-M3 arrastra torch ~3 GB, FalkorDB necesita volumen +
RPO 15 min, escalado independiente). B2 agregó el worker de ingesta; B2.1 agregó
el Redis compartido. Detalle: `docs/dkg_topology.md`.

- **Fly.io**:
  - `docyan-lde-api` — backend FastAPI (consultas, MO, clasificador, admin). Público.
  - `docyan-lde-graph` — FalkorDB self-hosted (DKG + DTM). Privado (`.internal:6379`), volumen `/data`. Config: `fly.graph.toml`. Acceso: `FALKOR_HOST`/`FALKOR_PORT`.
  - `docyan-lde-embedder` — BGE-M3 self-hosted (1024 dim). Privado (`.internal:8000`). Dir: `embedder/`. Acceso: `EMBEDDER_URL`.
  - `docyan-lde-ingest` — worker de ingesta (Docling + GraphRAG-SDK + LiteLLM + PyTorch CPU). **Construido en B2** (`worker/`). Privado (flycast:8000, solo `/health`), stateless. Consume jobs de una **cola Redis** (decisión §8 = Opción A). Vive aparte porque graphrag-sdk fuerza `transformers<5.2.0`/`typer<0.26` y arrastra PyTorch (`gliner`) + Docling (`docling-ibm-models`/TableFormer), incompatibles con el backend <1 GB. **PyTorch se conserva CPU-only**: TableFormer y gliner lo exigen incondicionalmente; no hay TableFormer en ONNX (decisión §3). Excluye los conectores (msal/etc.), lo que libera a `cryptography` del tope `<46` que impone msal (§2). Detalle: `docs/worker_architecture.md`.
- **Cotizador pre-ingesta (`app/ingesta/`) — GATE SIN BYPASS.** Todo documento se cotiza (tiktoken + presupuesto + hard caps) ANTES de ingerir; sin saldo/confirmación no hay ingesta. Justificación: incidente PoC $5,000. En tests se mockea el almacén (`InMemoryBudgetStore`), NUNCA la decisión. Detalle: `docs/cotizador.md`. Schemas por tipo documental en `app/schemas_documentales/` (`docs/schemas_documentales.md`).
  - `docyan-lde-redis` — Redis 7-alpine compartido. **Construido en B2.1** (`redis/`). Privado (`.internal:6379` / flycast), volumen `redis_data` en `/data`, AOF + `maxmemory-policy noeviction`. Doble propósito: **cola de ingesta** (B2, `REDIS_QUEUE_URL`) + **Session Manager/APScheduler** (B4, `REDIS_URL`, decisión #6). Detalle: `redis/README.md`.
- **Redis**: lo provee `docyan-lde-redis` (cola de ingesta B2 + sesiones MO/APScheduler B4).
- **Vercel**: frontend (las 4 UIs).

Clientes en el backend: `app/graph/dkg_client.py` (fachada DKG multi-tenant,
cliente `falkordb`) y `app/embeddings/bge_client.py` (cliente HTTP puro al
embedder). `graphrag-sdk`/`litellm` NO van a la imagen del backend (viven en el
worker B2); el backend solo usa el cliente `falkordb` (ligero).

### WhatsApp
- **360dialog directo** (BSP único, sin Twilio). Decisión #8.

### Scheduler
- **APScheduler con backend Redis.** Decisión #3.

---

## 4. Glosario canónico (memoriza, no inventes)

| Sigla | Significado | Notas |
|---|---|---|
| **DKG** | Document Knowledge Graph | Sobre FalkorDB vía GraphRAG-SDK. Multi-tenant strict por `graph_name`. (Antes PKG.) |
| **DTM** | Document Translation Memory | Sobre FalkorDB. Segregación estricta por par lingüístico. **No es TM tradicional.** (Antes PTM.) |
| **LDE** | Live Document Environment | El producto completo. (Antes DLE — Document Localization Engine.) |
| **MO** | Master Orchestrator | Pieza central. Doc 05. Orquesta el negocio; la ingesta interna la cubre el SDK. |
| **DII** | Document Ingestion Intelligence | **OBSOLETO. Reemplazado por GraphRAG-SDK.** Se marca deprecated en B1, se elimina tras B5. NO construir sobre él. |
| **EDB** | Entity Data **Brain** | Almacén **activo** que propone. **NO** "Entity Database". |
| **GRG** | Guardrail Governance | Existe en repo. Extendido en doc 07 (B6, con hash chain). |
| **FAT** | Foundation Audit Trail | Existe en repo (`matrix.py`/`TraceabilityMatrix`). Extendido en doc 08 (B6) con SHA-256 hash chain. |
| **MR** | Model Router | Existe (98 LOC, 4 tiers, con tests). Se mantiene. Para traducción, no para ingesta. |
| **RI** | Resilient Infrastructure | — |
| **GraphRAG-SDK** | FalkorDB GraphRAG-SDK 1.1.1 | Motor de ingesta y grafo. Reemplaza DII. |
| **CAT** | Computer-Aided Translation | **Referencia comparativa, NO stack de DOCYAN.** Trados/MemoQ/Phrase/XTM/SmartCAT. |

### Cosas eliminadas (no las uses)

- ❌ **Panohayan**: nombre anterior. Toda ocurrencia en código/docs es deuda de rebrand a DOCYAN.
- ❌ **PKG / PTM**: siglas anteriores. Ahora DKG / DTM.
- ❌ **DII como pipeline activo**: reemplazado por GraphRAG-SDK. Marcar deprecated, no extender.
- ❌ **Kiuey**: alucinación de Gemini en exploración inicial. Cualquier referencia es bug, debe limpiarse.
- ❌ **Rol "Traductor humano"**: ELIMINADO del modelo de roles. El Motor de Traducción ocupa esa función. Los humanos en el flujo son **revisores**, no traductores.
- ❌ **"TM tradicional"**: DOCYAN DTM es grafo ontológico, no una TM convencional. No la trates como una.
- ❌ **"Entity Database"**: es Entity Data **Brain**. Almacén activo.
- ❌ **Railway**: hosting anterior. Migrado a Fly.io. `railway.toml` se elimina en B0.

---

## 5. Las 15 decisiones del Paso C (cerradas — referencia rápida)

| # | Decisión | Compromiso |
|---|---|---|
| 1 | Embeddings | BGE-M3 self-hosted desde día 1 (embedder custom de GraphRAG-SDK) |
| 2 | Matching fuzzy | Híbrido Levenshtein + BGE-M3, score 70/30 altas, 30/70 bajas, umbral léxico ≥30% |
| 3 | Scheduler | APScheduler + Redis |
| 4 | Alineador Pista B | Vecalign primario + Hunalign fallback |
| 5 | i18n UI | react-i18next |
| 6 | Sesiones MO | Redis con TTL diferenciado + spillover Supabase para completadas |
| 7a | Hosting backend | Fly.io |
| 7b | Hosting frontend | Vercel |
| 8 | WhatsApp BSP | 360dialog directo, sin markup |
| 9 | Framework frontend | Next.js 15 App Router + React 19 + Tailwind |
| 10 | Componentes UI | shadcn/ui sobre Radix Primitives |
| 11 | Versionado DKG | In-place + aristas `:VERSION_HISTORICA` |
| 12 | Backup FalkorDB | RPO 15min, RTO 4h, retención 7 años producción / 3 años operativo |
| 13 | Pricing | Mantener precios actuales hasta primer cliente real |
| 14 | Testing | Balanceado 60-70% backend / 40-50% frontend, CI GitHub Actions |
| 15 | Criticidad por segmento | OBLIGATORIA en Onboarding Step 9, delegable a inferencia automática del pipeline |

---

## 6. Plan de 14 bloques (Paso D, actualizado post-PoC — ver `docs/Plan_Desarrollo_MVP_DOCYAN_v2_postPoC.md`)

| # | Bloque | Salida verificable |
|---|---|---|
| B0 | Fundación + migración + rebrand | Repo `docyan-lde-core` en Fly.io + Vercel, frontend bootstrapeado, tests en CI, rebrand total |
| B1 | DKG sobre GraphRAG-SDK + sistema de esquemas | Schema multi-tenant + versionado + catálogo del mercado meta + generador dinámico |
| B2 | DTM | Schema DTM + segregación por par + TM dual + lock terminológico |
| B3 | MO + Tokens QR + Cotizador | QR resuelve a contexto + cotizador pre-ingesta funcional |
| B4 | Motor Traducción Rigurosa (Pista A) | Doc traducido en formato original con scoring + lock activo |
| B5 | Ingesta Bilingüe (Pista B) | Agencia carga TMX/XLIFF, ingiere correctamente |
| B6 | GRG + FAT extendidos | Reglas + cadena criptográfica SHA-256 + reportes |
| B7 | Clasificador Intención + Pipelines 1-8 + Chat persistente | Consulta clasifica y ejecuta pipeline correcto; chat multi-turno |
| B8 | UI #1 Consulta PWA + Visualizaciones + Anotaciones + Alertas | Operador consulta vía PWA, renderización condicional, alertas administrativas |
| B9 | WhatsApp + Channel Adapter | Operador consulta vía WhatsApp en su idioma |
| B10 | UI #2 Revisión Lingüística | Revisor humano valida documento completo |
| B11 | UI #3 PM Dashboard | PM gestiona proyectos, asigna revisores, cotiza |
| B12 | UI #4 Onboarding | Cliente nuevo completa onboarding y queda activo |
| B13 | Tipos 9-11 potenciales + Hardening | Producto vendible primer cliente, monitoreado |

Paralelismos posibles: B4↔B5, B6 paralelo a B4/B5, B8↔B10.

**MVP demo-able** = B0+B1+B2+B3+B4+B6+B7+B8+B12. Hasta entonces, silencio comercial (ver sección 12).

---

## 7. Estructura del repo (estado real, paquete `app`)

```
/
├── frontend/                 # Workspace Next.js 15 (B0 bootstrap; UIs B8/B10/B11/B12)
│   ├── src/app/(consulta)/   # UI #1 PWA (B8)
│   ├── src/app/(revision)/   # UI #2 Revisión Lingüística (B10)
│   ├── src/app/(pm)/         # UI #3 PM Dashboard (B11)
│   └── src/app/(onboarding)/ # UI #4 Onboarding Wizard (B12)
├── app/                      # Backend Python (paquete principal — NO "panohayan", NO "docyan")
│   ├── core/                 # dii.py (deprecated), edb.py, grg.py, mr.py, intent.py, matrix.py, ri.py
│   ├── graph/                # docyan_graph.py (fachada GraphRAG-SDK), schemas/, versioning, multitenancy (B1/B2)
│   ├── schemas_documentales/ # catalogo/ + generador.py + registry.py (B1)
│   ├── translation/          # motor, scoring, tm_dual, lock_terminologico, fuzzy_matching (B2/B4)
│   ├── orchestrator/         # master_orchestrator, session_manager, scheduler, governance_gate (B3)
│   ├── qr/                   # qr_generator, qr_resolver (B3)
│   ├── ingesta/              # cotizador.py (B3)
│   ├── ingesta_bilingue/     # parsers/, alineadores/, pipeline (B5)
│   ├── governance/           # grg_extendido (B6)
│   ├── audit/                # fat_extendido + hash chain, integrity_checker, reports (B6)
│   ├── intent/               # clasificador, pipelines/, chat_persistente (B7)
│   ├── alerts/               # safety_validator (B8 — línea ABSOLUTA)
│   ├── channels/             # whatsapp_360dialog, channel_adapter (B9)
│   ├── llm/                  # litellm_config (B1)
│   ├── embeddings/           # bge_client.py (existente)
│   ├── cache/                # redis_client.py (existente, evoluciona en B3)
│   ├── connectors/           # 37 conectores (existentes — no foco MVP)
│   └── api/                  # FastAPI routers
├── scripts/                  # Utilidades operativas (rename, backup FalkorDB, etc.)
├── docs/                     # Plan v2, sprints/, adenda post-PoC, arquitectura/ (00-14), runbooks
├── migrations/               # SQL migrations (8 tablas + hash chain)
├── tests/                    # Tests backend (pytest)
├── .github/workflows/        # GitHub Actions CI
├── Dockerfile                # Backend container
├── fly.toml                  # Fly.io config (app docyan-lde-api)
├── vercel.json               # Vercel config (frontend)
├── pyproject.toml            # Deps Python
└── CLAUDE.md                 # Este archivo
```

---

## 8. Convenciones de código

### Python
- Type hints obligatorios en funciones públicas.
- Pydantic v2 para schemas de API.
- `async`/`await` por default en handlers FastAPI. **Cuidado con funciones async sin await** (el PoC dejó `finalize()` y `deduplicate_entities()` async sin await — corregir al integrar).
- Docstrings en español o inglés (consistente por módulo).
- `ruff` + `black` configurados; formatear antes de commit.
- Variables de entorno via `pydantic-settings`.

### TypeScript
- `strict: true` en tsconfig.
- Tipos generados desde OpenAPI, no hardcoded.
- Componentes React con tipos de props explícitos.
- `eslint` + `prettier` configurados.
- Estado global: Zustand o Jotai cuando aplique (no Redux).

### Commits
- Conventional commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`.
- Referenciar bloque cuando aplique: `feat(B2): add DTM segment versioning`.

### Branches
- `main`: producción.
- `develop` o feature branches por sprint: `sprint/B2-dtm`.

---

## 9. Variables de entorno principales

Documentadas en `.env.example`. Las críticas:

```
# Auth
JWT_SECRET=<random 64+ chars — NO defaults inseguros>
SUPABASE_URL=
SUPABASE_KEY=
SUPABASE_SERVICE_KEY=

# Databases
FALKORDB_HOST=
FALKORDB_PORT=
FALKORDB_GRAPH=docyan
REDIS_URL=

# LLMs de traducción (vía Model Router)
ANTHROPIC_API_KEY=

# LLMs de ingesta (GraphRAG-SDK vía LiteLLM)
GEMINI_API_KEY=        # NO GOOGLE_API_KEY
OPENAI_API_KEY=        # gpt-4o-mini para QA

# Embeddings (BGE-M3 self-hosted)
BGE_M3_URL=

# WhatsApp
WA_360DIALOG_API_KEY=
WA_360DIALOG_WEBHOOK_SECRET=

# Sentry (B13)
SENTRY_DSN=

# CORS (por dominio, NO wildcard en producción)
ALLOWED_ORIGINS=https://consulta.docyan.com,https://reviewer.docyan.com,...
```

**NO commitear secrets.** `gitleaks` corre en CI. La auditoría abril detectó `JWT_SECRET` default inseguro y dev API key hardcodeada — NO se repiten.

---

## 10. Política de auditoría / FAT

Cada acción significativa dispara un evento FAT (Foundation Audit Trail) con SHA-256 hash chain (construido en B6 — el `matrix.py` actual NO tiene hash chain todavía).

9 familias de eventos (definidas en B6):
- `consulta` — consultas operativas.
- `revision` — acciones del revisor lingüístico.
- `ingesta` — carga de documentos / pares Pista B.
- `governance` — cambios de configuración GRG, lock, etc.
- `troubleshooting` — sesiones Tipo 5.
- `alertas` — disparos de Tipo 7 (solo administrativas — ver sección 11.1).
- `onboarding` — flujo de UI #4.
- `system` — operaciones internas (webhook failures, scheduler runs).
- `auth` — login, logout, password reset.

**No agregues eventos fuera de estas familias sin justificación documentada.**

Retención (Decisión #12):
- 7 años: producción, revisión, ingesta, governance.
- 5 años: onboarding.
- 3 años: consulta, troubleshooting, alertas.
- 2 años: system.

---

## 11. Marco regulatorio que el producto satisface

NOM-018-STPS-2015, NOM-026-STPS-2008, LFT Art. 132, NOM-035-STPS-2018, IATF 16949, AS9100, ISO 17025, FDA, EU Organic.

**No es requisito que conozcas estas normas al detalle**, pero sí que entiendas que el producto **opera en industrias reguladas** y por eso:

- Compliance ≠ nice-to-have. La cadena hash de FAT es regulatoria, no opcional.
- Lock terminológico ≠ feature cosmética. Es diferenciador defendible vs CAT tools.
- Multi-tenant strict ≠ paranoia. Es contractual con clientes regulados.

### 11.1. Línea de seguridad regulatoria — ABSOLUTA

Las alertas del sistema deben ser **SOLO administrativas** (vencimientos, faltantes, fechas de calibración, documentos por expirar), **NUNCA decisiones clínicas u operativas** que sugieran qué hacer. Una alerta que sugiera decisión clínica entra en software como dispositivo médico (SaMD), regulación COFEPRIS/FDA, responsabilidad por mala praxis. **Esta línea no se cruza.** DOCYAN es capa de conocimiento, no sistema de registro primario de datos médicos. En B8 se codifica como `safety_validator` que rechaza cualquier alerta con sugerencia clínica/operativa — es requisito legal con cobertura de tests crítica, no opcional.

---

## 12. Contexto comercial — REGLA OPERATIVA INVIOLABLE

**SIN MENSAJES A CONTACTOS COMERCIALES HASTA QUE EL PRODUCTO SEA DEMO-ABLE.**

Vender un producto que no existe quema relaciones reales. No generes contenido tipo "email de pitch", "propuesta comercial", "mensaje de outreach" para contactos reales hasta que Jorge lo solicite explícitamente con producto en mano.

Contactos referidos en project knowledge (NO acción):
- México: Laboratorio Estándar, Daniel Calderón (Intermex Juárez), Elías Chacón (T-Hub), Sergio León.
- Internacional: Hafida Santoudy (NY), Sonia (Octagon Madrid, contacto Magna International).

Nota sobre pilotos: si se considera una clínica como piloto, NO como primer piloto por riesgo regulatorio de datos médicos (NOM-024-SSA3, posible HIPAA); empezar por documentación administrativa/de procesos, no expedientes de pacientes.

---

## 13. Cuando algo se rompa

1. **Diagnóstico real**: lee logs, ejecuta tests, inspecciona estado real. **NO supongas.**
2. **Verdad operacional**: si está roto, di que está roto. No "debería funcionar después de reiniciar".
3. **Documenta en el reporte**: bloqueador específico, intento de solución, qué se necesita para resolver.
4. **NO bloquees todo el sprint por un componente**: continúa con lo demás que sí puedes ejecutar.
5. **Si requiere decisión de Jorge**: marca `PENDIENTE DE JORGE` con detalle técnico suficiente para que decida sin tener que investigar.

---

## 14. Identidad del proyecto

- **Empresa**: XCID SA de CV
- **Producto**: DOCYAN LDE™ (Live Document Environment) — antes Panohayan DLE™
- **Fundador**: Jorge Luis Amparán Hernández (25 años en corredor industrial T-MEC + industria traducción profesional internacional)
- **Su corrección sobre flujos operativos es ley operativa, no opinable.**

Si Jorge contradice algo en este CLAUDE.md, **gana Jorge**. Este archivo es una guía, no un dogma.

---

## 15. Fuentes de verdad

Por orden de prioridad cuando algo entra en conflicto:

1. **Mensaje directo de Jorge en la sesión actual.**
2. **Sprint Contract activo** (lo que Jorge pega al inicio de la sesión).
3. **Adenda post-PoC** (`docs/adenda_postPoC_28mayo2026.md`) + **Plan v2** (`docs/Plan_Desarrollo_MVP_DOCYAN_v2_postPoC.md`).
4. **Docs 00-14 del modelado arquitectónico** (`docs/arquitectura/`, pegados cuando aplica).
5. **Este CLAUDE.md.**
6. **Estado actual del código en main.**

Cuando hay conflicto entre modelado y código existente: seguir el modelado. El código existente del repo previo (`delfa-bridge-core` migrado) tiene deuda técnica que se está limpiando bloque por bloque. Cuando hay conflicto entre una decisión del Paso C y la adenda post-PoC: **gana la adenda** (está basada en PoC ejecutado), salvo marca de PENDIENTE DE JORGE.

---

*XCID SA de CV — DOCYAN LDE™ by XCID — Actualizado 28 mayo 2026 — Confidencial.*
