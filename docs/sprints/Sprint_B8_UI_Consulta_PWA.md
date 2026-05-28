# Sprint Contract B8 — UI #1 Consulta Operativa PWA + Visualizaciones + Anotaciones + Alertas

**Producto:** DOCYAN LDE — Live Document Environment by XCID
**Bloque:** B8 | **Ejecutor:** Opus 4.8 vía Claude Code CLI
**Modo:** Una aprobación + ejecución completa + un reporte final.

---

## Prerequisitos
B0 (scaffolding frontend), B7 (pipelines + chat), B6 (governance/audit). Paralelo con B10.

## Contexto para Opus
Cara del producto al operador: UI #1 Consulta Operativa como PWA (doc 04). Interfaz simple (no dashboard sofisticado), renderización condicional desde día 1 (texto plano sin renderización anula el diferenciador). El mismo QR físico funciona en N idiomas (Magna: es-MX en Saltillo, en-US en Detroit, zh-CN en Wuhan).

Integra 4 componentes nuevos de la adenda: visualizaciones por tipo de documento, chat persistente (B7), anotaciones, alertas administrativas con línea ABSOLUTA.

**LÍNEA DE SEGURIDAD ABSOLUTA (adenda 9):** alertas SOLO administrativas (vencimientos, faltantes, fechas de calibración, documentos por expirar), NUNCA clínicas/operativas. Una alerta que sugiera decisión clínica entra en SaMD (COFEPRIS/FDA, mala praxis). Se codifica como `safety_validator` rechazante, NO como nota en docs. Requisito legal con cobertura de tests crítica.

Estado: solo existe `app/demo/index.html` (portal admin ~900 líneas). NO es PWA. Scaffolding Next.js viene de B0.

## Alcance específico

1. **PWA Next.js 15 en Vercel.** Landing del QR (doc 04):
   - Información de la entidad operativa (máquina, sitio, documentos asociados).
   - **Resolución de idioma del operador:** prioridad 1 configuración usuario auth, 2 Accept-Language, 3 selector explícito, default idioma del sitio, fallback a idioma cercano disponible con disclaimer.
   - Selector de canal (PWA vs WhatsApp) según política del tenant (algunos sitios prohíben WhatsApp).

2. **8 componentes de renderización condicional (doc 04 + doc 03):**
   - `<InfoCard/>` (T1): encabezado + valor + unidad + cita (documento+sección+página) + feedback.
   - `<ProcedureCard/>` (T2): encabezado + EPP (iconos+norma) + herramientas + precondiciones + advertencias (banners ISO 3864) + pasos numerados (con verbo, tiempo, advertencias inline, checkbox confirmación, especificación verificada con cita) + postcondiciones + cita. Modo "ejecutar paso a paso" (un paso, confirmación, registro FAT) + modo "vista completa".
   - `<DiagramViewer/>` (T3): imagen + overlay etiquetas con coordenadas + toggle original/traducido + leyenda + navegación a componentes + descarga PNG/SVG.
   - `<VideoPlayer/>` (T4): player + selector de pistas + capítulos + transcripción consultable.
   - `<DiagnosticTree/>` (T5): árbol diagnóstico interactivo secuencial.
   - `<TimelineView/>` (T6): historial cronológico.
   - `<AlertsDashboard/>` (T7): alertas jerárquico por urgencia.
   - `<ComparativeView/>` (T8): diff visual estrategia-específica.

3. **Visualizaciones por tipo de documento** (adenda): cada tipo (NOM, MSDS, calibración, manual técnico, ficha técnica, etc.) tiene visualización dedicada. Consume el mapeo tipo→visualización del sistema de esquemas de B1 (catálogo + generador). Tipos generados dinámicamente reciben visualización derivada/genérica hasta curarse.

4. **Chat persistente** (consume B7 `chat_persistente.py`): conversación multi-turno integrada en la UI.

