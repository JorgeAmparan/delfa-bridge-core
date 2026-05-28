# Sprint Contract B1 — DKG sobre GraphRAG-SDK + multi-tenant + versionado + sistema de esquemas

**Producto:** DOCYAN LDE — Live Document Environment by XCID
**Bloque:** B1 | **Ejecutor:** Opus 4.8 vía Claude Code CLI
**Modo:** Una aprobación + ejecución completa + un reporte final.

---

## Prerequisitos
B0 completo (repo `docyan-lde-core`, frontend bootstrapeado, deploys reales, 61+ tests en CI, 8 migraciones, rebrand total).

## Contexto para Opus
Cambio arquitectónico mayor de la adenda: el DII (352 LOC) se reemplaza por **FalkorDB GraphRAG-SDK 1.1.1**. El DII causó el incidente de $5,000 con Gemini (timeout 600s, escritura parcial, sin control de costo). El PoC (6 contratos sobre NOM-052 + LGPGIR) confirmó que el SDK resuelve esto: ingesta <5min, escritura transaccional, provenance nativo (`MENTIONED_IN`+`PART_OF`+`NEXT_CHUNK` + spans de caracteres), multi-tenancy por `graph_name`, `apply_changes()` crash-safe con SHA-256, estrategias swappables, LLM-agnóstico vía LiteLLM.

Estado del repo: GraphRAG-SDK ausente (no en deps, no en código). FalkorDB skeleton 34 LOC sin uso. DII único pipeline funcional. Docling 2.84.0 y LlamaIndex 0.14.19 ya en deps (stack de ingesta multi-formato). tiktoken 0.12.0 ya en deps.

## Alcance específico

1. **Integrar GraphRAG-SDK 1.1.1.** Agregar a deps. **Resolver conflictos de versión con el stack frozen** (graphrag-sdk + litellm pueden chocar con openai 2.30.0, google-genai, etc.) ejecutando el resolver real; reportar lo que resuelva, NO forzar pins inventados.

2. **BGE-M3 self-hosted como embedder custom — VALIDACIÓN CRÍTICA.** Decisión confirmada por Jorge: BGE-M3 firme (superior multilingüe para Magna 12-20 idiomas, soberanía de datos en industria regulada, costo cero recurrente, control de versionado para FAT). El PoC usó text-embedding-3-small solo por conveniencia, nunca comparó calidad. Configurar el SDK para usar el cliente BGE-M3 (`app/embeddings/bge_client.py`) vía interfaz ABC del SDK o LiteLLM. Si el SDK NO lo acepta directo, **construir adapter custom** — el modelo NO cambia. Reportar la vía de integración usada.

3. **Config de modelos de ingesta (validada PoC Contrato 4):**
   - Extracción: **Gemini 2.5 Flash** — `gemini/gemini-2.5-flash` vía LiteLLM. Prefijo `gemini/` OBLIGATORIO o LiteLLM defaultea a Vertex AI y falla pidiendo credenciales GCP.
   - QA: **gpt-4o-mini**.
   - Resolution: **Gemini 2.5 Flash (LLMVerifiedResolution)**.
   - Post-proceso: **`deduplicate_entities(fuzzy=True)` OBLIGATORIO** (el Contrato 5 dejó 653 residuos sin dedup por no ejecutarlo). Manejar el async correctamente: el SDK tiene `finalize_sync()` pero NO `deduplicate_entities_sync()` — usar `await`/`asyncio.run`. **Corrige bug PoC #1.** Test de regresión.
   - Forzar idioma español en el prompt de extracción (Gemini alterna ES/EN en descripciones).
   - Variables: `GEMINI_API_KEY` (NO `GOOGLE_API_KEY`), `OPENAI_API_KEY`.
   - Retry con tenacity (ya en deps) para rate limiting de Gemini (1,506 retries en multi-doc del PoC).

4. **Schema DKG (ontología) según doc 01.** Nodos núcleo: `:EntidadOperativa` (con `token_qr`, `tipo`, `cliente_id`, `sitio`, `estado_ciclo_vida`), `:CategoriaEntidad`, `:DocumentoSource` (con `tipo_documento`, `idioma_origen`, `version_documento`, `hash_contenido`), `:DocumentoTraducido` (con `idioma_destino`, `origen_ingesta`, `tier_servicio`, vinculación uno-a-muchos), `:Especificacion`, `:TerminoTecnico`, `:FormaLinguistica`. Nodos por tipo de intención (se completan en B7 pero el schema base aquí): `:Procedimiento`/`:Paso`/`:EPP`/`:Herramienta`/`:Advertencia`, `:RecursoVisual`/`:Etiqueta`/`:LeyendaSimbolica`, `:RecursoVideo`/`:Capitulo`/`:Subtitulo`/`:Transcripcion`, `:ArbolDiagnostico`/`:NodoDecision`/`:CausaProbable`/`:AccionResolutoria`, `:EventoOperativo`/`:CertificadoVigencia`/`:Observacion`/`:MedicionRegistrada`, `:Alerta`/`:ReglaAlerta`, `:Norma`/`:RequisitoNormativo`, `:Tenant`.

