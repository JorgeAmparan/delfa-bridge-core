# Sprint Contract B10 — UI #2 Revisión Lingüística

**Producto:** DOCYAN LDE — Live Document Environment by XCID
**Bloque:** B10 | **Ejecutor:** Opus 4.8 vía Claude Code CLI
**Modo:** Una aprobación + ejecución completa + un reporte final.

---

## Prerequisitos
B0 (scaffolding frontend), B4 (motor produce output revisable), B6 (governance/audit). Paralelo con B8.

## Contexto para Opus
UI #2: revisor humano valida traducciones. Una sola UI #2 con modos por rol (decisión cerrada, NO tres UIs). El rol Traductor humano está ELIMINADO; los humanos son revisores. Revisión humana en producción = gobernanza central para Tier 2/3 Pista A. DOCYAN provee la interfaz, no los revisores (excepto contratación externa por proyecto Tier 2/3). **Solo Pista A** (en Pista B la revisión la hizo la agencia en su CAT tool).

Estado: UI #2 ausente.

## Alcance específico (doc 04 + doc 12)

1. **SPA Next.js + shadcn/ui** (desktop, NO PWA).

2. **Vista del documento traducido completo** como flujo principal (NO segmento a segmento como CAT tools) + **vista alterna bilingüe segmento a segmento** bajo demanda.

3. **Panel detalle por segmento:**
   - Origen de propuesta (match exacto / fuzzy con % / glosario / LLM nuevo).
   - Score de confianza (de B4, pesos 30/20/20/15/15).
   - Justificación de la propuesta.
   - Match DTM utilizado cuando aplica.

4. **Acciones por segmento:** validar / editar / rechazar / comentar. Cada acción → `:RegistroRevision` + registro en FAT (B6).

5. **Propagación automática** de ediciones a repeticiones internas (Fase 3 del motor) + **des-propagación manual** cuando el revisor quiere editar solo una instancia.

6. **Lock terminológico visible:** segmentos lockeados marcados, sugerencias bloqueadas visibles. Anulación de lock por revisor con justificación (R-LT-03 de B6, registrada en FAT).

7. **Modos por rol (doc 09):**
   - AUDITOR (revisor agencia/DOCYAN): flujo estándar.
   - AUDITOR EXTERNO (revisor cliente Tier 3): flujo de aprobación final + objeciones.
   - Resolución de conflictos entre AUDITOR y AUDITOR EXTERNO.

8. **Función "pedir otra propuesta IA"** (re-traducción de segmento específico vía motor B4).

9. **react-i18next. Tipos TS desde OpenAPI.**

## Componentes a construir
- `frontend/src/app/(revision)/...`
- `frontend/src/components/review/document_view.tsx`, `bilingual_view.tsx`, `segment_panel.tsx`, `role_modes.tsx`, `conflict_resolution.tsx`
- Backend: `app/api/routers/review.py`

## Tests automatizados requeridos
- Render de vista documento completo + vista bilingüe.
- E2E: revisor agencia valida/edita/rechaza/comenta; cambios persistidos + `:RegistroRevision` + FAT.
- Propagación: editar primaria propaga a repeticiones; des-propagación individual.
- Lock visible: segmento lockeado marcado, no editable sin anulación justificada.
- Modo por rol: AUDITOR vs AUDITOR EXTERNO con permisos correctos; resolución de conflicto.
- "Pedir otra propuesta IA": re-traducción de segmento.

## Salida verificable
Revisor humano valida documento traducido completo, edita segmentos con propagación a repeticiones, lock terminológico se respeta visualmente, acciones registradas en FAT, modos por rol con permisos correctos, conflictos AUDITOR/AUDITOR EXTERNO resueltos.

## Notas para Opus sobre integración con código existente
- Scaffolding frontend de B0.
- Motor (B4) produce output con scoring y razonamiento que esta UI muestra.
- Lock terminológico (B2) determina segmentos no editables.
- Cada acción registra en FAT (B6).
- Roles según doc 09 (AUDITOR, AUDITOR EXTERNO).
- Tipos TS del OpenAPI (B0).

## Reglas de ejecución
- No stubs, no mocks (excepto tests), no hardcoded. Vista completa + bilingüe + modos por rol + propagación + lock visible, completos.
- Testing balanceado incluye frontend.
- Verdad operacional. PENDIENTE DE JORGE si modelado no resuelto.

**Referencias:** doc 04 (UI #2), doc 12 (motor, scoring, repeticiones, lock), doc 09 (roles AUDITOR/AUDITOR EXTERNO).
