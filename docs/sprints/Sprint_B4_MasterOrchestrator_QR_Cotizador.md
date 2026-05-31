# Sprint Contract B3 — Master Orchestrator + Tokens QR + Cotizador pre-ingesta

**Producto:** DOCYAN LDE — Live Document Environment by XCID
**Bloque:** B3 | **Ejecutor:** Opus 4.8 vía Claude Code CLI
**Modo:** Una aprobación + ejecución completa + un reporte final.

---

## Prerequisitos
B1 completo. B2 puede estar en paralelo (B3 requiere el grafo de B1; consume DTM de B2 al conectar).

## Contexto para Opus
El MO es la pieza central del MVP (doc 05): fachada del sistema hacia el exterior. Todo request (API, webhook WhatsApp, evento de conector, acción de UI, tarea programada) termina invocando al MO. El `DocyanOrchestrator` actual (129 LOC, coordinación CLI) NO es el MO del plan; este sprint lo construye completo.

GraphRAG-SDK absorbe la orquestación interna de ingesta. El MO orquesta el negocio. El cotizador pre-ingesta es CRÍTICO (adenda 8): el PoC topó hard cap de Google a MXN 119 en incidente controlado.

Estado: Redis skeleton 38 LOC sin uso. Sin APScheduler, sin sesiones MO, sin QR, sin cotizador (tiktoken ya en deps).

## Alcance específico

1. **MO con las 10 responsabilidades del doc 05:**
   1. Resolución de contexto del request (identidad, tenant, par lingüístico, canal, variante regional jerárquica usuario>cliente>default>neutro, permisos, sesión).
   2. Clasificación y ruteo (consulta→clasificador→pipeline tipo; producción→motor; revisión→UI#2; configuración→onboarding; conector→ingesta; programada→alertas/reportes).
   3. Coordinación de pipelines (invoca ingesta SDK, DKG, motor, gobernanza, compositor, adaptador de canal, FAT).
   4. Gestión de estado de sesiones.
   5. Aplicación de gobernanza centralizada (Governance Gate).
   6. Resolución de variante regional y localización.
   7. Adaptación a canal (PWA rica / WhatsApp degradado graceful).
   8. Ejecución del scheduler proactivo.
   9. Registro auditable en FAT.
   10. Gestión de errores y degradación graceful (retry, fallback vía MR, degradación, escalación a humano, comunicación honesta — nunca enmascarar falla como éxito).

2. **6 sub-componentes:** Context Resolver, Intent Router (interfaz al clasificador de B7), Pipeline Coordinator, Session Manager, Governance Gate (interfaz al GRG, completo en B6), Scheduler.

3. **Tokens QR persistentes:** generación vinculada a `:EntidadOperativa` (`token_qr`) + `tenant_id` + firma. Endpoint público de resolución contextual (token → entidad → documentos asociados, con `tenant_id` correcto). Resolución roundtrip.

4. **Session Manager Redis con TTLs exactos (decisión #6, doc 14):**
   - Consulta operativa: **30 minutos sliding**.
   - Troubleshooting: **2 horas sliding**.
   - Revisión: **8 horas sliding**.
   - Onboarding: **30 días sliding**.
   - Spillover a Supabase para sesiones completadas.
   - Operaciones: crear, obtener, actualizar, **transferir entre canales** (WhatsApp↔PWA preservando estado), cerrar.

5. **APScheduler backend Redis (decisión #3):** tareas por tenant — evaluación de vencimientos (Tipo 7: diario default + cada 6h críticas), evaluación de patrones EDB, limpieza de sesiones expiradas (cada hora), mantenimiento de índices vectoriales, reportes periódicos a PMs (semanal), sincronización con conectores (MVP v2). Único punto de programación temporal.

6. **Governance Gate:** invoca GRG antes de servir. Verificación de permisos, confianza (scoring por segmento), criticidad, freno de alucinación si confianza<umbral, lock cliente, revisión humana según criticidad, escalación, bloqueo+notificación. (GRG completo en B6; aquí el gate que lo invoca, integrando con el GRG actual de 252 LOC mientras tanto.)

7. **Cotizador pre-ingesta tiktoken (CRÍTICO, adenda 8):** antes de cualquier ingesta al grafo:
   - Mide tokens con tiktoken.
   - Estima costo (extracción Gemini Flash + QA gpt-4o-mini). Baselines PoC: NOM 32pp ~$0.036, Ley 61pp ~$0.046, corpus 50 normas+10 leyes ~$2.26.
   - **Verifica presupuesto disponible del tenant** (no solo estima).
   - Contempla **tiempo** además de costo (Gemini Flash 642s + rate limiting: 1,506 retries en multi-doc).
   - Muestra estimación + pide confirmación. Sin confirmación, no ingiere.
   - Operacionaliza el Token Budget por plan. Protección: saldo prepagado finito sin auto-recharge + hard cap + cotizador.

## Componentes a construir
- `app/orchestrator/master_orchestrator.py` (absorbe/reemplaza `app/main.py` actual)
- `app/orchestrator/context_resolver.py`, `intent_router.py`, `pipeline_coordinator.py`, `session_manager.py`, `governance_gate.py`, `scheduler.py`
- `app/qr/qr_generator.py`, `qr_resolver.py`
- `app/ingesta/cotizador.py`

## Tests automatizados requeridos
- Sesión MO: crear/transición/cerrar; transferencia WhatsApp↔PWA preservando estado.
- Session Manager: TTLs exactos (30min/2h/8h/30d), spillover a Supabase al completar.
- Scheduler: tarea programada ejecuta en tiempo simulado; limpieza de sesiones expiradas.
- Governance Gate: output con violación bloqueado, limpio servido.
- QR: generación + resolución roundtrip, validación de firma, rechazo de QR de otro tenant.
- Cotizador: documento conocido → estimación esperada (baselines PoC); rechazo si presupuesto insuficiente; confirmación requerida antes de ingerir; estimación de tiempo incluida.

## Salida verificable
QR escaneable resuelve a contexto de entidad operativa. MO orquesta sesión completa con transición de canal. Cotizador rechaza ingestas sobre presupuesto y confirma las viables (costo + tiempo). Scheduler ejecuta tareas por tenant con TTLs correctos.

## Notas para Opus sobre integración con código existente
- Redis skeleton (`app/cache/redis_client.py`) se evoluciona para Session Manager + APScheduler backend; no recrear.
- MR existente (98 LOC, 4 tiers, con tests) se mantiene; el MO lo invoca para fallback (responsabilidad 10).
- GRG actual (252 LOC) se invoca desde Governance Gate; extensión completa en B6.
- QR vincula a entidades del grafo de B1; usar fachada `docyan_graph.py`.
- El cotizador de B3 (ingesta) es distinto del cotizador pre-venta de traducción (B11). No confundir.

## Reglas de ejecución
- No stubs, no mocks (excepto tests), no hardcoded. Alcance completo.
- Verdad operacional. PENDIENTE DE JORGE si modelado no resuelto.

**Referencias:** doc 05 (MO, 10 responsabilidades + 6 sub-componentes), doc 14 (TTLs exactos), Adenda 2/8, REPORTE_CONTRATO5 (baselines + rate limiting).