5. **Anotaciones vinculadas** (adenda): notas del usuario vinculadas a entidades/operaciones/documentos. **Capa complementaria, NO sistema de registro primario.** Supabase, vinculadas por entity_id.

6. **Alertas administrativas con `safety_validator`** (adenda 9, LÍNEA ABSOLUTA): vencimientos, faltantes, fechas de calibración, documentos por expirar. `app/alerts/safety_validator.py` rechaza cualquier alerta cuyo contenido sugiera decisión clínica/operativa (verbos imperativos clínicos/operativos). Conecta con T7 (B7) y scheduler (B3).

7. **Pedigree clickeable:** renderización del provenance nativo del SDK (`MENTIONED_IN`/`PART_OF`/`NEXT_CHUNK` + spans). Click → fuente exacta (chunk → documento).

8. **Service worker PWA + offline parcial. Captura de feedback (útil/no útil/comentario) por consulta. react-i18next** con idiomas activos del tenant. **Tipos TS desde OpenAPI** (pipeline B0).

## Componentes a construir
Frontend:
- `frontend/src/app/(consulta)/...`
- `frontend/src/components/render/InfoCard.tsx`, `ProcedureCard.tsx`, `DiagramViewer.tsx`, `VideoPlayer.tsx`, `DiagnosticTree.tsx`, `TimelineView.tsx`, `AlertsDashboard.tsx`, `ComparativeView.tsx`
- `frontend/src/components/visualizations/` (por tipo de documento)
- `frontend/src/components/chat/`, `annotations/`, `alerts/`, `pedigree/`
- `frontend/public/manifest.json` + service worker

Backend:
- `app/api/routers/annotations.py`, `alerts.py`
- `app/alerts/safety_validator.py` (LÍNEA ABSOLUTA)

## Tests automatizados requeridos
- Frontend: cada componente de renderización con Vitest + React Testing Library.
- Frontend E2E (Playwright): operador consulta → respuesta renderizada por tipo (al menos T1, T2, T5).
- Frontend E2E: chat multi-turno; anotación creada visible en re-visita; visualización por tipo de documento.
- Frontend E2E: pedigree clickeable lleva a fuente.
- Backend: `safety_validator` rechaza ≥10 casos de alertas clínicas/operativas.
- Backend: `safety_validator` acepta ≥10 casos de alertas administrativas válidas.
- E2E: alerta de vencimiento se genera y se muestra; resolución de idioma (3 idiomas distintos para mismo QR).

## Salida verificable
Operador escanea QR, consulta en su idioma, recibe respuesta renderizada por tipo de intención, ve visualización por tipo de documento, anota, ve alertas administrativas válidas, el validador bloquea cualquier alerta clínica/operativa, pedigree clickeable funcional.

## Notas para Opus sobre integración con código existente
- Scaffolding frontend de B0 (Next.js 15 + React 19 + Tailwind + shadcn/ui + react-i18next).
- Pipelines de intención y chat de B7; consumir vía API.
- Visualizaciones conectan con sistema de esquemas de B1 (catálogo + generador).
- Pedigree usa provenance nativo del SDK (B1).
- Tipos TS generados del OpenAPI (B0); usar generados, no escribir a mano.
- `app/demo/index.html` NO es la PWA; puede mantenerse como portal admin separado o retirarse.
- `safety_validator` es requisito legal; cobertura de tests crítica.

## Reglas de ejecución
- No stubs, no mocks (excepto tests), no hardcoded. Los 8 componentes, visualizaciones, chat, anotaciones, alertas, pedigree, completos.
- Testing balanceado incluye frontend (decisión #14).
- Línea de seguridad de alertas ABSOLUTA: ante duda, el validador rechaza por defecto.
- Verdad operacional. PENDIENTE DE JORGE si modelado no resuelto.

**Referencias:** doc 04 (UIs, componentes detallados), doc 03 (tipos + pipelines), Adenda 6/7/9.
