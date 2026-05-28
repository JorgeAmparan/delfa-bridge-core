# Sprint Contract B4 — Motor de Traducción Rigurosa (Pista A) + 3 tiers

**Producto:** DOCYAN LDE — Live Document Environment by XCID
**Bloque:** B4 | **Ejecutor:** Opus 4.8 vía Claude Code CLI
**Modo:** Una aprobación + ejecución completa + un reporte final.

---

## Prerequisitos
B2, B3 completos. Paralelo con B5.

## Contexto para Opus
Corazón de Pista A (laboratorios ISO 17025, maquiladoras IMMEX corredor T-MEC). **DOCYAN no es CAT tool.** Es motor de traducción gobernado que produce traducción rigurosa completa y la entrega a revisor humano (Tier 2/3) o agente revisor IA (Tier 1).

**Decisión categórica del fundador (doc 12):** "DOCYAN juega el papel del traductor experimentado, aprovecha lo que hay en la TM y en el corpus terminológico para traducir." El motor NO traduce de cero cuando hay traducción aprobada en DTM. Aprovecha matches 100%, repeticiones y fuzzies aprovechables. Solo invoca LLM para huecos reales y para ajustar fuzzies tomando el match como referencia.

El rol Traductor humano está ELIMINADO; el motor ocupa esa función. Humanos son revisores. Modelos de traducción: Claude Sonnet 4.6 + Gemini 2.5 Pro vía MR, tier medio piloto (sin cambio — el cambio de modelos de la adenda es solo para ingesta). Estado: motor ausente.

## Alcance específico

### Pipeline de 6 fases (doc 12)

**Fase 1 — Normalización:** documento source (PDF/DOCX/XLSX/HTML/otros) → extracción de estructura semántica (párrafos, tablas, listas, headers, notas, numeraciones, refs cruzadas, recursos visuales/video) + preservación de metadatos de formato + detección de tipo/dominio/marco regulatorio + identificación de entidades operativas (vínculo DKG). (El pipeline de ingesta GraphRAG-SDK de B1 alimenta esto.)

**Fase 2 — Segmentación:** división en unidades traducibles, cada una clasificada por `tipo_segmento` (23 tipos de B2), con contexto operacional (documento, sección, página, dominio, criticidad inferida) + detección de elementos no traducibles (códigos de norma, números de artículo, fórmulas químicas, unidades SI, marcas, números de figura).

