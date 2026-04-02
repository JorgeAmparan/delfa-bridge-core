# DelfaBridge_Blueprint_v2.md
> Fuente de verdad arquitectónica de Delfa Bridge.
> Versión: 2.0 | Fecha: Abril 2026 | Autor: Jorge Luis Amparán Hernández

---

## 1. VISIÓN DEL PRODUCTO

**Delfa Bridge** es la primera capa de middleware de inteligencia artificial diseñada para cerrar
la brecha entre documentos empresariales caóticos y agentes de IA de grado profesional.

A través de la arquitectura **Panohayan™** (del Náhuatl: "Lugar por donde se pasa"), Delfa Bridge
transforma datos no estructurados — PDFs, Word, Excel, ERPs, APIs — en un Entity Data Brain
estructurado, auditable y listo para alimentar cualquier agente de IA.

**Propuesta de valor única:**
- **Cero alucinación** — GRG garantiza que ninguna respuesta sale sin fuente verificada
- **Trazabilidad total** — TM registra cada decisión hasta su origen documental
- **Soberanía de datos** — el conocimiento vive en la base de datos del cliente, no en el modelo
- **Agnóstico** — funciona con cualquier documento, cualquier LLM, cualquier vertical
- **Costo-eficiente** — Model Router selecciona el LLM más económico por tarea
- **Conectividad MCP** — se conecta directamente a Claude y ecosistema MCP

---

## 2. ARQUITECTURA PANOHAYAN™

### 2.1 Los 4 Pilares + MR

```
┌──────────────────────────────────────────────────────────────┐
│                      PANOHAYAN™                              │
│                                                              │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐  │
│  │   DII   │───▶│  EDB    │───▶│   GRG   │───▶│   TM    │  │
│  │  + MR   │    │  Lite   │    │         │    │         │  │
│  │ +Intent │    │+Intent-B│    │         │    │         │  │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘  │
│  Extracción     Persistencia   Gobernanza    Trazabilidad   │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 DII — Digest Input Intelligence

**Pipeline completo:**
```
Documento entrada (PDF, DOCX, XLSX, CSV, HTML, imágenes)
        ↓
[DOCLING] — Conversión universal + OCR
        ↓
[INTENT-A] — Análisis de tipo de documento
  • "contrato" → extrae partes, montos, fechas, cláusulas
  • "factura" → extrae proveedor, conceptos, totales, IVA
  • "reglamento" → extrae artículos, obligaciones, sanciones
  • Ajusta prompt de LangExtract dinámicamente
        ↓
[CLASIFICADOR DE CONTENIDO]
  • ¿Tiene tablas? → rama LlamaIndex
  • ¿Texto narrativo? → rama LangExtract
  • ¿Ambos? → ambas ramas en paralelo
        ↓              ↓
  [LlamaIndex]    [LangExtract]
  Indexación      Extracción
  tabular         semántica
        ↓              ↓
        └──── [IHS MERGE] ────┘
  • Deduplicación por hash SHA256
  • Normalización de valores
        ↓
[MODEL ROUTER] — Selección inteligente de LLM
  Tier 1: Gemini 2.5 Flash    (< 20K chars, sin tablas)
  Tier 2: Gemini 2.5 Flash    (tablas o > 20K chars)
  Tier 3: Claude Sonnet 4.6   (legal/fiscal > 50K chars)
  Tier 4: Claude Opus 4.6     (> 100K chars)
        ↓
[EDB LITE] + [TM]
  Persistencia + Audit trail + Embeddings automáticos
