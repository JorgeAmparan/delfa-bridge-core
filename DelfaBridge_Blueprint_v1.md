# DelfaBridge_Blueprint_v1.md
> Fuente de verdad arquitectónica de Delfa Bridge.
> Versión: 1.0 | Fecha: Marzo 2026 | Autor: Jorge Luis Amparán Hernández

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

---

## 2. ARQUITECTURA PANOHAYAN™

### 2.1 Los 4 Pilares

```
┌─────────────────────────────────────────────────────────┐
│                    PANOHAYAN™                           │
│                                                         │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────┐  │
│  │   DII   │───▶│  EDB    │───▶│   GRG   │───▶│ TM  │  │
│  │         │    │  Lite   │    │         │    │     │  │
│  └─────────┘    └─────────┘    └─────────┘    └─────┘  │
│  Extracción     Persistencia   Gobernanza    Trazab.    │
└─────────────────────────────────────────────────────────┘
```

### 2.2 DII — Digest Input Intelligence

El componente de ingesta. Transforma cualquier documento en entidades estructuradas.

**Pipeline completo:**
```
Documento entrada (PDF, DOCX, XLSX, CSV, HTML, imágenes)
        ↓
[DOCLING] — Conversión universal
  • PDF nativo → Markdown estructurado
  • PDF escaneado → OCR → Markdown
  • XLSX/CSV → tablas estructuradas
  • DOCX/PPTX → texto + estructura
  • Preserva jerarquía, tablas, layouts
        ↓
[CLASIFICADOR DE CONTENIDO]
  • ¿Tiene tablas? → rama LlamaIndex
  • ¿Texto narrativo? → rama LangExtract
  • ¿Ambos? → ambas ramas en paralelo
        ↓              ↓
  [LlamaIndex]    [LangExtract]
  Indexación      Extracción
  tabular         semántica de
  estructurada    entidades
        ↓              ↓
        └──── [MERGE + IHS] ────┘
  • Unificación de entidades
  • Deduplicación por hash SHA256
  • Normalización de valores
        ↓
[MODEL ROUTER] — Selección inteligente de LLM
  Tier 1: Gemini 2.0 Flash    → doc simple < 5 páginas
  Tier 2: Gemini 2.5 Flash    → tablas o > 5 páginas
  Tier 3: Claude Sonnet/GPT-4o-mini → legal/fiscal denso
  Tier 4: Claude Opus/GPT-4o  → razonamiento profundo
        ↓
[LLM SELECCIONADO]
  • Normalización semántica
  • Inferencia de relaciones
  • Enriquecimiento de entidades
        ↓
[EDB LITE] + [TM]
  Persistencia + Audit trail
```

**Criterios Model Router:**
```python
def seleccionar_modelo(chars: int, tiene_tablas: bool, source_type: str) -> str:
    if source_type in ["pdf"] and chars > 50000:
        return "claude-sonnet-4-6"  # Tier 3
    if tiene_tablas and chars > 20000:
        return "gemini-2.5-flash"   # Tier 2
    if chars > 100000:
        return "claude-opus-4-6"    # Tier 4
    return "gemini-2.0-flash"       # Tier 1 default
```

### 2.3 EDB Lite — Entity Data Brain Lite

Capa de persistencia inteligente. Memoria híbrida: relacional + vectorial.

**Diferencia EDB vs EDB Lite:**
- EDB (XCID): FalkorDB + XKGs + razonamiento graph-based
- EDB Lite (Delfa Bridge): Supabase + pgvector — suficiente para PYMEs y middleware

**Funciones principales:**
- `store_entity(entity)` — persiste entidad con embedding vectorial
- `search_semantic(query, org_id)` — búsqueda por similitud coseno
- `get_by_class(entity_class, org_id)` — recuperación por tipo
- `get_document_entities(document_id)` — todas las entidades de un documento

### 2.4 GRG — Governance Guardrails

Capa de gobernanza configurable por organización. Garantiza cero alucinación.

