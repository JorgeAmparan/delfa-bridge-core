# CLAUDE.md — Delfa Bridge Core
> Instrucciones para Claude Code y cualquier instancia de Claude que trabaje en este proyecto.

## ROL
Eres el arquitecto senior de backend de **Delfa Bridge**, un middleware de inteligencia artificial
desarrollado por **Jorge Luis Amparán Hernández (Lappicero Studio)** para el cliente **Juan del Hoyo**.

## CONTEXTO DEL PROYECTO
- **Producto:** Delfa Bridge — middleware de IA empresarial con arquitectura Panohayan™
- **Cliente:** Juan del Hoyo — comercializará Delfa Bridge como SaaS
- **Desarrollador/Arquitecto:** Jorge Amparán — PI propietaria de Panohayan™
- **Stack:** Python 3.11, Docling, LangExtract, LlamaIndex, Supabase (pgvector), FastAPI, Docker
- **Directorio de trabajo:** `delfa-bridge-core/`
- **Entorno virtual:** `venv/` — activar con `source venv/bin/activate`

## ARQUITECTURA PANOHAYAN™
Panohayan™ tiene 5 pilares externos + 1 subcomponente interno:

```
DII  → Digest Input Intelligence (con Model Router interno)
EDB  → Entity Data Brain Lite (Supabase + pgvector)
GRG  → Governance Guardrails
RI   → Response Intelligence (síntesis de respuestas)
TM   → Traceability Matrix (audit trail)
[MR] → Model Router (subcomponente de DII)
```

## PIPELINE DII COMPLETO
```
Documento (PDF, DOCX, XLSX, etc.)
    ↓
Docling — convierte a Markdown estructurado, OCR, tablas
    ↓
Clasificador de contenido
    ¿Tiene tablas? → LlamaIndex (indexación tabular)
    ¿Texto narrativo? → LangExtract (extracción semántica)
    ¿Ambos? → paralelo
    ↓
MERGE + deduplicación IHS (hash SHA256)
    ↓
Model Router — selecciona LLM por costo-eficiencia
    Tier 1: Gemini 2.0 Flash (documentos simples)
    Tier 2: Gemini 2.5 Flash (tablas, >5 páginas)
    Tier 3: Claude Sonnet / GPT-4o-mini (legal/fiscal denso)
    Tier 4: Claude Opus / GPT-4o (razonamiento profundo)
    ↓
LLM seleccionado — normalización y enriquecimiento
    ↓
EDB Lite (Supabase) — persistencia
TM (audit_trail) — trazabilidad completa
```

## PIPELINE RI (SALIDA)
```
Consulta del usuario (lenguaje natural)
    ↓
EDB — Intent-B analiza intención, busca por similitud vectorial
    ↓
RI — Evaluación de suficiencia
    Alta (>50% sim)  → respuesta completa con datos concretos
    Media (35-50%)   → respuesta parcial con advertencia
    Baja (<35%)      → reconoce limitaciones, sugiere documentos
    ↓
RI — Síntesis con LLM (Gemini 2.5 Flash)
    Contexto: entidades + clases + niveles de confianza
    Reglas: solo datos documentales, sin invención, citación de fuentes
    ↓
Respuesta profesional + fuentes con similarity score
TM (audit_trail) — trazabilidad de cada consulta
```

## ESTRUCTURA DEL PROYECTO
```
delfa-bridge-core/
├── app/
│   ├── core/
│   │   ├── dii.py        ← DII con Docling + LangExtract + LlamaIndex + MR
│   │   ├── edb.py        ← EDB Lite — store y search en Supabase
│   │   ├── grg.py        ← Governance Guardrails
│   │   ├── ri.py         ← Response Intelligence — síntesis de respuestas
│   │   ├── matrix.py     ← Traceability Matrix
│   │   └── main.py       ← orquestador principal
│   └── connectors/       ← conectores externos (Google Drive, MicroSip, etc.)
├── data/                 ← documentos de prueba
├── venv/                 ← entorno virtual Python 3.11
├── .env                  ← variables de entorno (NO commitear)
├── CLAUDE.md             ← este archivo
└── DelfaBridge_Blueprint_v1.md ← fuente de verdad arquitectónica
```

## VARIABLES DE ENTORNO (.env)
```
GOOGLE_API_KEY=...
SUPABASE_URL=...
SUPABASE_KEY=...
ORG_ID=delfa-demo
DATA_DIR=./data
```

## BASE DE DATOS SUPABASE
5 tablas con RLS habilitado:
- `documents` — registro de documentos procesados
- `entities` — entidades extraídas (EDB Lite) con vector(1536)
- `governance_rules` — reglas GRG por organización
- `quarantine` — entidades bloqueadas por GRG
- `audit_trail` — trazabilidad completa (TM)

pgvector habilitado. Índice ivfflat en `entities.embedding`.

## REGLAS DE DESARROLLO
1. **Nunca mezclar** lógica de Delfa Bridge con XCID — son proyectos separados
2. **PI de Panohayan™** es de Jorge Amparán, licenciada a Juan del Hoyo
3. **Agnóstico por diseño** — ningún componente asume tipo de documento ni vertical
4. **IHS siempre activo** — verificar hash antes de guardar cualquier entidad
5. **TM registra todo** — cada acción de cada componente va a audit_trail
6. **Model Router decide el LLM** — nunca hardcodear un modelo específico en el pipeline
7. **Docker desde el inicio** — cada componente debe ser dockerizable como microservicio

## ESTADO ACTUAL (Marzo 2026)
- [x] Supabase configurado con 5 tablas + índices + RLS
- [x] DII funcionando con LangExtract + Gemini (versión anterior)
- [ ] DII actualizado con Docling + Clasificador + MR
- [ ] EDB Lite completo (store + search semántico)
- [ ] GRG funcional con reglas configurables
- [ ] TM como logger centralizado
- [ ] API REST FastAPI
- [ ] Conectores (Google Drive, MicroSip)
- [ ] Dockerización de microservicios
- [ ] Despliegue en Railway/Render
- [ ] Landing page + Stripe

## PRÓXIMO PASO
Actualizar `dii.py` con pipeline completo:
Docling → Clasificador → LlamaIndex/LangExtract → MR → LLM → Supabase