```

### 2.3 EDB Lite — Entity Data Brain Lite

Memoria híbrida: relacional + vectorial (pgvector).

**Funciones principales:**
- `store_entity()` — persiste entidad en Supabase
- `store_embedding()` — genera embedding OpenAI y actualiza entidad
- `store_document_embeddings()` — batch embeddings por documento
- `search_semantic(query)` — búsqueda semántica con Intent-B integrado
- `search_by_class(entity_class)` — recuperación por tipo exacto
- `search_by_document(document_id)` — entidades de un documento
- `get_summary()` — resumen del EDB para la organización

**Intent-B integrado en search_semantic:**
- Analiza intención del query antes de buscar
- Optimiza el query semántico para mejor precisión
- Filtra por entity_classes relevantes automáticamente

### 2.4 GRG — Governance Guardrails

Gobernanza configurable por organización.

**4 tipos de acción:**
- `block` — rechaza la entidad completamente
- `flag` — marca para revisión humana
- `require_approval` — manda a cuarentena hasta aprobación
- `redact` — guarda pero oculta el valor

**3 tipos de condición:**
- `min_value` — umbral numérico (ej: montos > $20,000)
- `contains` — texto específico en el valor
- `min_length` — longitud mínima del valor

### 2.5 TM — Traceability Matrix

Logger centralizado. Registra absolutamente todo.

**Consultas disponibles:**
- `get_document_trail(document_id)` — trail completo por documento
- `get_entity_trail(entity_id)` — trail de una entidad específica
- `get_recent_activity(limit)` — actividad reciente
- `get_component_summary()` — resumen por componente
- `reconstruir_estado_entidad(entity_id)` — historial completo

### 2.6 MR — Model Router

Módulo independiente `app/core/mr.py`.

```python
# Criterios de selección
chars > 100000        → Tier 4: Claude Opus 4.6
chars > 50000 + pdf   → Tier 3: Claude Sonnet 4.6
tiene_tablas          → Tier 2: Gemini 2.5 Flash
default               → Tier 1: Gemini 2.5 Flash
```

**Override manual:** `MR_OVERRIDE_MODEL=modelo` en `.env`

### 2.7 Intent Analyzer

Módulo independiente `app/core/intent.py`.

**DocumentIntentAnalyzer (Intent-A):**
- Detecta tipo de documento con Gemini 2.5 Flash
- Tipos: contrato, factura, reglamento, estado_de_cuenta, propuesta, general
- Ajusta prompt de LangExtract dinámicamente
- Persiste tipo detectado en metadata del documento

**QueryIntentAnalyzer (Intent-B):**
- Analiza intención del query del usuario
- Optimiza query semántico para búsqueda vectorial
- Identifica entity_classes relevantes para filtrar
- Integrado en EDB `search_semantic()`

---

## 3. BASE DE DATOS SUPABASE

### 3.1 Tablas

**documents** — registro de documentos
```
id, org_id, name, source_type, source_path, status,
doc_hash, processed_at, created_at, metadata(jsonb)
metadata incluye: model_router, document_type
```

**entities (EDB Lite)** — entidades extraídas
```
id, document_id, org_id, entity_class, entity_value,
normalized_value, hash, confidence, embedding(vector 1536),
status, created_at, updated_at
```

**governance_rules (GRG)** — reglas configurables
```
id, org_id, entity_class, rule_type, condition(jsonb),
action, is_active, created_at
```

**quarantine (GRG output)** — entidades bloqueadas
```
id, entity_id, org_id, rule_id, reason,
resolved, resolved_at, created_at
```

**audit_trail (TM)** — trazabilidad completa
```
id, org_id, document_id, entity_id, component,
action, actor, before_value(jsonb), after_value(jsonb),
detail(jsonb), created_at
```

### 3.2 Función RPC
```sql
match_entities(query_embedding, match_threshold, match_count, p_org_id)
-- Búsqueda por similitud coseno en pgvector
```

---

## 4. STACK TECNOLÓGICO

| Capa | Tecnología | Versión |
|------|-----------|---------|
| Conversión | Docling | 2.84.0 |
| Extracción semántica | LangExtract + Gemini | 1.2.0 |
| Indexación tabular | LlamaIndex | 0.14.x |
| Análisis de intención | Google Gemini | 2.5 Flash |
| Embeddings | OpenAI | text-embedding-3-small |
| LLMs Tier 1-2 | Google Gemini | 2.5 Flash |
| LLMs Tier 3 | Anthropic Claude | Sonnet 4.6 |
| LLMs Tier 4 | Anthropic Claude | Opus 4.6 |
| Persistencia | Supabase + pgvector | PostgreSQL 15 |
| API | FastAPI + Uvicorn | latest |
| Contenedores | Docker + docker-compose | 29.x |
| MCP | mcp SDK | latest |
| Despliegue | Railway / AWS ECS | — |

---

## 5. API REST

**Base URL:** `http://localhost:8000` (dev) / `https://api.delfa.bridge` (prod)

**Autenticación:** Header `X-API-Key: {api_key}`

### Endpoints

```
GET  /                          — info del producto
GET  /health                    — health check

POST /documents/process         — procesar documento
GET  /documents/                — listar documentos
GET  /documents/{id}            — detalle + entidades

POST /search/                   — búsqueda semántica

POST /governance/rules          — crear regla GRG
GET  /governance/rules          — listar reglas activas

GET  /trail/document/{id}       — audit trail por documento
GET  /trail/recent              — actividad reciente
GET  /trail/summary             — resumen por componente
```