**Flujo GRG:**
```
Entidad extraída por DII
        ↓
¿Existe regla activa para esta entity_class en esta org?
        ↓              ↓
       Sí              No
        ↓              ↓
¿Cumple condición?   → Aprobada → EDB Lite
        ↓
  Tipo de acción:
  • block → rechaza entidad
  • flag → marca para revisión
  • require_approval → cuarentena hasta aprobación humana
  • redact → guarda pero oculta el valor
        ↓
  → quarantine table + TM log
```

**Casos de uso GRG:**
- Montos > $500K requieren aprobación humana
- Datos de personas físicas se redactan automáticamente
- Cláusulas específicas se marcan para revisión legal
- Entidades de baja confianza van a cuarentena

### 2.5 TM — Traceability Matrix

Columna vertebral de trazabilidad. Registra absolutamente todo.

**Cada registro incluye:**
- Componente que ejecutó la acción (DII, EDB, GRG, API)
- Acción ejecutada (extracted, stored, flagged, queried, etc.)
- Estado antes y después (before_value, after_value)
- Timestamp exacto
- Actor (system, user, api-key)

**Capacidad de reconstrucción:** dado cualquier `entity_id` o `document_id`,
TM puede reconstruir el estado completo en cualquier momento histórico.

---

## 3. BASE DE DATOS

### 3.1 Esquema Supabase

**Tabla: documents**
```sql
id              UUID PK
org_id          TEXT NOT NULL
name            TEXT NOT NULL
source_type     TEXT          -- pdf, docx, xlsx, erp, api
source_path     TEXT
status          TEXT          -- pending, processing, processed, failed
doc_hash        TEXT          -- SHA256 del documento completo (IHS)
processed_at    TIMESTAMP
created_at      TIMESTAMP DEFAULT NOW()
metadata        JSONB
```

**Tabla: entities (EDB Lite)**
```sql
id              UUID PK
document_id     UUID FK → documents
org_id          TEXT NOT NULL
entity_class    TEXT          -- tipo de entidad (agnóstico)
entity_value    TEXT          -- valor raw extraído
normalized_value TEXT         -- valor normalizado
hash            TEXT          -- SHA256(entity_class:normalized_value)
confidence      FLOAT         -- nivel de confianza
embedding       VECTOR(1536)  -- para búsqueda semántica
status          TEXT          -- active, quarantined, superseded
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

**Tabla: governance_rules (GRG)**
```sql
id              UUID PK
org_id          TEXT NOT NULL
entity_class    TEXT
rule_type       TEXT          -- block, flag, require_approval, redact
condition       JSONB
action          TEXT
is_active       BOOLEAN DEFAULT TRUE
created_at      TIMESTAMP
```

**Tabla: quarantine (GRG output)**
```sql
id              UUID PK
entity_id       UUID FK → entities
org_id          TEXT NOT NULL
rule_id         UUID FK → governance_rules
reason          TEXT
resolved        BOOLEAN DEFAULT FALSE
resolved_at     TIMESTAMP
created_at      TIMESTAMP
```

**Tabla: audit_trail (TM)**
```sql
id              UUID PK
org_id          TEXT NOT NULL
document_id     UUID FK → documents
entity_id       UUID FK → entities  -- nullable
component       TEXT          -- DII, EDB, GRG, TM, API, MR
action          TEXT          -- extracted, stored, flagged, queried...
actor           TEXT DEFAULT 'system'
before_value    JSONB
after_value     JSONB
detail          JSONB
created_at      TIMESTAMP
```

### 3.2 Índices
```sql
CREATE INDEX ON entities USING ivfflat (embedding vector_cosine_ops) WITH (lists=100);
CREATE INDEX ON documents (org_id);
CREATE INDEX ON entities (org_id, document_id, hash);
CREATE INDEX ON audit_trail (org_id, document_id, entity_id);
CREATE INDEX ON quarantine (org_id);
CREATE INDEX ON governance_rules (org_id);
```

---

## 4. STACK TECNOLÓGICO

| Capa | Tecnología | Propósito |
|------|-----------|-----------|
| Conversión | Docling 2.x | PDF, DOCX, XLSX, OCR → Markdown |
| Indexación tabular | LlamaIndex | Tablas y datos estructurados |
| Extracción semántica | LangExtract + Gemini | Entidades de texto narrativo |
| Model Router | Custom Python | Selección LLM costo-eficiente |
| LLMs disponibles | Gemini Flash/Pro, Claude Sonnet/Opus, GPT-4o/mini | Normalización y enriquecimiento |
| Persistencia | Supabase (PostgreSQL + pgvector) | EDB Lite + vectores |
| API | FastAPI | REST endpoints |
| Contenedores | Docker + docker-compose | Microservicios |
| Despliegue | Railway / Render | Cloud hosting |
| Pagos | Stripe | Suscripciones automatizadas |
| Frontend cliente | Lovable (Juan del Hoyo) | Interface y portal |

---

## 5. MODELO DE NEGOCIO

### 5.1 Tiers de Suscripción
```
Starter         $X USD/mes
  • 3 conectores activos
  • 10,000 entidades/mes
  • 1 organización
  • Soporte email

