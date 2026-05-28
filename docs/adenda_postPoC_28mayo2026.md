# Adenda post-PoC — DOCYAN LDE

**Fecha:** 28 mayo 2026
**Origen:** 6 reportes del PoC de GraphRAG-SDK sobre NOM-052-SEMARNAT-2005 y LGPGIR + decisiones del fundador.
**Estado:** documento de referencia vigente. Complementa y, donde se indica, actualiza los 15 documentos arquitectónicos y las 15 decisiones del Paso C.

Este documento es la fuente de verdad de los cambios introducidos tras el PoC. Trackeable en el repo para que cualquier instancia de trabajo (humana o IA) parta de la misma base.

---

## 1. Rebrand: Panohayan → DOCYAN

El producto pasa a llamarse **DOCYAN LDE — Live Document Environment by XCID**. Rebrand completo en código, documentación, infraestructura. Confirmado por Jorge:
- Repo: `docyan-lde-core`.
- App Fly.io: `docyan-lde-api`.
- Grafo FalkorDB default: `docyan`.
- Clase orquestadora: `DocyanOrchestrator`.

## 2. Siglas: PKG→DKG, PTM→DTM

- **DKG** — Document Knowledge Graph (antes PKG, Panohayan Knowledge Graph).
- **DTM** — Document Translation Memory (antes PTM, Panohayan Translation Memory).

Rename completo en código, strings, comentarios y documentación.

## 3. Deuda técnica y de seguridad a cerrar

De la auditoría de abril 2026, aún presente: JWT_SECRET con default inseguro, dev API key hardcodeada, bug en `sql.py:38` (`int()` sobre string vacío), CORS wildcard, `sed` frágil en Dockerfile. Más: `railway.toml` legacy (Railway retirado), 6 migraciones SQL faltantes, variables de entorno de LLMs ausentes de `.env.example`, frontend inexistente. Todo se cierra en B0.

## 4. Cambio arquitectónico central: GraphRAG-SDK reemplaza el DII

El DII propio (352 LOC reales) causó el incidente de ~$5,000 con Gemini: timeout de 600s, escritura parcial al grafo, sin control de costo ni de tiempo. Se reemplaza por **FalkorDB GraphRAG-SDK 1.1.1**, validado en el PoC:

- Ingesta en <5 min (vs el timeout previo).
- Escritura transaccional crash-safe (`apply_changes()` con SHA-256).
- **Provenance nativo:** edges `MENTIONED_IN`, `PART_OF`, `NEXT_CHUNK` + chunks con spans de caracteres. Base del pedigree clickeable.
- **Multi-tenancy nativa** por `graph_name` (sirve aislamiento de tenants y la relación Agencia↔Cliente Final de Pista B).
- Estrategias de extracción/resolución swappables.
- LLM-agnóstico vía LiteLLM.

## 5. Stack de ingesta multi-formato y configuración de modelos

**Pipeline:** Docling (conversión universal) → LlamaIndex (indexación) → GraphRAG-SDK → FalkorDB.

**Configuración de modelos validada por el PoC (Contrato 4):**
- **Extracción:** Gemini 2.5 Flash — model string `gemini/gemini-2.5-flash` vía LiteLLM. El prefijo `gemini/` es **obligatorio**; sin él, LiteLLM defaultea a Vertex AI y falla pidiendo credenciales GCP. Variable `GEMINI_API_KEY` (no `GOOGLE_API_KEY`).
  - Evidencia: 15 obligaciones extraídas vs 4 de gpt-4o; 13 relaciones DEBE_CUMPLIR vs 4; cadenas regulatorias completas; costo de mini ($0.036/doc para NOM de 32pp). Gana 9 de 11 criterios.
- **QA:** gpt-4o-mini (~$0.002/consulta). Es el control de calidad del pipeline de ingesta; **no es dependencia fantasma**, se conserva.
- **Resolution:** Gemini 2.5 Flash (LLMVerifiedResolution).
- **Post-proceso obligatorio:** `deduplicate_entities(fuzzy=True)`. El Contrato 5 dejó 653 entidades duplicadas por no ejecutarlo (era async sin await + rate limit). No es opcional.

**Bugs del PoC a corregir en construcción (B1):**
1. `finalize()` y `deduplicate_entities()` son async y se llamaron sin `await`. El SDK tiene `finalize_sync()` pero **no** `deduplicate_entities_sync()` — manejar con `await`/`asyncio.run`.
2. Rate limiting severo de Gemini Flash: 1,506 retries en ingesta multi-documento (TPM 30K en el tier actual). Mitigar con retry (tenacity) y contemplar el tiempo en el cotizador.

**Limitaciones a mitigar (no a aceptar):** tiempo de ingesta 2.7x vs gpt-4o (aceptable one-time, monitorear); idioma mixto ES/EN en descripciones (forzar idioma en el prompt); 1 chunk con JSON inválido de 104 (recuperación automática del SDK, monitorear).

**Embedder:** **BGE-M3 self-hosted (firme).** El PoC usó text-embedding-3-small solo por conveniencia de prueba; nunca comparó calidad. BGE-M3 es superior para el caso multilingüe de DOCYAN (Magna 12-20 idiomas), garantiza soberanía de datos para industria regulada, costo cero recurrente y control de versionado para el FAT a 7 años. B1 valida la integración con GraphRAG-SDK como embedder custom (vía ABC o LiteLLM); si la vía directa falla, se construye adapter — el modelo no cambia.

## 6. Hallazgo central: el schema debe corresponder al tipo de documento + contexto del usuario