**Docs interactivas:** `/docs` (Swagger) | `/redoc` (ReDoc)

---

## 6. MCP SERVER

**Archivo:** `app/mcp_server.py`
**Configuración:** `mcp_config.json`
**Protocolo:** stdio

### 4 Herramientas MCP

| Tool | Descripción |
|------|-------------|
| `search_knowledge` | Búsqueda semántica con Intent-B |
| `get_document_trail` | Audit trail completo de un documento |
| `list_documents` | Lista documentos procesados |
| `get_knowledge_summary` | Resumen del EDB Lite |

**Para conectar a Claude Desktop:** copiar `mcp_config.json` a la configuración de Claude.

---

## 7. ESTRUCTURA DEL PROYECTO

```
delfa-bridge-core/
├── app/
│   ├── __init__.py
│   ├── main.py               ← Orquestador CLI completo
│   ├── mcp_server.py         ← MCP Server Panohayan™
│   ├── core/
│   │   ├── __init__.py
│   │   ├── dii.py            ← DII + Docling + Intent-A + LangExtract
│   │   ├── edb.py            ← EDB Lite + Intent-B + search semántico
│   │   ├── grg.py            ← Governance Guardrails
│   │   ├── matrix.py         ← Traceability Matrix
│   │   ├── mr.py             ← Model Router independiente
│   │   └── intent.py         ← Intent-A + Intent-B
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py           ← FastAPI gateway
│   │   ├── auth.py           ← API Key authentication
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── documents.py  ← /documents endpoints
│   │       ├── search.py     ← /search endpoints
│   │       ├── governance.py ← /governance endpoints
│   │       └── trail.py      ← /trail endpoints
│   └── connectors/           ← conectores externos (próxima fase)
├── data/                     ← documentos (gitignored)
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── mcp_config.json
├── CLAUDE.md
├── DelfaBridge_Blueprint_v2.md
├── .env.example
├── requirements.txt
└── README.md
```

---

## 8. COMANDOS PRINCIPALES

```bash
# Activar entorno
source venv/bin/activate

# Pipeline completo
python3 -m app.main

# Búsqueda semántica CLI
python3 -m app.main buscar "quién firma el contrato"

# API REST
python3 -m uvicorn app.api.main:app --reload --port 8000

# MCP Server
python3 -m app.mcp_server

# Docker build
docker build -t delfa-bridge .

# Docker run
docker run -p 8020:8000 --env-file .env delfa-bridge

# Docker compose
docker compose up -d
```

---

## 9. MODELO DE NEGOCIO

| Tier | Segmento | Precio | Límites |
|------|---------|--------|---------|
| Starter | PYME, consultor | $X/mes | 3 conectores, 10K entidades/mes |
| Professional | Empresa mediana | $X/mes | 8 conectores, 100K entidades/mes |
| Enterprise | Corporativo | Negociado | Ilimitado + SLA |

**Multitenancy:** org_id + RLS en Supabase — aislamiento total entre clientes.

---

## 10. ROADMAP

```
✅ Fase 1 — Core Panohayan
   DII + EDB Lite + GRG + TM + MR + Intent-A + Intent-B

✅ Fase 2 — API REST
   FastAPI + autenticación + 4 routers

✅ Fase 3 — Docker
   Dockerfile + docker-compose + .dockerignore

✅ Fase 4 — MCP Server
   4 herramientas + configuración Claude Desktop

⏳ Fase 5 — Conectores
   Google Drive, MicroSip ERP, SQL

⏳ Fase 6 — Infraestructura
   Railway deploy + dominio + SSL

⏳ Fase 7 — Comercial
   Landing + Stripe + docs + guía implementación
```

---

## 11. PROPIEDAD INTELECTUAL

- **Panohayan™** y todos sus componentes son PI de **Jorge Luis Amparán Hernández**
- **Delfa Bridge** opera bajo licencia exclusiva otorgada a **Juan del Hoyo** y sus socios
- La licencia es válida mientras se mantenga el pago de la iguala mensual acordada
- **XCID y XitleCore** son proyectos completamente separados, no relacionados con Delfa Bridge
- Cualquier mejora a Panohayan™ desarrollada por Jorge sigue siendo PI de Jorge

---

*DelfaBridge Blueprint v2.0 — Confidencial*
*Jorge Luis Amparán Hernández / Lappicero Studio — Abril 2026*
