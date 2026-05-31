# Sprint Contract B13 — Tipos 9-11 + Hardening final

**Producto:** DOCYAN LDE — Live Document Environment by XCID
**Bloque:** B13 | **Ejecutor:** Opus 4.8 vía Claude Code CLI
**Modo:** Una aprobación + ejecución completa + un reporte final.

---

## Prerequisitos
B7, B8 completos (e idealmente el resto del MVP para el hardening final).

## Contexto para Opus
Último bloque: tipos de intención adicionales (según necesidad del primer cliente) + hardening obligatorio para producción real. Cierra la deuda técnica de las auditorías (abril y mayo 2026) y deja el producto vendible.

## Alcance específico

### Tipos de intención adicionales (doc 03)
Componentes y estructuras DKG:
- **Tipo 9 — Cumplimiento normativo** (`:Norma` + `:RequisitoNormativo` + `:EvaluacionCumplimiento` → `<ComplianceView/>`). Alto valor para labs ISO 17025 y agencias en industria regulada. **Probable SÍ en MVP v1.** Pipeline: norma + scope → requisitos aplicables → cruce con datos del cliente (documentos/eventos/procedimientos/certificados) → `:EvaluacionCumplimiento` por requisito → estado de cumplimiento + evidencias + gaps + acciones correctivas + modo "reporte de auditoría" exportable. Ingesta especializada de normas: detección de cláusulas + obligatoriedad (shall/must/deberá vs should/may/se recomienda) + interpretación operativa vía LLM tier alto + flag a Revisor regulatorio. Corpus de normas públicas compartible entre clientes; DTM/glosarios privados.
- **Tipo 10 — Cadena causal** (`:RelacionCausal` + `:CadenaImpacto` + `:NodoImpacto` → `<ImpactChain/>` navegable). Navegación profunda de grafo (varios saltos), propagación, razonamiento causal. Profundidad configurable (default 3 saltos). Ejecución asíncrona para análisis amplios. Ingesta de relaciones causales: inferencia DII + carga manual por experto (UI #3) + aprendizaje desde historial.
- **Tipo 11 — Capacitación contextual** (`:ModuloFormativo` + `:UnidadAprendizaje` + `:RegistroAprendizaje` → `<LearningExperience/>`). Multi-modal adaptativo al nivel del consultor. Cruce con NOM-035-STPS y capacitación obligatoria con vigencia (genera alertas Tipo 7).

**Decisión de cuáles implementar:** depende del primer cliente real. T9 probable sí (alto valor). T10/T11 según necesidad. Si no hay cliente definido al ejecutar, implementar T9 completo y marcar T10/T11 como PENDIENTE DE JORGE con su modelado listo. (Esto NO es recorte: el modelado de los 3 está completo en doc 03; la activación depende de necesidad real del cliente, criterio del propio modelado.)

### Hardening obligatorio (doc 14)
- **Rate limiting en API.**
- **Migraciones formales consolidadas y versionadas** (no schema management externo).
- **Observabilidad:** Sentry / Datadog / nativo Fly.io (decisión operativa dentro del sprint, una variable a la vez).
- **Documentación de API para clientes:** OpenAPI exportada + Swagger UI.
- **Plantillas multilingües en 360dialog** para idiomas activos del primer cliente (completa lo de B9).
- **Optimización Dockerfile:** evaluar PyTorch CPU-only. **Importante:** BGE-M3 self-hosted necesita torch; eliminar solo si BGE-M3 corre como servicio separado del contenedor principal. NO eliminar a ciegas. Revisar el `sed` frágil del Dockerfile (auditoría abril).
- **Verificación de seguridad final:** no secrets en código (gitleaks en CI), CORS por dominio, JWT robusto, confirmar correcciones de auditoría abril (`sql.py:38`, defaults inseguros).
- **Eliminación definitiva de DII** si tras B5 nada lo usa (estuvo deprecated desde B1).

## Componentes a construir
- `app/intent/pipelines/tipo_9.py` (y 10, 11 según activación)
- `frontend/src/components/render/ComplianceView.tsx` (y ImpactChain, LearningExperience según activación)
- Rate limiter (middleware FastAPI)
- Observabilidad (integración elegida)
- Swagger UI expuesto
- Consolidación de migraciones

## Tests automatizados requeridos
- Rate limit: exceder límite → 429.
- CORS: origen no autorizado rechazado.
- JWT robusto: token manipulado rechazado.
- Seguridad: `grep` confirma 0 secrets hardcodeados; gitleaks en CI verde.
- Tipo 9 (si se implementa): consulta de cumplimiento → `:EvaluacionCumplimiento` con estado + gaps.
- Tipos 10/11 si se implementan: tests por pipeline.

## Salida verificable
Producto vendible primer cliente: monitoreado (observabilidad activa), documentado (Swagger UI), seguro (sin secrets, CORS por dominio, JWT robusto, rate limiting), con tipos de intención adicionales según necesidad real. DII eliminado si ya nada lo usa.

## Notas para Opus sobre integración con código existente
- Deuda de seguridad de auditoría abril: confirmar qué sigue presente tras B0 y cerrarlo.
- `railway.toml` ya eliminado en B0; confirmar.
- DII deprecated desde B1; si tras B5 nada lo usa, eliminar definitivamente.
- BGE-M3 necesita torch; NO eliminar torch sin confirmar que BGE-M3 corre separado.
- Tipos de intención usan clasificador e infraestructura de pipelines de B7.

## Reglas de ejecución
- No stubs, no mocks (excepto tests), no hardcoded. Hardening completo.
- Una variable a la vez en decisiones técnicas (ej. observabilidad).
- T10/T11 condicionales por necesidad de cliente (criterio del modelado), no por recorte.
- Verdad operacional. PENDIENTE DE JORGE para decisión de activación de tipos o decisión de cliente.

**Referencias:** doc 03 (Tipos 9-11 con pipelines), doc 10 (Stack), doc 14 (B13, hardening).