Professional    $X USD/mes
  • 8 conectores activos
  • 100,000 entidades/mes
  • 5 organizaciones
  • Soporte prioritario

Enterprise      Precio negociado
  • Conectores ilimitados
  • Entidades ilimitadas
  • Organizaciones ilimitadas
  • SLA + soporte dedicado
```

### 5.2 Multitenancy
Cada cliente de Juan tiene su propio `org_id`. RLS en Supabase garantiza
aislamiento total de datos entre organizaciones.

---

## 6. MICROSERVICIOS (Fase 4)

```
delfa-dii      puerto 8001  — procesa documentos
delfa-edb      puerto 8002  — almacena y busca entidades
delfa-grg      puerto 8003  — gobernanza y reglas
delfa-matrix   puerto 8004  — trazabilidad
delfa-api      puerto 8000  — gateway principal REST
```

Cada microservicio expone un **MCP server** para conectividad con Claude y ecosistema MCP.

---

## 7. CONECTORES (Fase 3)

| Conector | Prioridad | Estado |
|----------|-----------|--------|
| PDF/DOCX/XLSX | Alta | En desarrollo |
| Google Drive | Alta | Pendiente |
| MicroSip ERP | Alta | Pendiente |
| SQL/PostgreSQL | Media | Pendiente |
| HubSpot CRM | Media | Pendiente |
| Slack/Teams | Baja | Pendiente |
| APIs REST | Media | Pendiente |

---

## 8. ROADMAP

```
Fase 1 — Core Panohayan        3-4 semanas
  DII completo (Docling+MR) + EDB + GRG + TM

Fase 2 — API REST              1-2 semanas
  FastAPI + autenticación + API keys por org

Fase 3 — Conectores            2-3 semanas
  Google Drive + MicroSip + SQL

Fase 4 — Dockerización + MCP   1 semana
  Microservicios + MCP servers

Fase 5 — Infraestructura       1 semana
  Railway/Render + dominio + SSL

Fase 6 — Comercial             2-3 semanas
  Landing + Stripe + docs para devs + guía no-devs
```

---

## 9. PROPIEDAD INTELECTUAL

- **Panohayan™** y todos sus componentes son PI de **Jorge Luis Amparán Hernández**
- **Delfa Bridge** opera bajo licencia exclusiva otorgada a **Juan del Hoyo** y sus socios
- La licencia es válida mientras se mantenga el pago de la iguala mensual acordada
- **XCID y XitleCore** son proyectos separados, no relacionados con Delfa Bridge
- Cualquier mejora a Panohayan™ desarrollada por Jorge sigue siendo PI de Jorge

---

## 10. ESTADO ACTUAL

| Componente | Estado | Notas |
|-----------|--------|-------|
| Supabase configurado | ✅ Completo | 5 tablas + índices + RLS |
| DII v1 | ✅ Funcional | LangExtract + Gemini |
| DII v2 | 🔄 En desarrollo | Docling + MR pendiente |
| EDB Lite | ⏳ Pendiente | Esquema listo en Supabase |
| GRG | ⏳ Pendiente | |
| TM | ⏳ Pendiente | |
| API REST | ⏳ Pendiente | |
| Conectores | ⏳ Pendiente | |
| Docker | ⏳ Pendiente | |
| Comercial | ⏳ Pendiente | |

---

*Delfa Bridge Blueprint v1.0 — Confidencial*
*Jorge Luis Amparán Hernández / Lappicero Studio — Marzo 2026*
