# Sprint Contract B7 — Clasificador de Intención + Pipelines Tipos 1-8 + Chat persistente

**Producto:** DOCYAN LDE — Live Document Environment by XCID
**Bloque:** B7 | **Ejecutor:** Opus 4.8 vía Claude Code CLI
**Modo:** Una aprobación + ejecución completa + un reporte final.

---

## Prerequisitos
B3 completo (MO necesario para sesiones, ruteo y chat persistente).

## Contexto para Opus
Cada tipo de intención es un patrón estructural de pregunta del consultor. La clasificación la resuelve el Clasificador de Intención invocado por el MO. Cada tipo activa: pipeline de resolución + componente de renderización (UI #1, B8) + adaptación a canal (WhatsApp, B9) + cruces estructurales con otros tipos.

Estado (auditoría): `app/core/intent.py` clasifica tipo de documento y query pero NO implementa los 8 tipos de intención. PARCIAL. El chat persistente aprovecha que GraphRAG-SDK soporta multi-turno nativo (`completion()` con `history`).

## Alcance específico

### Clasificador de Intención (doc 03 + doc 14)
Híbrido: heurístico para casos obvios (palabras clave, estructura de pregunta) + **LLM classifier (Gemini 2.5 Flash para minimizar costo)** cuando heurístico no resuelve con confianza + fallback. Resolución de idioma del operador (Accept-Language o configuración explícita).

### Pipelines de los 8 tipos confirmados MVP v1 (doc 03)

| # | Tipo | Estructura DKG central | Componente (B8) |
|---|------|------------------------|-----------------|
| 1 | Informativa | `:Especificacion` + `:TerminoTecnico` | `<InfoCard/>` |
| 2 | Guía paso a paso | `:Procedimiento` + `:Paso` + `:EPP` + `:Herramienta` + `:Advertencia` | `<ProcedureCard/>` |
| 3 | Gráficos/diagramas | `:RecursoVisual` + `:Etiqueta` + `:LeyendaSimbolica` | `<DiagramViewer/>` con overlay |
| 4 | Video | `:RecursoVideo` + `:Capitulo` + `:Subtitulo` + `:Transcripcion` | `<VideoPlayer/>` |
| 5 | Troubleshooting | `:ArbolDiagnostico` + `:NodoDecision` + `:CausaProbable` + `:AccionResolutoria` | `<DiagnosticTree/>` |
| 6 | Historial | `:EventoOperativo` + `:CertificadoVigencia` + `:Observacion` + `:MedicionRegistrada` | `<TimelineView/>` |
| 7 | Alertas de vencimientos | `:Alerta` + `:ReglaAlerta` + `:AccionSobreAlerta` | `<AlertsDashboard/>` |
| 8 | Comparativa | `:SesionComparativa` + `:DiferenciaDetectada` + `:ReporteComparativo` | `<ComparativeView/>` |

**Detalles de pipeline por tipo (doc 03):**
- **T1:** token QR → entidad → extracción de TerminoTecnico → resolución en DTM (respeta lock) → navegación DKG → match único alto/desambiguación múltiple/flag si seguridad y confianza<umbral → `<InfoCard/>` con valor + unidad + cita (documento+sección+página).
- **T2:** procedimiento con pasos en orden + EPP/Herramientas/Advertencias/Pre-Postcondiciones + especificaciones referenciadas (cruce T1) + modo "ejecutar paso a paso" con confirmación humana registrada en FAT (auditoría IATF 16949).
- **T3:** RecursoVisual + etiquetas con coordenadas + leyenda + traducción de etiquetas (tipo_segmento=etiqueta_diagrama) + split-screen original/traducido + descarga PNG/SVG.
- **T4:** RecursoVideo + subtítulos par activo (o generación vía motor si solo hay transcripción) + capítulos + transcripción consultable.
- **T5:** árbol diagnóstico secuencial interactivo; sesión troubleshooting (TTL 2h); puede invocar T2 (acción=ejecutar_procedimiento) y registrarse como `:EventoOperativo` (cruce T6).
- **T6:** timeline cronológico de eventos/certificados/observaciones/mediciones; base de T7.
- **T7:** alertas de vencimientos vía scheduler APScheduler (B3); jerárquico por urgencia; base en `:CertificadoVigencia` de T6. **(Conecta con alertas administrativas de B8 — línea ABSOLUTA: solo administrativas, nunca clínicas/operativas.)**
- **T8:** sesión comparativa con estrategia por tipo (versiones de documento, normas aplicables); resumen ejecutivo vía LLM; cache 24h; computación asíncrona para comparativas largas.

**Cruces estructurales (doc 03):** implementar la matriz de interdependencias (T5→T2, T2→T1/T3/T4, T3→T1, T6→T7, T7→T2, etc.).

### Chat persistente en contexto (adenda)
Multi-turno con `completion()` + `history` del SDK. Sesión (Session Manager de B3) mantiene historial; consultas siguientes se interpretan con contexto previo; TTL respetado. Cambio de tipo de intención mid-conversación soportado.

### Composición de respuesta
JSON tipado según schemas Pydantic v2 (para renderización condicional en B8 vía tipos generados de OpenAPI).

## Componentes a construir
- `app/intent/clasificador.py` (heurístico + Gemini 2.5 Flash + fallback)
- `app/intent/pipelines/tipo_1.py` a `tipo_8.py` (8 pipelines con sus estructuras DKG)
- `app/intent/cruces.py` (matriz de interdependencias)
- `app/intent/chat_persistente.py` (multi-turno con history del SDK)
- `app/intent/schemas_respuesta.py` (Pydantic v2 por tipo)

## Tests automatizados requeridos
- Clasificador: ≥3 consultas por cada uno de los 8 tipos, clasificadas correctamente; heurístico vs LLM vs fallback.
- Pipeline por tipo (8): cada uno ejecuta con input canónico y retorna estructura esperada.
- Cruces: T5→T2 (acción ejecutar_procedimiento), T2→T1 (verifica especificación), T6→T7 (certificado base de alerta).
- Chat persistente: 3 turnos; turno 3 interpreta referencia a turno 1; cambio de tipo mid-conversación.
- Resolución de idioma: Accept-Language y configuración explícita.

## Salida verificable
Consulta clasifica correctamente y ejecuta el pipeline apropiado, devolviendo respuesta estructurada JSON tipada lista para renderización condicional. Chat multi-turno mantiene contexto. Cruces entre tipos funcionan.

## Notas para Opus sobre integración con código existente
- `intent.py` actual se evoluciona; preservar clasificación de tipo de documento que funciona.
- Chat persistente usa Session Manager de B3 (Redis + spillover); no crear sistema paralelo.
- Pipelines consultan grafo vía `docyan_graph.py` de B1.
- Clasificador usa LiteLLM config de B1 (Gemini 2.5 Flash).
- T7 alertas usa APScheduler de B3 y conecta con safety_validator de B8.
- Prerequisito de B8 (la UI consume estos pipelines y el chat).

## Reglas de ejecución
- No stubs, no mocks (excepto tests), no hardcoded. Los 8 pipelines completos con sus estructuras DKG y cruces.
- Verdad operacional. PENDIENTE DE JORGE si modelado no resuelto.

**Referencias:** doc 03 (Catálogo Tipos 1-8 con pipelines, estructuras DKG, componentes, cruces), doc 05 (MO/Intent Router), doc 14 (B7, clasificador híbrido Gemini Flash), Adenda (chat persistente).