**Evidencia dura (Contrato 5):** el schema diseñado para NOM-052 (norma técnica: CRETIB, PECT, procedimientos de prueba) extrajo **0 relaciones semánticas** al aplicarse a la LGPGIR (ley general: artículos, competencias de autoridades, sanciones, "prestadores de servicios de manejo"). El mecanismo multi-documento al mismo grafo funciona y MultiPathRetrieval cruza chunks correctamente; lo que falla es la **cobertura del schema** cuando el documento no calza con el molde.

**Conclusión de diseño:** el sistema de esquemas no es una lista parcial de tipos a implementar. Son **dos capas que conviven desde el diseño**:

1. **Catálogo del mercado meta (completo, vivo, ajustable).** Todos los tipos del mercado presentes como estructura desde el inicio: NOM, ley, reglamento, norma ISO, manual técnico, MSDS, histórico de calibraciones, especificación, ficha técnica, memoria de traducción — y los que aparezcan con clientes reales. Ninguno se descarta ni se difiere. Todos se ajustan iterativamente según el feedback de pilotos y usuarios.

2. **Generador dinámico (Gemini 2.5 Flash).** Cuando un documento no calza con el catálogo (caso LGPGIR), el generador analiza documento + contexto del usuario (industria, operación, par lingüístico, tier) y deriva un schema de extracción adecuado, en vez de producir 0 relaciones. Los schemas generados realimentan el catálogo. Gemini 2.5 Flash es el modelo idóneo: ya es el extractor del pipeline, y su capacidad demostrada en el PoC de inferir sujetos implícitos de la voz pasiva regulatoria es justo lo que se necesita para derivar estructura de documentos no vistos.

El tipo de documento determina tanto el **schema de extracción** (DKG, B1) como la **visualización** (UI, B8). Catálogo + generador alimentan ambos. Se construye en B1.

## 7. Funcionalidades confirmadas (ampliaciones sobre los DAs)

- **Visualizaciones por tipo de documento:** además de la renderización por tipo de intención (8 componentes del doc 04), cada tipo de documento (NOM, MSDS, calibración, etc.) tiene visualización dedicada, conectada al sistema de esquemas. (B8.)
- **Chat persistente en contexto:** GraphRAG-SDK soporta conversación multi-turno nativa (`completion()` con `history`). El operador conversa con el documento vivo manteniendo contexto de sesión. (B7 + B8.)
- **Anotaciones vinculadas:** notas del usuario sobre entidades/operaciones/documentos. **Capa complementaria, no sistema de registro primario.** (B8.)
- **Pedigree clickeable:** el provenance nativo del SDK se expone como navegación clickeable de cada dato a su fuente exacta (chunk → documento). (B8.)
- **Cotizador pre-ingesta:** medición de tokens (tiktoken) + estimación de costo + verificación de presupuesto + confirmación, antes de ingerir. Protección contra el hard cap (el PoC topó el cap de Google a MXN 119 en incidente controlado). Contempla tiempo además de costo por el rate limiting de Gemini. Baselines: NOM 32pp $0.036, Ley 61pp $0.046, corpus 50 normas+10 leyes ~$2.26. (B3.) **Distinto** del cotizador pre-venta de traducción (B11), que corre matching sin invocar LLM.

## 8. Protección financiera de la ingesta

Saldo prepagado finito sin auto-recharge + hard cap + cotizador pre-ingesta obligatorio. Operacionaliza el Token Budget por plan. Ninguna ingesta procede sin estimación y confirmación.

## 9. Línea de seguridad ABSOLUTA: alertas solo administrativas

Las alertas (Tipo 7) son **exclusivamente administrativas**: vencimientos, documentos faltantes, fechas de calibración, certificados por expirar. **Nunca** clínicas ni operativas. Una alerta que sugiera una decisión clínica u operativa convertiría al producto en software como dispositivo médico (SaMD), con implicaciones de COFEPRIS/FDA y responsabilidad por mala praxis.

Se codifica como un `safety_validator` **rechazante** (no como nota en documentación): ante cualquier alerta cuyo contenido sugiera decisión clínica/operativa, el validador rechaza por defecto. Requisito legal con cobertura de tests crítica. (B8.)

## 10. Modelos de traducción (Pista A) — sin cambio

El cambio de modelos introducido por el PoC aplica **solo al pipeline de ingesta**. La traducción de Pista A mantiene Claude Sonnet 4.6 + Gemini 2.5 Pro vía Model Router, tier medio para el piloto.

## 11. Pendientes técnicos consolidados

| Pendiente | Bloque |
|-----------|--------|
| Manejo async correcto de `finalize()`/`deduplicate_entities()` | B1 |
| BGE-M3 como embedder custom del SDK (validación + adapter si falla) | B1 |
| Sistema de esquemas: catálogo + generador (test con caso LGPGIR) | B1 |
| Conflictos de versión graphrag-sdk/litellm con stack frozen (resolver real) | B1 |
| Cotizador pre-ingesta tiktoken (costo + tiempo) | B3 |
| Mitigación de rate limiting Gemini (tenacity) | B1, B3 |
| `safety_validator` de alertas (línea ABSOLUTA) | B8 |
| Rebrand + deuda de seguridad + frontend bootstrap | B0 |

---

*Esta adenda se mantiene sincronizada con `CLAUDE.md` y con el Plan de desarrollo v2 post-PoC.*
*XCID SA de CV — DOCYAN LDE™ — 28 mayo 2026.*