**Fase 3 — Repeticiones internas:** detección de segmentos idénticos intra-documento. Primera ocurrencia = primaria, resto = repeticiones vinculadas. Revisor edita primaria → propaga; des-propagación individual posible (UI #2).

**Fase 4 — Match DTM Cliente:** búsqueda en DTM cliente del par activo. Bandas: 100% exacto / 95-99% nearly exact / 85-94% high fuzzy / 75-84% medium fuzzy / 50-74% low fuzzy / 0-49% no match (umbral mínimo 50%). Si no hay DTM cliente del par (primer documento): "sin DTM disponible" → Fase 5.

**Fase 5 — Match corpus terminológico DOCYAN + glosario cliente:** corpus terminológico multi-dominio de fuentes públicas (IATE, IEC Electropedia, ISO public, NIST, ASTM). Identificación de equivalencias técnicas validadas. Aplicación de glosario cliente con lock si activo (lock se impone en Fase 6).

**Fase 6 — Traducción LLM con grafos. TABLA ORIGEN→ACCIÓN EXACTA:**

| Origen | Acción |
|--------|--------|
| 100% match DTM cliente | Usar tal cual. **NO invocar LLM.** |
| Repetición interna | Usar traducción de la primaria. **NO invocar LLM.** |
| 95-99% nearly exact | Ajustes automáticos (tags, números, puntuación). **LLM NO se invoca.** |
| 85-94% high fuzzy | LLM con prompt especializado, match fuzzy como referencia, ajusta diferencia mínima. |
| 75-84% medium fuzzy | LLM con prompt especializado, match como referencia, atención a palabras divergentes. |
| 50-74% low fuzzy | LLM con prompt especializado, match como referencia tentativa. |
| 0-49% no match | LLM con prompt completo: contexto operacional + glosarios + corpus + tipo_segmento. Traducción nueva. |

**Conflictos terminológicos:** el motor NO decide autónomamente. Registra todas las opciones en `:SegmentoTraduccion` y las presenta al revisor (Tier 2/3) en UI #2. En Tier 1 sin revisor: prioridad automática DTM cliente > glosario cliente > corpus DOCYAN > LLM nuevo, registrada en FAT con justificación.

**Lock terminológico (Fase 6):** si glosario cliente `lock_terminologico=true` y LLM se desvía → reemplazo automático por término cliente + `:SugerenciaTermino` estado reportada_al_cliente. (Función técnica de B2, activada aquí.)

**Sin QA interno automático** (decisión fundador): output va directo al revisor. No hay segunda pasada del LLM. Hay scoring de confianza para priorizar atención del revisor, pero el motor no rechaza ni reprocesa sus propuestas.

### Prompts especializados por los 23 tipos de segmento (doc 12)
Estructura común (10 elementos: rol, par lingüístico, tipo de segmento, contexto operacional, match de referencia, términos+equivalencias, lock activo, no-traducibles, restricciones del tipo, output JSON con texto+scoring+términos no encontrados+candidatos a glosario). Restricciones por tipo: `especificacion` preserva valores/unidades SI; `instruccion_paso` imperativo + números de paso; `advertencia` ANSI Z535/ISO 3864 + tono por nivel; `etiqueta_diagrama` longitud para `{x,y,w,h}`; `subtitulo` CPS + ≤42 char/línea; `mensaje_alerta` preserva `{variable}`; `requisito_normativo` preserva refs normativas + distingue shall/must/deberá vs should/may/se recomienda; (y los 23 completos del doc 12).

### Scoring por segmento — pesos exactos (doc 12)
`score_calidad` (0-1): 30% confianza LLM + 20% ajuste glosario + 20% ajuste DTM (% del match aprovechado, 0 si nuevo) + 15% validación reglas tipo_segmento + 15% validación cross-segmento. NO es freno automático (score bajo va igual al revisor). <0.85 marcado "prioridad de revisión" en UI #2. Tier 1: <0.75 dispara flag al cliente con disclaimer.

### Reconstrucción de formato original (doc 12)
PDF (weasyprint/reportlab), DOCX (python-docx), XLSX (openpyxl), HTML (lxml/beautifulsoup), texto plano (directo), imagen (OCR+overlay traducido), video (subtítulos VTT/SRT). Subcomponente Reconstructor de Formato. Registra en FAT ajustes no triviales (longitud español +20-30% vs inglés puede requerir reposicionar etiquetas).

### 3 tiers de servicio (doc 12)
- **Tier 1** (informativos no técnicos): motor + agente revisor IA, sin humano. Disclaimer de nivel de gobernanza.
- **Tier 2** (técnicos/legales): motor + revisor humano externo especializado (contratado por proyecto).
- **Tier 3** (alta criticidad regulatoria): motor + revisor externo + revisor interno del cliente.
Tier asignado por documento, no por cliente.

### Routing por MR
Claude Sonnet 4.6 + Gemini 2.5 Pro, tier medio piloto. Ruteo por criticidad presente pero desactivado.

## Componentes a construir
- `app/translation/motor_traduccion.py` (6 fases)
- `app/translation/segmentador.py` (23 tipos)
- `app/translation/prompts/` (por tipo de segmento)
- `app/translation/scoring.py` (pesos 30/20/20/15/15)
- `app/translation/reconstructor_formato.py` (por formato)
- `app/translation/tiers.py` (Tier 1/2/3)
- Integra `litellm_config.py` (B1), `mr.py` (existente), `lock_terminologico.py` + `fuzzy_matching.py` + `tm_dual.py` (B2)

## Tests automatizados requeridos
- Las 6 fases en orden con documento corto.
- Tabla origen→acción: 100%/repetición/95-99% NO invocan LLM; 85-94%/75-84%/50-74%/0-49% sí, con comportamiento esperado.
- Lock activo: traducción que viola lock → reemplazo + registro.
- Conflicto terminológico: opciones registradas para revisor (Tier 2/3) / prioridad automática (Tier 1).
- Scoring: segmento crítico vs informativo con scores distintos; pesos correctos.
- Reconstrucción: documento Word entra → Word traducido con layout; PDF→PDF; XLSX→XLSX.
- 3 tiers: Tier 1 sin humano con disclaimer, Tier 2/3 con flag a revisor.
- Routing MR: tier medio recibe la traducción.

## Salida verificable
Documento source EN → es-MX completo, formato original preservado, scoring por segmento, lock respetado, matches aprovechados sin invocar LLM donde no corresponde, 3 tiers operando.

## Notas para Opus sobre integración con código existente
- Lock, fuzzy, TM dual ya en B2; aquí se activan en el flujo.
- MR existente se invoca, no se reconstruye.
- Docling ya en deps para conversión de formato.
- Retrieval del grafo vía fachada `docyan_graph.py` de B1.
- Reconstrucción usa python-docx/openpyxl/weasyprint/lxml (verificar en deps; agregar weasyprint o reportlab si falta).

## Reglas de ejecución
- No stubs, no mocks (excepto tests), no hardcoded. Alcance completo: las 6 fases, los 23 tipos de segmento, los 3 tiers, todos los formatos de reconstrucción.
- Verdad operacional. PENDIENTE DE JORGE si modelado no resuelto.

**Referencias:** doc 12 (Motor completo: 6 fases, tabla origen→acción, 23 tipos, scoring, reconstrucción, 3 tiers), doc 07 (gobernanza), doc 02 (DTM), doc 00 (alcance Pista A).
