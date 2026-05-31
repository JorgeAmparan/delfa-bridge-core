# Sprint Contract B5 — Ingesta Bilingüe (Pista B) + Alineadores

**Producto:** DOCYAN LDE — Live Document Environment by XCID
**Bloque:** B5 | **Ejecutor:** Opus 4.8 vía Claude Code CLI
**Modo:** Una aprobación + ejecución completa + un reporte final.

---

## Prerequisitos
B2, B3 completos. Paralelo con B4.

## Contexto para Opus
Pista B = agencias profesionales (B2B2C, USD). **DOCYAN no traduce en Pista B.** La agencia traduce con su stack (Trados/MemoQ/Phrase/XTM/SmartCAT); DOCYAN ingiere los documentos ya traducidos y construye el documento vivo consultable vinculado al QR de la entidad operativa del cliente final.

Caso ancla Magna (doc 13): Octagon traduce un manual a N idiomas → sube source + N traducciones a DOCYAN → DOCYAN alinea como pares bilingües, construye DTM derivada, vincula al QR. El mismo QR físico funciona en 28 plantas con operadores en es-MX, en-US, zh-CN, de-AT, hi-IN, etc.

Estado: ingesta bilingüe ausente. Vecalign, Hunalign, matching fuzzy: ausentes (fuzzy se construye en B2).

## Alcance específico

1. **Parser de formatos CAT — Modo A** (doc 13):
   - TMX (Translation Memory eXchange)
   - XLIFF (XML Localization Interchange File Format)
   - TBX (TermBase eXchange)
   - SDLXLIFF (variante Trados)
   - Bilingual DOCX (formato común agencias)

2. **Alineador automático — Modo B** (decisión #4):
   - **Vecalign primario.**
   - **Hunalign fallback** cuando Vecalign falla.
   - Sistema decide automáticamente según score.
   - Pares con **score < 0.7 flagueados** para revisión manual opcional por PM agencia en UI #3 simplificada.

3. **Modo C (conector CAT):** MVP v2, **NO incluido en este bloque** (esto no es diferir alcance del MVP v1; el modelado lo define explícitamente como v2).

4. **Pipeline de ingesta bilingüe:** Docling (conversión universal) → LlamaIndex (indexación semántica) → GraphRAG-SDK → DTM segregada por par lingüístico (B2).

5. **DTM derivada** con `origen_propuesta=agencia_externa` (NO `panohayan_interno`/`docyan_interno`). `:DocumentoTraducido` con `origen_ingesta=pista_b_ingesta_bilingue_modo_a` o `modo_b`.

6. **Vinculación uno-a-muchos** `:DocumentoSource` → N `:DocumentoTraducido` (Magna 12-20 idiomas; sin límite arquitectónico).

7. **Resolución de idioma del operador** (preparada para consumo en B8/B9).

## Componentes a construir
- `app/ingesta_bilingue/parsers/tmx.py`, `xliff.py`, `tbx.py`, `sdlxliff.py`, `bilingual_docx.py`
- `app/ingesta_bilingue/alineadores/vecalign_runner.py`, `hunalign_runner.py`
- `app/ingesta_bilingue/pipeline.py`
- Instalación de `vecalign` y `hunalign` (binarios/scripts externos; documentar en Dockerfile)

## Tests automatizados requeridos
- Por parser (5): TMX/XLIFF/TBX/SDLXLIFF/Bilingual DOCX de muestra real → segmentos extraídos correctamente.
- Alineación Vecalign: corpus bilingüe simple → alineación esperada.
- Fallback: forzar fallo de Vecalign → Hunalign ejecuta y completa.
- Score <0.7: par flagueado para revisión.
- E2E: agencia carga TMX → DTM segregada por par poblada con `origen_propuesta=agencia_externa`.
- Uno-a-muchos: 1 source + 3 idiomas destino → 3 `:DocumentoTraducido` colgando del mismo source.

## Salida verificable
Agencia carga documento bilingüe en cualquier formato soportado, DOCYAN ingiere y persiste como DTM derivada segregada por par, lista para consulta operativa multilingüe. Alineación con métricas, fallback Hunalign funcional.

## Notas para Opus sobre integración con código existente
- DTM segregado por par (B2) recibe los segmentos; usar `dtm_segregation.py`.
- Docling + LlamaIndex ya en deps.
- Vecalign + Hunalign son externos; documentar instalación en Dockerfile.
- Tras B5, DII puede eliminarse definitivamente si nada lo usa (se cierra en B13).
- Cotizador de B3 aplica a ingesta bilingüe de volúmenes grandes.

## Reglas de ejecución
- No stubs, no mocks (excepto tests), no hardcoded. Los 5 parsers + ambos alineadores, completos.
- Modo C es v2 por modelado, no por recorte.
- Verdad operacional. PENDIENTE DE JORGE si modelado no resuelto.

**Referencias:** doc 13 (Ingesta Bilingüe Pista B, Modos A/B/C, caso Magna), doc 02 (DTM derivada), doc 00 (alcance Pista B).
