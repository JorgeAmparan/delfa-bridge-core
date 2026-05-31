# Sprint Contract B11 — UI #3 PM Dashboard + Cotizador pre-venta

**Producto:** DOCYAN LDE — Live Document Environment by XCID
**Bloque:** B11 | **Ejecutor:** Opus 4.8 vía Claude Code CLI
**Modo:** Una aprobación + ejecución completa + un reporte final.

---

## Prerequisitos
B4, B5, B10 completos.

## Contexto para Opus
UI #3: PM gestiona proyectos, asigna revisores, configura clientes, cotiza. Interfaz simple, no dashboard sofisticado (decisión cerrada).

**Cotizador pre-venta de traducción ≠ cotizador pre-ingesta de B3.** El de B3 mide tokens tiktoken antes de ingerir al grafo (costo de LLM de ingesta). El de B11 estima un proyecto de traducción corriendo DII/pipeline + matching contra DTM **SIN invocar LLM** (sin costo), devolviendo volumen por banda fuzzy + costo proyectado. Herramienta comercial de pre-venta.

Estado: UI #3 ausente.

## Alcance específico (doc 14 + doc 04)

1. **Dashboard Next.js + shadcn/ui.**

2. **Vista de proyectos activos:**
   - Pista A: proyectos de producción de traducción.
   - Pista B: proyectos de ingesta bilingüe + sub-tenants cliente final.

3. **Módulo de Cotización pre-proyecto (pre-venta):**
   - Recibe documentos del prospecto.
   - Corre DII/pipeline + segmentación.
   - Aplica matching contra DTM existente del cliente (si la hay).
   - **NO invoca LLM (sin costo significativo).**
   - Devuelve estimación de volumen por banda fuzzy (100/95-99/85-94/75-84/50-74/0-49) + costo proyectado.

4. **Configuración por proyecto:** par lingüístico, glosario asignado, lock terminológico, DTM activa, tier (1/2/3 Pista A o Base/Profesional/Enterprise Pista B).

5. **Vista FAT del proyecto** (consume B6).

6. **Gestión de reglas GRG por tenant** sin tocar código (`:ConfiguracionGRG` de B6).

7. **Asignación de revisores externos** a proyectos Tier 2/3 (modelo de contratación por proyecto, doc 09).

8. **Configuración de plantillas WhatsApp por idioma** (consume B9).

9. **UI #3 simplificada Pista B:** revisión opcional de pares con score <0.7 del alineador (B5).

## Componentes a construir
- `frontend/src/app/(pm)/...`
- `frontend/src/components/pm/projects.tsx`, `quote_preview.tsx`, `assignments.tsx`, `grg_config.tsx`, `whatsapp_templates.tsx`
- Backend: `app/api/routers/projects.py`, `app/api/routers/quotes_preventa.py`

## Tests automatizados requeridos
- E2E: PM crea proyecto, configura par/glosario/lock/tier, asigna revisor.
- Cotizador pre-venta: documento de muestra → volumen por banda fuzzy + costo proyectado, **sin invocar LLM** (verificar que no hay llamada a LLM).
- Asignación: revisor asignado recibe el proyecto en su UI (B10).
- Config GRG por tenant: cambio de regla sin tocar código se persiste.
- Pista B: par con score <0.7 aparece para revisión opcional.

## Salida verificable
PM gestiona proyectos, asigna revisores, configura clientes, ejecuta cotizaciones de pre-venta sin costo de LLM, gestiona reglas GRG por tenant.

## Notas para Opus sobre integración con código existente
- Scaffolding frontend de B0.
- El cotizador pre-venta NO usa el cotizador de ingesta de B3; es módulo distinto que corre matching sin LLM.
- Métricas DTM del grafo (B2) vía `docyan_graph.py` de B1.
- Alertas (B8) y reportes FAT (B6) se muestran aquí.
- `:ConfiguracionGRG` de B6 se edita aquí.
- Roles (PM=TITULAR, revisor=AUDITOR) según doc 09.
- Tipos TS del OpenAPI (B0).

## Reglas de ejecución
- No stubs, no mocks (excepto tests), no hardcoded.
- El cotizador pre-venta SIN LLM es requisito explícito (test lo verifica).
- Verdad operacional. PENDIENTE DE JORGE si modelado no resuelto.

**Referencias:** doc 04 (UI #3), doc 14 (B11, módulo de cotización sin LLM), doc 07 (config GRG), doc 09 (roles, contratación revisores), doc 13 (Pista B simplificada).
