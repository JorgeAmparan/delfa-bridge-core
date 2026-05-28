# Plan de desarrollo del MVP de DOCYAN — v2 post-PoC

**Fecha:** 28 mayo 2026
**Autor:** Claude (socio estratégico) bajo dirección de Jorge Luis Amparán Hernández
**Estado:** Para aprobación del fundador antes de ejecución de Sprint Contracts
**Base inmutable:** 15 decisiones del Paso C + Adenda post-PoC (28 mayo 2026, CLAUDE_8.md) + 6 reportes del PoC GraphRAG-SDK + Auditoría del repo (28 mayo 2026) + los 15 documentos arquitectónicos (00-14)

**Principio rector de esta fase:** alcance completo. No se simplifica, no se difiere, no se construyen stubs ni mocks fuera de tests, no se reduce alcance. Donde hay tensión técnica real se discute con argumento; la resolución nunca es aplazar. Lo que el modelado describe se construye real.

---

## Decisiones confirmadas por Jorge (28 mayo 2026)

1. **Repo GitHub:** `panohayan-dle-core` → `docyan-lde-core`. ✅
2. **App Fly.io:** `panohayan-dle-api` → `docyan-lde-api`. ✅
3. **Grafo FalkorDB default:** `panohayan` → `docyan`. ✅
4. **Siglas:** PKG→DKG (Document Knowledge Graph), PTM→DTM (Document Translation Memory). Rename completo en código y docs. ✅
5. **Embedder:** **BGE-M3 self-hosted firme** (decisión #1 del Paso C). El PoC usó text-embedding-3-small solo por conveniencia de prueba (nunca comparó calidad). BGE-M3 es superior para el caso multilingüe de DOCYAN (Magna 12-20 idiomas), garantiza soberanía de datos para industria regulada, costo cero recurrente, y control de versionado para FAT a 7 años. B1 valida la integración con GraphRAG-SDK como embedder custom; si la vía directa falla, se construye adapter — el modelo NO cambia. ✅
6. **Rebrand a DOCYAN:** completo. Producto pasa a **DOCYAN LDE — Live Document Environment by XCID**. ✅

No quedan decisiones pendientes de fondo. Todo lo demás está cerrado en Paso C, adenda, o los DAs.

---

## Sección 1 — Decisiones técnicas vigentes (reconciliación completa)

### Las 15 decisiones del Paso C con su estado tras la adenda

| # | Decisión | Estado final vigente |
|---|----------|---------------------|
| 1 | Embeddings | **BGE-M3 self-hosted desde día 1.** Embedder custom de GraphRAG-SDK (vía ABC o LiteLLM; B1 valida, fallback adapter). El PoC usó text-embedding-3-small por conveniencia, no invalida la decisión. |
| 2 | Matching fuzzy | **Híbrido Levenshtein + BGE-M3 dos pasadas.** Score 70/30 bandas altas, 30/70 bandas bajas. Umbral mínimo léxico ≥30% para invocar vectorial. Umbral mínimo fuzzy 50%. |
| 3 | Scheduler | **APScheduler con backend Redis.** Subcomponente del MO. |
| 4 | Alineador bilingüe Pista B | **Vecalign primario + Hunalign fallback.** Ambos día 1. Pares con score <0.7 flagueados para revisión manual en UI #3. |
| 5 | i18n del UI | **react-i18next.** |
| 6 | Sesiones MO | **Redis con TTL diferenciado + spillover Supabase para completadas.** TTLs exactos: consulta operativa 30min sliding, troubleshooting 2h sliding, revisión 8h sliding, onboarding 30 días sliding. |
| 7a | Hosting backend | **Fly.io.** App `docyan-lde-api`, region `mia`. |
| 7b | Hosting frontend | **Vercel.** |
| 8 | WhatsApp BSP | **360dialog único, acceso directo API sin markup.** |
| 9 | Framework frontend | **Next.js 15 App Router + React 19 + Tailwind.** |
| 10 | Componentes UI | **shadcn/ui sobre Radix Primitives.** |
| 11 | Versionado DKG | **In-place + aristas `:VERSION_HISTORICA` / `:VersionAnterior`.** Default on para documentos/procedimientos/glosarios/entidades operativas; default off para términos individuales. |
| 12 | Respaldo FalkorDB | **RPO 15min + RTO 4h + retención 7 años producción / 3 años operativo.** |
| 13 | Pricing operativo | **Mantener precios project instructions hasta primer cliente real.** Pista A MXN (setup $15-25k + susc. $5-12k/mes + doc $300-800). Pista B USD (agencia $500-2k/mes + tier cliente final Base $2-5k / Profesional $8-15k / Enterprise $20-50k). |
| 14 | Testing | **Balanceado 60-70% backend / 40-50% frontend, CI/CD GitHub Actions.** Sin tests = sprint no terminado. |
| 15 | Criticidad por segmento | **Obligatoria en Onboarding Paso 9, delegable a inferencia automática del pipeline de ingesta.** |

### Cambios introducidos por la adenda post-PoC (con evidencia de los 6 reportes)

| Tema | Antes (Paso C / DAs) | Después (Adenda + PoC) |
|------|----------------------|------------------------|
| Arquitectura de ingesta | DII propio (352 LOC reales en repo; el doc 10 declaraba 1,759 incluyendo comentarios) | **GraphRAG-SDK 1.1.1 reemplaza DII.** El DII causó el incidente de $5,000 con Gemini (timeout 600s, escritura parcial, sin control de costo). PoC confirmó: ingesta <5min, escritura transaccional, provenance nativo, multi-tenancy por `graph_name`, `apply_changes()` crash-safe con SHA-256, estrategias swappables, LLM-agnóstico vía LiteLLM. |
| Modelo extracción (ingesta) | Sin config explícita | **Gemini 2.5 Flash** (`gemini/gemini-2.5-flash` vía LiteLLM — prefijo `gemini/` OBLIGATORIO o LiteLLM defaultea a Vertex AI). Evidencia Contrato 4: 15 obligaciones vs 4 de gpt-4o, 13 DEBE_CUMPLIR vs 4, cadenas regulatorias completas, a costo de mini ($0.036/doc). Gana 9 de 11 criterios. |
| Modelo QA (ingesta) | Sin config explícita | **gpt-4o-mini** (~$0.002/consulta). NO es dependencia fantasma: es el QA del pipeline, validado en PoC. |
| Resolution (ingesta) | Sin config explícita | **Gemini 2.5 Flash (LLMVerifiedResolution).** |
| Post-proceso dedup | No previsto | **`deduplicate_entities(fuzzy=True)` post-ingesta OBLIGATORIO.** El Contrato 5 dejó 653 residuos sin dedup por no ejecutarlo (era async sin await + rate limit). No es opcional. |
| Multi-tenancy en grafo | Conceptual en DKG | **Nativa por `graph_name`.** Sirve Agencia↔Cliente Final (Pista B) y aislamiento de tenants. |
| Provenance / pedigree | Por construir (doc 01) | **Nativo: edges `MENTIONED_IN`, `PART_OF`, `NEXT_CHUNK`, chunks con spans de caracteres.** Confirmado en PoC v1.1.1 (320→1,577 MENTIONED_IN según corpus). Base del pedigree clickeable. |
| LLMs de traducción (Pista A) | Claude Sonnet 4.6 + Gemini 2.5 Pro vía MR | **Sin cambio.** El cambio de modelos aplica SOLO al pipeline de ingesta, NO a la traducción. |
| Cotizador pre-ingesta | No previsto | **CRÍTICO. tiktoken antes de ingerir + verificación de presupuesto + confirmación.** El PoC topó hard cap de Google a MXN 119 en incidente controlado. Baselines reales: NOM 32pp $0.036, Ley 61pp $0.046, corpus 50 normas+10 leyes ~$2.26. Distinto del cotizador pre-venta de traducción (B11, ver más abajo). |
| Sistema de esquemas | No previsto | **Componente central nuevo. Catálogo del mercado meta + generador dinámico por Gemini 2.5 Flash.** Evidencia Contrato 5: schema de NOM-052 extrajo 0 relaciones de LGPGIR. El schema debe corresponder al TIPO de documento + contexto del usuario. (Detalle Sección 3.) |
| Alertas administrativas | No previsto | **Componente nuevo. SOLO administrativas (vencimientos, faltantes, fechas). NUNCA clínicas/operativas — línea ABSOLUTA (SaMD/COFEPRIS/FDA).** |
| Chat persistente en contexto | No previsto | **Componente nuevo. GraphRAG-SDK soporta multi-turno nativo (`completion()` con `history`).** |
| Anotaciones vinculadas | No previsto | **Componente nuevo. Capa complementaria, NO sistema de registro primario.** |
| Visualizaciones por tipo documental | Parcial (componentes por tipo de intención, doc 04) | **Ampliado: visualización por TIPO DE DOCUMENTO (NOM, MSDS, calibración...) además de por tipo de intención.** Conecta con el sistema de esquemas. |
| Nombre del producto | Panohayan DLE | **DOCYAN LDE — Live Document Environment by XCID.** Rename completo. |
| Siglas | PKG, PTM | **DKG, DTM.** |

### Dos bugs del PoC a corregir en construcción

1. **`finalize()` y `deduplicate_entities()` async sin `await`** (Contrato 5). El SDK tiene `finalize_sync()` pero **NO** `deduplicate_entities_sync()`. Se maneja el async correctamente en B1. Test de regresión.
2. **Rate limiting severo de Gemini Flash:** 1,506 retries en multi-doc, TPM 30K en tier actual. Se contempla en el diseño del cotizador (tiempo, no solo costo) y en el manejo de ingesta (retry con tenacity, ya en deps).

### Limitaciones de Gemini Flash a mitigar (no a aceptar como están)

- Tiempo de ingesta 642s (2.7x gpt-4o) — aceptable para one-time, se monitorea.
- Residuos sin dedup (653) — `deduplicate_entities(fuzzy=True)` obligatorio resuelve.
- Idioma mixto en descripciones (alterna ES/EN) — se fuerza idioma en el prompt de extracción.
- 1 chunk con JSON inválido de 104 — recuperación automática del SDK, se monitorea.

---

## Sección 2 — Plan de bloques actualizado (con detalle real de los DAs)

**Convención de estado:** Sin cambio / Alcance reducido (SDK absorbe) / Alcance ampliado (adenda agrega) / Alcance reformulado (nueva arquitectura).

Los Sprint Contracts derivan de esta sección con el detalle completo. Aquí el resumen por bloque; el detalle vive en cada Sprint Contract.

---

### B0 — Fundación, migración y rebrand
**Estado:** Alcance ampliado.
**Prerequisitos:** ninguno.

Cierra la fundación del repo DOCYAN en estado operable. Absorbe: push del commit del Sprint B0 previo (61 tests en local sin pushear); rebrand completo Panohayan→DOCYAN + PKG→DKG + PTM→DTM (221 ocurrencias); eliminación de `railway.toml`; corrección de deuda de seguridad de auditoría abril (JWT_SECRET default inseguro, dev API key hardcodeada, bug `sql.py:38`, CORS wildcard, Dockerfile `sed` frágil); `GEMINI_API_KEY`/`OPENAI_API_KEY`/`ANTHROPIC_API_KEY` en `.env.example`; 6 migraciones SQL faltantes (`documents`, `entities`, `audit_trail`, `governance_rules`, `quarantine`, `api_keys`); `pyproject.toml`; **bootstrap completo del workspace frontend** (Next.js 15 + React 19 + Tailwind + shadcn/ui + react-i18next + Vitest + Playwright); `vercel.json`; pipeline OpenAPI 3.1→TypeScript con `openapi-typescript`; deploy real verificado a Fly.io + Vercel; CI ejecutado en GitHub Actions.

**Por qué el frontend entra en B0:** la auditoría confirmó cero frontend. B8/B10/B11/B12 asumen scaffolding existente. Sin él, esos bloques no pueden arrancar. El frontend bootstrap entra en B0 en secuencia correcta (no antes de tener backend que tipar vía OpenAPI, no después de necesitarlo en B8).

**Salida verificable:** `grep -ri panohayan` = 0; `grep -ri "\bPKG\b\|\bPTM\b"` = 0 en código; `fly status` app `docyan-lde-api` health 200; Vercel placeholder accesible; 61+ tests backend + 2+ frontend pasando en CI; 8 tablas con migraciones.

---

### B1 — DKG sobre GraphRAG-SDK + multi-tenant + versionado + sistema de esquemas
**Estado:** Alcance reformulado + ampliado.
**Prerequisitos:** B0.

Integra GraphRAG-SDK 1.1.1. Configura BGE-M3 self-hosted como embedder custom (validación crítica). Config de modelos de ingesta (Gemini 2.5 Flash extracción/resolution, gpt-4o-mini QA, `deduplicate_entities(fuzzy=True)` con await correcto). Schema DKG según doc 01 (nodos `:EntidadOperativa`, `:DocumentoSource`, `:DocumentoTraducido`, `:CategoriaEntidad`, `:Especificacion`, `:TerminoTecnico`, y los específicos por tipo de intención). Multi-tenancy por `graph_name`↔`tenant_id`. Versionado in-place con `:VERSION_HISTORICA`/`:VersionAnterior`. Retiro controlado de DII (deprecated, eliminación tras B5). Respaldo FalkorDB (decisión #12).

**Sistema de esquemas (componente central):** catálogo del mercado meta completo (NOM, ley, reglamento, ISO, manual técnico, MSDS, calibración, especificación, ficha técnica, memoria de traducción — todos presentes, todos ajustables) + generador dinámico Gemini 2.5 Flash que deriva schema según documento + contexto de usuario cuando no calza. Evidencia: Contrato 5, schema rígido cruzado = 0 relaciones.

**Salida verificable:** documento ingiere vía SDK, grafo poblado con provenance nativo, multi-tenant aislado, versionado registra cambios, BGE-M3 confirmado como embedder activo, generador produce schema y >0 relaciones para documento fuera del catálogo (replica caso LGPGIR).

---

### B2 — DTM + segregación estricta + TM dual + lock terminológico
**Estado:** Alcance reformulado.
**Prerequisitos:** B1.

Schema DTM según doc 02 (`:SegmentoTraduccion` con 23 tipos de segmento, `:Glosario`, `:TerminoGlosario`, `:RegistroRevision`, `:SugerenciaTermino`). Segregación estricta por par lingüístico (5 pares día 1: en-US↔es-MX, en-US↔es-US, en-US↔es-ES, en-UK↔es-MX, en-UK↔es-ES). TM dual con prioridad cliente sobre agencia (orden: match exacto TM cliente → parcial ≥75% TM cliente → TM agencia → nuevo). Lock terminológico como función técnica (constraint + post-validación que reemplaza y registra `:SugerenciaTermino` estado `reportada_al_cliente`). Matching fuzzy híbrido Levenshtein+BGE-M3. Aristas cross DKG↔DTM (`:TRADUCIDA_VIA`, etc.). Exportación a TMX/XLIFF/TBX.

**Salida verificable:** segregación por par demostrada, prioridad cliente en TM dual, lock rechaza violaciones técnicamente, fuzzy híbrido en las 6 bandas del tabulador.

---

### B3 — Master Orchestrator + Tokens QR + Cotizador pre-ingesta
**Estado:** Alcance ampliado.
**Prerequisitos:** B1 (B2 en paralelo).

MO completo según doc 05 (10 responsabilidades, 6 sub-componentes: Context Resolver, Intent Router, Pipeline Coordinator, Session Manager, Governance Gate, Scheduler). Reemplaza el `DocyanOrchestrator` actual (coordinación CLI básica). Tokens QR persistentes vinculados a `:EntidadOperativa` + endpoint público de resolución contextual. Session Manager Redis con TTLs exactos (consulta 30min, troubleshooting 2h, revisión 8h, onboarding 30 días, todos sliding) + spillover Supabase. APScheduler backend Redis. Governance Gate que invoca GRG. **Cotizador pre-ingesta tiktoken** (mide tokens antes de ingerir, estima costo con baselines del PoC, verifica presupuesto disponible del tenant, pide confirmación, contempla tiempo por rate limiting de Gemini).

**Salida verificable:** QR resuelve a contexto correcto, MO orquesta sesión completa con transición de canal, cotizador rechaza ingestas sobre presupuesto y confirma las viables, scheduler ejecuta tareas por tenant.

---

### B4 — Motor de Traducción Rigurosa (Pista A) + 3 tiers
**Estado:** Alcance reducido (retrieval se apoya en SDK; las 6 fases siguen siendo propias).
**Prerequisitos:** B2, B3. Paralelo con B5.

Pipeline de 6 fases según doc 12: normalización → segmentación (23 tipos de segmento) → repeticiones internas → match DTM cliente (tabulador 100/95-99/85-94/75-84/50-74/0-49, umbral 50%) → match corpus terminológico + glosario con lock → traducción LLM con grafos. **Tabla origen→acción exacta:** 100% y repeticiones y 95-99% NO invocan LLM; 85-94%/75-84%/50-74% invocan LLM con fuzzy como referencia; 0-49% traducción nueva. Prompts especializados por los 23 tipos de segmento con sus restricciones (CPS subtítulos, ANSI Z535 advertencias, longitud etiquetas, etc.). Conflictos terminológicos: mostrar todas las opciones al revisor (Tier 2/3) o prioridad automática (Tier 1: DTM cliente > glosario > corpus > LLM). Sin QA interno automático. Scoring por segmento con pesos exactos (30% confianza LLM, 20% glosario, 20% DTM, 15% reglas tipo, 15% cross-segmento). Reconstrucción de formato original (PDF weasyprint/reportlab, DOCX python-docx, XLSX openpyxl, HTML lxml, imagen OCR+overlay, video VTT/SRT). 3 tiers de servicio (Tier 1 agente IA, Tier 2 +revisor externo, Tier 3 +revisor interno cliente). Routing por MR (Claude Sonnet 4.6 + Gemini 2.5 Pro, tier medio piloto).

**Salida verificable:** documento source EN → es-MX completo, formato original preservado, scoring por segmento, lock respetado, matches correctamente aprovechados sin invocar LLM donde no corresponde.

---

### B5 — Ingesta Bilingüe (Pista B) + Alineadores
**Estado:** Alcance reducido.
**Prerequisitos:** B2, B3. Paralelo con B4.

Parser de formatos CAT Modo A (TMX, XLIFF, TBX, SDLXLIFF, Bilingual DOCX). Alineador Modo B (Vecalign primario + Hunalign fallback, decisión automática por score, pares <0.7 flagueados para UI #3). Modo C (conector CAT) es MVP v2, NO en este bloque. Pipeline Docling → LlamaIndex → GraphRAG-SDK al DTM segregado por par. DTM derivada con `origen_propuesta=agencia_externa`. Vinculación uno-a-muchos `:DocumentoSource`→N `:DocumentoTraducido` (Magna 12-20 idiomas). Resolución de idioma del operador.

**Salida verificable:** agencia carga TMX/XLIFF/etc, ingiere, DTM segregada por par poblada, alineación con métricas, fallback Hunalign funcional.

---

### B6 — GRG extendido (8 familias) + FAT extendido (9 familias + SHA-256)
**Estado:** Alcance ampliado.
**Prerequisitos:** B3, B4 (al menos parcial). Paralelo con B4/B5.

**GRG con 8 familias de reglas según doc 07** (con códigos): F1 lock terminológico (R-LT-01/02/03), F2 umbrales de confianza por criticidad (R-UC-01 a 05: seguridad ≥0.95, regulatorio ≥0.90, calidad ≥0.85, operacional ≥0.75, informativa ≥0.60), F3 freno de alucinación (fabricación numérica/referencias normativas/identificadores), F4 fidelidad de no-traducibles (fórmulas químicas, unidades SI, marcas, marcadores paramétricos), F5 validación por tipo de segmento (CPS, longitud etiquetas, imperativo en pasos, tono ANSI Z535), F6 consistencia cross-segmento (intra-documento, cross-documento del cliente), F7 consulta operativa (3 reglas UI #1), F8 canal PWA vs WhatsApp. `:ConfiguracionGRG` por tenant. Cache config 15min, sin cache para segmentos individuales.

**FAT con 9 familias de eventos según doc 08 + cadena criptográfica:** algoritmo SHA-256 sobre `(evento_id || timestamp || tipo_evento || payload || hash_evento_anterior)`. Inmutabilidad append-only, corrección vía `corrige_evento_id`. 9 familias (pipeline traducción, revisión humana, ingesta bilingüe, consulta operativa, troubleshooting, alertas, gobernanza, onboarding, sistema/meta-FAT). Retención por familia (7 años producción/revisión/ingesta/gobernanza, 5 onboarding, 3 consulta/troubleshooting/alertas, 2 sistema). Implementación híbrida (eventos críticos en FalkorDB, alta frecuencia en Supabase). Reconstrucción de estado en cualquier punto. Exportación PDF/XML/JSON/CSV. Verificador de integridad de cadena.

**Salida verificable:** GRG flagea según las 8 familias, FAT registra con integridad criptográfica verificable (alterar evento rompe cadena), reportes auditables exportables.

---

### B7 — Clasificador de Intención + Pipelines Tipos 1-8 + Chat persistente
**Estado:** Alcance ampliado.
**Prerequisitos:** B3.

Clasificador híbrido según doc 03: heurístico para casos obvios + LLM classifier (Gemini 2.5 Flash para minimizar costo) cuando heurístico no resuelve + fallback. Pipelines para los 8 tipos confirmados MVP v1 con sus estructuras DKG y componentes: T1 Informativa (`:Especificacion`+`:TerminoTecnico`→`<InfoCard/>`), T2 Guía paso a paso (`:Procedimiento`+`:Paso`+`:EPP`+`:Herramienta`+`:Advertencia`→`<ProcedureCard/>`), T3 Gráficos (`:RecursoVisual`+`:Etiqueta`+`:LeyendaSimbolica`→`<DiagramViewer/>`), T4 Video (`:RecursoVideo`+`:Capitulo`+`:Subtitulo`+`:Transcripcion`→`<VideoPlayer/>`), T5 Troubleshooting (`:ArbolDiagnostico`+`:NodoDecision`+`:CausaProbable`+`:AccionResolutoria`→`<DiagnosticTree/>`), T6 Historial (`:EventoOperativo`+`:CertificadoVigencia`+`:Observacion`+`:MedicionRegistrada`→`<TimelineView/>`), T7 Alertas (`:Alerta`+`:ReglaAlerta`+`:AccionSobreAlerta`→`<AlertsDashboard/>`, con scheduler APScheduler), T8 Comparativa (`:SesionComparativa`+`:DiferenciaDetectada`+`:ReporteComparativo`→`<ComparativeView/>`). Cruces estructurales entre tipos. Resolución de idioma del operador. Composición de respuesta JSON tipada Pydantic v2. **Chat persistente multi-turno** (GraphRAG-SDK `completion()` con `history`, Session Manager de B3).

**Salida verificable:** consulta clasifica correctamente y ejecuta pipeline apropiado con respuesta estructurada lista para renderización condicional; chat multi-turno mantiene contexto.

---

### B8 — UI #1 Consulta Operativa PWA + Visualizaciones + Anotaciones + Alertas
**Estado:** Alcance ampliado.
**Prerequisitos:** B0, B7, B6. Paralelo con B10.

PWA Next.js 15 en Vercel. Landing del QR con resolución de idioma del operador (prioridad: usuario auth > Accept-Language > selector > default sitio; fallback a idioma cercano con disclaimer) y selector de canal (PWA vs WhatsApp según política del tenant). 8 componentes de renderización condicional por tipo de intención (`<InfoCard/>`, `<ProcedureCard/>`, `<DiagramViewer/>` con overlay, `<VideoPlayer/>`, `<DiagnosticTree/>`, `<TimelineView/>`, `<AlertsDashboard/>`, `<ComparativeView/>`). **Visualizaciones por tipo de documento** (consume sistema de esquemas de B1). **Chat persistente** (consume B7). **Anotaciones** vinculadas a entidades/documentos (capa complementaria, NO registro primario). **Alertas administrativas** con `safety_validator` que rechaza cualquier alerta clínica/operativa (línea ABSOLUTA, requisito legal, cobertura de tests crítica). **Pedigree clickeable** (provenance nativo del SDK). Service worker PWA + offline parcial. Captura de feedback por consulta. react-i18next. Tipos TS desde OpenAPI.

**Salida verificable:** operador escanea QR, consulta en su idioma, recibe respuesta renderizada por tipo, ve visualización por tipo de documento, anota, ve alertas administrativas válidas, validador bloquea casos clínicos/operativos, pedigree clickeable funcional.

---

### B9 — WhatsApp + Adaptador de canal + 360dialog
**Estado:** Sin cambio.
**Prerequisitos:** B7, B8.

Integración 360dialog (acceso directo API). Plantillas WhatsApp pre-aprobadas multilingües por idioma activo del tenant. Adaptaciones por tipo de intención al canal (T1 texto+cita, T2 lista numerada+advertencias inline, T3 imagen+texto, T4 link video+timestamp, T5 nodos secuenciales con botones, T6 resumen+link PWA, T7 texto+acción, T8 resumen+link PWA). Resolución de idioma del operador en WhatsApp. Sesiones persistentes troubleshooting (TTL 2h). División de mensajes >4096 caracteres. Channel adapter unificado PWA/WhatsApp. Transición de canal preservando sesión (Session Manager B3).

**Salida verificable:** operador escanea QR, conversa en WhatsApp en su idioma, recibe respuestas adaptadas al canal, continúa sesión en PWA.

---

### B10 — UI #2 Revisión Lingüística
**Estado:** Sin cambio.
**Prerequisitos:** B4, B6. Paralelo con B8.

SPA Next.js + shadcn/ui (desktop, no PWA). Vista del documento traducido completo (flujo principal, NO segmento a segmento como CAT tools) + vista alterna bilingüe segmento a segmento bajo demanda. Panel detalle por segmento (origen de propuesta: match exacto/fuzzy/glosario/LLM nuevo; score de confianza; justificación; match DTM usado). Acciones por segmento: validar/editar/rechazar/comentar (registradas en FAT). Propagación automática a repeticiones internas + des-propagación manual. Lock terminológico visible (segmentos lockeados marcados, sugerencias bloqueadas visibles). Modos por rol: AUDITOR (revisor agencia/DOCYAN, flujo estándar), AUDITOR EXTERNO (revisor cliente Tier 3, aprobación final + objeciones). Resolución de conflictos AUDITOR vs AUDITOR EXTERNO. Función "pedir otra propuesta IA" (re-traducción de segmento). Solo Pista A.

**Salida verificable:** revisor valida documento completo, edita con propagación, lock respetado visualmente, acciones en FAT, modos por rol con permisos correctos.

---

### B11 — UI #3 PM Dashboard + Cotizador pre-venta
**Estado:** Sin cambio (con cotizador pre-venta explícito).
**Prerequisitos:** B4, B5, B10.

Dashboard Next.js + shadcn/ui. Vista de proyectos activos (Pista A producción; Pista B ingesta + sub-tenants). **Módulo de Cotización pre-proyecto** (distinto del cotizador de ingesta de B3): recibe documentos del prospecto, corre DII/pipeline + segmentación, aplica matching contra DTM existente del cliente, **NO invoca LLM (sin costo)**, devuelve estimación de volumen por banda fuzzy + costo proyectado. Configuración por proyecto (par lingüístico, glosario, lock, DTM activa, tier). Vista FAT del proyecto. Gestión de reglas GRG por tenant sin tocar código. Asignación de revisores externos a Tier 2/3. Configuración de plantillas WhatsApp por idioma. UI #3 simplificada Pista B (revisión opcional de pares <0.7 del alineador).

**Salida verificable:** PM gestiona proyectos, asigna revisores, configura clientes, ejecuta cotizaciones pre-venta sin costo de LLM.

---

### B12 — UI #4 Onboarding (3 modalidades, 12 pasos)
**Estado:** Sin cambio estructural.
**Prerequisitos:** B11 (e indirectamente B1, B2, B3, B6, B7, B8, B10).

Wizard secuencial Next.js + shadcn/ui. 3 modalidades (A cliente final industrial directo Pista A, B agencia Pista B simplificada, C sub-tenant cliente final de agencia). 12 pasos del doc 06: identificación cliente, modalidad/tier, pares lingüísticos, carga entidades operativas + categorización + QRs, carga documentos source (pipeline de ingesta), carga glosarios cliente (CSV/TBX) o construir orgánicamente, config lock terminológico, usuarios/roles, **criticidad obligatoria (decisión #15, delegable a inferencia automática)**, reglas GRG personalizadas, validación funcional end-to-end con doc real del cliente, activación del tenant. Generación de QRs físicos para imprimir (PDF descargable). Chat de soporte con responsable DOCYAN durante wizard. Pausa/reanudación (TTL 30 días). Tests E2E del flujo completo.

**Salida verificable:** cliente nuevo completa onboarding (12 pasos) en cualquier modalidad y queda activo en producción, con QRs físicos generados, criticidad configurada o delegada.

---

### B13 — Tipos 9-11 + Hardening final
**Estado:** Sin cambio.
**Prerequisitos:** B7, B8, y resto del MVP.

Tipos de intención adicionales (doc 03): T9 Cumplimiento normativo (`:Norma`+`:RequisitoNormativo`+`:EvaluacionCumplimiento`→`<ComplianceView/>` — alto valor labs ISO 17025, probable sí), T10 Cadena causal (`:RelacionCausal`+`:CadenaImpacto`+`:NodoImpacto`→`<ImpactChain/>` navegable), T11 Capacitación contextual (`:ModuloFormativo`+`:UnidadAprendizaje`+`:RegistroAprendizaje`→`<LearningExperience/>`). La decisión de cuáles implementar depende del primer cliente; T9 probable sí, T10/T11 según necesidad real. Hardening: rate limiting API, migraciones formales consolidadas, observabilidad (Sentry/Datadog/Fly.io), documentación API (OpenAPI + Swagger UI), plantillas multilingües 360dialog, optimización Dockerfile (PyTorch solo si BGE-M3 no corre como servicio separado — evaluar, no eliminar a ciegas), verificación de seguridad final, eliminación definitiva de DII (tras B5).

**Salida verificable:** producto vendible primer cliente, monitoreado, documentado, seguro, con tipos de intención adicionales según necesidad real.

---

## Sección 3 — Sistema de esquemas: catálogo del mercado meta + generador dinámico

**Naturaleza:** componente de diseño CENTRAL. Evidencia dura del PoC (Contrato 5, REPORTE_CONTRATO5.md): el schema diseñado para NOM-052 (norma técnica: CRETIB, PECT, procedimientos) extrajo **0 relaciones semánticas** de la LGPGIR (ley general: artículos, competencias, sanciones, "prestadores de servicios de manejo"). El mecanismo multi-documento al mismo grafo funciona y MultiPathRetrieval cruza chunks bien; lo que falla es la cobertura de schema cuando el documento no calza con el molde. El schema debe corresponder al **TIPO de documento + el contexto del usuario**.

**NO es lista parcial a implementar.** Dos capas que conviven desde el diseño:

**Capa 1 — Catálogo del mercado meta (completo desde el diseño, todo ajustable):**
Todos los tipos presentes como estructura: NOM, ley, reglamento, norma ISO, manual técnico, MSDS, histórico de calibraciones, especificación, ficha técnica, memoria de traducción — y los que aparezcan con clientes reales. Ninguno se descarta ni se difiere. Todos se ajustan iterativamente según feedback de pilotos/usuarios. El catálogo es vivo.

**Capa 2 — Generador dinámico (Gemini 2.5 Flash):**
Analiza documento + contexto de usuario (industria, operación, par lingüístico, tier) y deriva el schema de extracción. Si calza con el catálogo, lo usa/refina; si no calza (caso LGPGIR), genera schema nuevo en vez de producir 0 relaciones. Los schemas generados realimentan el catálogo. Gemini 2.5 Flash es el modelo idóneo: ya es el extractor de la config de ingesta, y su capacidad de inferir sujetos implícitos de voz pasiva regulatoria (demostrada en PoC) es lo que se necesita para derivar estructura de documentos no vistos.

**Conexión:** el tipo de documento define schema de extracción (B1) Y visualización (B8). Catálogo + generador alimentan ambos.

**Código:** `app/schemas_documentales/catalogo/` (módulo por tipo) + `generador.py` (Gemini 2.5 Flash) + `registry.py` (registro vivo). Construido en B1.

---

## Sección 4 — Dos cotizadores distintos (aclaración crítica)

El modelado tiene **dos** mecanismos de cotización que NO deben confundirse:

1. **Cotizador pre-ingesta (B3, adenda sección 8):** mide tokens con tiktoken antes de ingerir un documento al grafo GraphRAG-SDK, estima costo de extracción/QA (baselines PoC: NOM 32pp $0.036, Ley 61pp $0.046), verifica presupuesto disponible del tenant, pide confirmación. Protección financiera contra el hard cap. SÍ contempla costo de LLM de ingesta.

2. **Cotizador pre-venta de traducción (B11, doc 14):** módulo de UI #3 PM que recibe documentos de un prospecto, corre DII/pipeline + segmentación + matching contra DTM existente, **NO invoca LLM** (sin costo significativo), devuelve estimación de volumen por banda fuzzy + costo proyectado de proyecto de traducción. Herramienta comercial de pre-venta.

Ambos se construyen. Son componentes separados con propósitos distintos.

---

## Sección 5 — Pendientes técnicos del PoC a resolver en construcción

| Pendiente | Bloque | Acción |
|-----------|--------|--------|
| `finalize()`/`deduplicate_entities()` async sin await | B1 | Manejar async correcto. SDK tiene `finalize_sync()` pero NO `deduplicate_entities_sync()` — usar await/asyncio.run. Test de regresión. |
| BGE-M3 como embedder custom de GraphRAG-SDK | B1 | Validación crítica. Vía ABC o LiteLLM. Si falla directo, adapter custom. El modelo NO cambia (decisión confirmada). |
| Sistema de esquemas (catálogo + generador) | B1 | Catálogo completo del mercado meta + generador Gemini 2.5 Flash. Test con caso LGPGIR. |
| Cotizador pre-ingesta tiktoken | B3 | Con baselines del PoC + contempla tiempo por rate limiting Gemini. |
| Rate limiting Gemini Flash (1,506 retries en multi-doc) | B1, B3 | Retry con tenacity (ya en deps) + cotizador contempla tiempo. |
| `deduplicate_entities(fuzzy=True)` post-ingesta | B1 | Obligatorio (653 residuos sin dedup en Contrato 5). No opcional. |
| Idioma mixto en descripciones de Gemini | B1 | Forzar idioma en prompt de extracción. |
| Rebrand Panohayan→DOCYAN, PKG→DKG, PTM→DTM | B0 | Resuelto. Rename completo. |
| `railway.toml` + deuda seguridad auditoría abril | B0 | Eliminar Railway + corregir secrets/CORS/sql.py:38. |
| 6 migraciones SQL faltantes | B0 | `002`-`007`. |
| Variables de entorno faltantes | B0 | GEMINI/OPENAI/ANTHROPIC en `.env.example`. |

---

## Sección 6 — Orden de ejecución y paralelismos

Mapa de dependencias del doc 14, confirmado:

```
B0 → B1 → B2 → B3
                ├─→ B4 (Pista A)  ┐
                ├─→ B5 (Pista B)  ├─ paralelos tras B3
                ├─→ B6 (GRG+FAT)  ┘ (B6 paralelo a B4/B5)
                └─→ B7
                      ├─→ B8 (UI#1)  ┐ paralelos
                      │     └─→ B9   │
                      └─→ B10 (UI#2) ┘
                            └─→ B11 (UI#3)
                                  └─→ B12 (UI#4)
                                        └─→ B13
```

**Orden de generación/ejecución de Sprint Contracts:** B0 → B1 → B2 → B3 → B4 → B5 → B6 → B7 → B8 → B9 → B10 → B11 → B12 → B13. Catorce contratos. Iteración solo ante bloqueador real.

---

## Sección 7 — Criterio de MVP demo-able

Subconjunto mínimo para mostrar valor a un cliente piloto de Pista A (laboratorio ISO 17025 o maquiladora IMMEX), sin desactivar la regla inviolable de no contactar antes:

**MVP demo-able Pista A = B0 + B1 + B2 + B3 + B4 + B6 + B7 + B8 + B12.**

- B0: base operable.
- B1: DKG + ingesta + sistema de esquemas.
- B2: DTM + lock terminológico (diferenciador para industria regulada).
- B3: MO + QR + cotizador (el QR escaneable resolviendo a contexto es el diferenciador físico).
- B4: Motor de Traducción Rigurosa con lock (núcleo de Pista A).
- B6: GRG + FAT con hash chain (un lab ISO 17025 exige auditoría criptográfica).
- B7: clasificador + 8 pipelines + chat persistente.
- B8: UI #1 PWA con visualizaciones + anotaciones + alertas administrativas.
- B12: onboarding (activa al cliente piloto con sus propios documentos).

**No requeridos para demo-able Pista A** (entran después, sin recortar — se construyen igual): B5 (Pista B), B9 (WhatsApp, canal secundario), B10 (UI #2 revisión, para Tier 2/3), B11 (UI #3 PM, multi-proyecto), B13 (tipos adicionales + hardening, antes de cobrar).

**Pista B demo-able** requiere adicionalmente B5 + B10 + B11 antes de contactar agencias (Hafida, Sonia/Octagon-Magna).

**Condición exacta para activar contactos comerciales:** los bloques del MVP demo-able completos, tests en CI, deploy real verificado, y ≥1 documento real (NOM/ISO/regulatorio T-MEC) ingerido end-to-end mostrando ingesta cotizada + grafo poblado + consulta clasificada + respuesta con visualización + pedigree clickeable + alerta administrativa + FAT auditable. Solo entonces se activan contactos. Antes: silencio comercial. Regla inviolable.

---

*Fin del Plan de desarrollo del MVP de DOCYAN — v2 post-PoC.*
*XCID SA de CV — DOCYAN LDE™ — 28 mayo 2026.*
