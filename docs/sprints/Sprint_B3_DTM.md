# Sprint Contract B2 — DTM + segregación estricta + TM dual + lock terminológico

**Producto:** DOCYAN LDE — Live Document Environment by XCID
**Bloque:** B2 | **Ejecutor:** Opus 4.8 vía Claude Code CLI
**Modo:** Una aprobación + ejecución completa + un reporte final.

---

## Prerequisitos
B1 completo (GraphRAG-SDK integrado, schema DKG, multi-tenancy, versionado, BGE-M3 confirmado).

## Contexto para Opus
El DTM (Document Translation Memory, antes PTM) NO es TM tradicional plana. Es grafo ontológico de equivalencias técnicas con contexto operacional + sugerencia activa de términos no genéricos (doc 02). Vive sobre el mismo motor (FalkorDB vía GraphRAG-SDK) que el DKG. El lock terminológico es el diferenciador defendible vs CAT tools (Trados/MemoQ/Phrase/XTM/SmartCAT): función técnica, no instrucción verbal.

Estado: DTM ausente. Sin segregación, sin TM dual, sin lock, sin matching fuzzy.

## Alcance específico

1. **Schema DTM según doc 02.** Nodos:
   - `:SegmentoTraduccion` (texto_origen/destino, idioma_origen/destino BCP-47, contexto, dominio, cliente_id, aprobado_por, score_calidad, uso_contador, version_glosario, **`tipo_segmento`** enum de 23 valores).
   - `:Glosario` (tipo_glosario, par_linguistico, version, `lock_terminologico` bool).
   - `:TerminoGlosario` (texto_origen/destino, definicion, dominio, prioridad).
   - `:RegistroRevision` (revisor_id, `rol_revisor` enum traductor/revisor_agencia/revisor_cliente, accion aprobar/editar/rechazar/comentar, texto_anterior/nuevo).
   - `:SugerenciaTermino` (texto_origen/destino_sugerido, dominio_inferido, frecuencia_aparicion, `estado` propuesta/aceptada/rechazada/reportada_al_cliente).

2. **Los 23 tipos de segmento:** narrativa, especificacion, instruccion_paso, advertencia, etiqueta_diagrama, leyenda_simbolica, subtitulo, transcripcion, nodo_diagnostico_pregunta, nodo_diagnostico_respuesta_etiqueta, causa_probable, accion_resolutoria, descripcion_evento, observacion_descripcion, accion_correctiva, mensaje_alerta, consecuencia_no_accion, accion_recomendada_alerta, resumen_ejecutivo_comparativo, descripcion_diferencia, accion_sugerida_comparativa, requisito_normativo, modulo_formativo_contenido.

3. **Segregación estricta por par lingüístico.** Cada par direccional soberano en su propio `graph_name`/sub-grafo. **Sin cruce entre pares.** Sin sugerencias de vecindad. 5 pares día 1: en-US↔es-MX, en-US↔es-US, en-US↔es-ES, en-UK↔es-MX, en-UK↔es-ES. Agnóstico al idioma: nuevos pares como configuración.

4. **TM dual con prioridad cliente** (orden de búsqueda del doc 02): 1) match exacto TM cliente del par activo → 2) match parcial ≥75% TM cliente → 3) TM agencia → 4) generar nuevo. En Pista A análogo con DTM Local (planta) > DTM Corporativa (grupo).

5. **Lock terminológico como función técnica.** Si glosario cliente tiene `lock_terminologico=true` y el LLM propone término que se desvía: el motor **reemplaza automáticamente** por el término del cliente y registra `:SugerenciaTermino` con `estado=reportada_al_cliente`. NO se aplica la desviación aunque sea "más correcta". Anulación manual solo por revisor con justificación (registrada en FAT). Constraint generator + validator.

6. **Matching fuzzy híbrido (decisión #2):** Levenshtein (pasada léxica) + BGE-M3 (pasada vectorial). Score 70/30 bandas altas, 30/70 bandas bajas. Umbral mínimo léxico ≥30% para invocar vectorial. Tabulador: 100% / 95-99% / 85-94% / 75-84% / 50-74% / 0-49%. Umbral mínimo fuzzy 50%.

7. **Aristas DTM y cross DKG↔DTM** (doc 02): `:PERTENECE_A_PROYECTO`, `:RECIBIO_REVISION`, `:CONTIENE_TERMINO`, `:USA_GLOSARIO`, `:USA_TERMINO_GLOSARIO`, `:CANDIDATA_PARA_GLOSARIO`; cross: `:TRADUCIDA_VIA` (de `:Especificacion`/`:Paso`/`:Advertencia`/etc. a `:SegmentoTraduccion`), `:TRADUCIDO_DESDE` (subtítulos/transcripciones).

8. **Exportación a formatos CAT** (doc 02): TMX 1.4 / XLIFF 2.0 / TBX, preservando pares + metadata (`x-docyan-cliente`, `x-docyan-tipo`, `x-docyan-dominio`). Documentar qué se pierde (aristas ontológicas, lock, sugerencias EDB).

9. **Sugerencias del EDB activo** como `:SugerenciaTermino` con estados, para enriquecer glosario localizado del cliente.

## Componentes a construir
- `app/graph/schemas/dtm_ontology.py`
- `app/graph/dtm_segregation.py` (graph_name por par)
- `app/translation/tm_dual.py` (prioridad cliente)
- `app/translation/lock_terminologico.py` (constraint + validator)
- `app/translation/fuzzy_matching.py` (Levenshtein + BGE-M3, umbrales Paso C)
- `app/translation/cat_export.py` (TMX/XLIFF/TBX)

## Tests automatizados requeridos
- Segregación: par en-US↔es-MX y en-US↔es-ES aislados; query en uno no retorna del otro.
- TM dual: match en ambas TMs → retorna cliente; orden exacto/parcial≥75%/agencia/nuevo.
- Lock: output que viola lock → reemplazo automático + `:SugerenciaTermino` estado reportada_al_cliente.
- Anulación de lock: revisor con justificación → permite + registra en FAT.
- Matching híbrido: 6 casos cubriendo cada banda del tabulador.
- Umbral léxico: input <30% similitud léxica no invoca pasada vectorial.
- Exportación TMX: roundtrip preserva pares + metadata.

## Salida verificable
DTM persiste segmentos con par lingüístico, segregación demostrada, TM dual respeta prioridad cliente, lock rechaza violaciones técnicamente, fuzzy híbrido opera en las 6 bandas, exportación TMX funcional.

## Notas para Opus sobre integración con código existente
- DTM sobre la misma fachada `docyan_graph.py` de B1.
- Lock se construye aquí; se activa en el flujo en B4.
- Fuzzy se usa en consulta DTM y en `deduplicate_entities`; mantener coherencia.
- BGE-M3 de B1 para la pasada vectorial.

## Reglas de ejecución
- No stubs, no mocks (excepto tests), no hardcoded. Alcance completo.
- Verdad operacional. PENDIENTE DE JORGE si modelado no resuelto.

**Referencias:** doc 02 (DTM), doc 12 (interfaces con motor), doc 07 (reglas sobre lock — F1), Adenda 2/5.