5. **Multi-tenancy efectiva** por `graph_name`↔`tenant_id`. Toda query/mutación con tenant implícito. Helper de scope. Aislamiento verificable (regla inviolable).

6. **Versionado in-place** (decisión #11): aristas `:VERSION_HISTORICA`/`:VersionAnterior`. Default on documentos/procedimientos/glosarios/entidades operativas; default off términos individuales. Trazabilidad con timestamp.

7. **Fachada sobre el SDK:** evolucionar `app/graph/falkor_client.py` a `app/graph/docyan_graph.py` (fachada GraphRAG-SDK + Cypher directo para casos no cubiertos).

8. **Retiro controlado de DII:** marcar `@deprecated`. NO eliminar (B5 podría necesitarlo hasta su cierre). Migrar datos de tablas Supabase `documents`/`entities` al grafo si los hay; entorno limpio = nada que migrar.

9. **Sistema de esquemas — COMPONENTE CENTRAL.** Evidencia Contrato 5: schema NOM-052 extrajo 0 relaciones de LGPGIR. NO construir lista parcial. Dos capas:
   - **Catálogo del mercado meta completo:** `app/schemas_documentales/catalogo/` con módulo por tipo (nom, ley, reglamento, iso, manual_tecnico, msds, calibracion, especificacion, ficha_tecnica, memoria_traduccion). Todos presentes, todos ajustables. Ninguno se difiere.
   - **Generador dinámico Gemini 2.5 Flash:** `app/schemas_documentales/generador.py` — analiza documento + contexto de usuario (industria, operación, par lingüístico, tier) y deriva schema cuando no calza con catálogo. `app/schemas_documentales/registry.py` — registro vivo que realimenta el catálogo.
   - Cada schema expone su mapeo a visualización (consumido por B8).

10. **Respaldo FalkorDB (decisión #12):** `scripts/backup_falkordb.sh` / `restore_falkordb.sh` + config Fly.io. RPO 15min, RTO 4h, retención 7 años producción / 3 años operativo.

## Componentes a construir
- `app/graph/docyan_graph.py`, `app/graph/schemas/dkg_ontology.py`, `app/graph/versioning.py`, `app/graph/multitenancy.py`
- `app/llm/litellm_config.py` (prefijos correctos)
- `app/schemas_documentales/catalogo/` (10 módulos), `generador.py`, `registry.py`
- `scripts/backup_falkordb.sh`, `restore_falkordb.sh`

## Tests automatizados requeridos
- Conexión FalkorDB vía SDK (lectura/escritura).
- Embedder BGE-M3 custom: el SDK genera embedding con cliente BGE-M3 local, NO OpenAI.
- Ingesta mínima: documento 1pp → grafo poblado con nodos esperados + provenance (`MENTIONED_IN`).
- Multi-tenant: tenant A y B en `graph_name` distintos, query de A no retorna datos de B.
- Versionado: actualizar nodo crea `:VERSION_HISTORICA` con timestamp.
- Regresión bug PoC: `deduplicate_entities(fuzzy=True)` con await correcto ejecuta y reduce duplicados.
- Catálogo: cada tipo del mercado meta con doc de muestra real → extracción esperada.
- Generador: documento FUERA del catálogo (replica caso LGPGIR) → genera schema y extrae **>0 relaciones**, NO falla con 0.
- Realimentación: schema generado queda en registro y es reutilizable.

## Salida verificable
Schema DKG con multi-tenant y versionado funcional vía GraphRAG-SDK. Documento ingiere con provenance nativo, multi-tenant aislado, versionado registra cambios, BGE-M3 confirmado como embedder activo, generador produce schema y >0 relaciones para documento fuera del catálogo. DII deprecated.

## Notas para Opus sobre integración con código existente
- BGE-M3 client ya existe; reutilizar.
- Skeleton `falkor_client.py` se evoluciona/reemplaza.
- DII NO se elimina aquí, solo deprecated.
- Docling + LlamaIndex ya en deps (stack ingesta multi-formato adenda sección 5); NO eliminar.
- `openai` se queda: gpt-4o-mini es el QA del pipeline (validado PoC). NO es dependencia fantasma.
- torch/transformers ya en deps para BGE-M3; NO eliminar.

## Reglas de ejecución
- No stubs, no mocks (excepto tests), no hardcoded. Alcance completo.
- Si BGE-M3 no integra directo, es adapter, no cambio de modelo, no bloqueador de alcance.
- Conflictos de versión: resolver con el resolver real, reportar, no inventar pins.
- Verdad operacional. PENDIENTE DE JORGE si algo del modelado no resuelto.

**Referencias:** doc 01 (DKG), doc 09 (Multi-tenant), doc 10 (Stack), doc 12 (consumo del grafo), Adenda 2/4/5, REPORTE_CONTRATO4 y 5, REPORTE_V111.
