# Sprint Contract B12 — UI #4 Onboarding (3 modalidades, 12 pasos)

**Producto:** DOCYAN LDE — Live Document Environment by XCID
**Bloque:** B12 | **Ejecutor:** Opus 4.8 vía Claude Code CLI
**Modo:** Una aprobación + ejecución completa + un reporte final.

---

## Prerequisitos
B11 (e indirectamente B1, B2, B3, B6, B7, B8, B10 — el onboarding integra capacidad de todos: activa un cliente que usará todo).

## Contexto para Opus
UI #4: wizard de onboarding. Flujo arquitectónico de MVP v1 (decisión cerrada, no diferido). Es lo que permite activar un cliente piloto en producción con sus propios documentos. Iniciado por evento de venta, ejecutado como flujo procedural (doc 06).

Estado: UI #4 ausente.

## Alcance específico (doc 06)

### 3 modalidades
- **Modalidad A:** cliente final industrial directo (Pista A).
- **Modalidad B:** agencia (Pista B, simplificada — sin Motor de Traducción, sin UI #2, sin glosarios de producción, sin tabulador; solo tenant agencia + pares + PMs como TITULAR + canales + fallback de idioma).
- **Modalidad C:** sub-tenant cliente final gestionado por agencia (con DTM cliente prioridad sobre agencia, lock, AUDITOR EXTERNO si aplica, tier Base/Profesional/Enterprise).

### 12 pasos del wizard (Modalidad A; B y C son variaciones)
1. Identificación del cliente (datos legales, sector, jurisdicción) → crea `:Tenant` estado `onboarding_en_curso` + selecciona `:PlantillaOnboarding` por sector.
2. Selección de modalidad y tier.
3. Configuración de pares lingüísticos activos.
4. Carga inicial de entidades operativas + categorización + **generación de tokens QR** por entidad.
5. Carga inicial de documentos source (pipeline de ingesta GraphRAG-SDK de B1 + cotizador de B3).
6. Carga inicial de glosarios cliente (CSV/TBX) o decisión de construir orgánicamente.
7. Configuración de lock terminológico.
8. Configuración de usuarios y roles (PM=TITULAR, AUDITOR, AUDITOR EXTERNO si Tier 3).
9. **Configuración OBLIGATORIA de criticidad por tipo de documento (decisión #15).** Cliente puede delegar a inferencia automática del pipeline si no quiere configurar manualmente. NO se puede avanzar sin configurar o delegar.
10. Configuración de reglas GRG personalizadas (opcional, default usa configuración DOCYAN por sector — `:ConfiguracionGRG` de B6).
11. Validación funcional con demo end-to-end usando 1 documento real del cliente.
12. Activación del tenant (estado → `activo`, credenciales finales, scheduler de alertas arranca, notificación a comercial para facturación).

### Capacidades del wizard
- Wizard secuencial con estado por paso + progreso visual.
- Sidebar de ayuda contextual (explicaciones por paso, mejores prácticas del sector, plantillas).
- **Chat de soporte directo con responsable DOCYAN** durante el wizard (crítico MVP v1, acompañamiento alto).
- **Pausa y reanudación** (sesiones Onboarding TTL 30 días, Session Manager B3).
- Generación de **QRs físicos para imprimir** (PDF descargable con QRs vinculados a entidades — usa qr_generator de B3).
- Vista de auditoría del progreso (log en FAT).

## Componentes a construir
- `frontend/src/app/(onboarding)/...`
- `frontend/src/components/onboarding/wizard.tsx`, `step_panels.tsx` (12), `help_sidebar.tsx`, `support_chat.tsx`, `qr_print.tsx`
- Backend: `app/api/routers/onboarding.py`, `app/onboarding/activation.py`, `app/onboarding/plantillas.py`

## Tests automatizados requeridos
- E2E: completar wizard Modalidad A end-to-end con cliente simulado (12 pasos).
- E2E: Modalidad B (agencia simplificada) y Modalidad C (sub-tenant).
- Cada paso genera el efecto persistente esperado (tenant, entidades+QR, documentos ingeridos, glosarios, roles, criticidad, GRG, activación).
- Paso 9: no se puede avanzar sin configurar criticidad o delegar.
- Pausa/reanudación: TTL 30 días respetado.
- QRs físicos: PDF descargable con QRs válidos.
- Activación: estado `activo`, scheduler arranca, evento `tenant_activado` en FAT.

## Salida verificable
Cliente nuevo completa onboarding (12 pasos) en cualquier modalidad y queda activo en producción, con QRs físicos generados, criticidad configurada o delegada, validación end-to-end con documento real superada.

## Notas para Opus sobre integración con código existente
- Scaffolding frontend de B0.
- Carga de documentos (paso 5) usa pipeline de ingesta (B1) + cotizador (B3).
- Lock (paso 7) usa función de B2.
- Criticidad (paso 9) integra con inferencia del pipeline (decisión #15).
- Reglas GRG (paso 10) usan `:ConfiguracionGRG` de B6.
- QRs físicos usan qr_generator de B3.
- Chat de soporte puede reutilizar chat persistente de B7/B8.
- Sesiones Onboarding usan Session Manager de B3 (TTL 30 días).
- Roles (paso 8) según doc 09.

## Reglas de ejecución
- No stubs, no mocks (excepto tests), no hardcoded. Las 3 modalidades, los 12 pasos, completos.
- Testing balanceado incluye frontend (E2E del flujo completo).
- Verdad operacional. PENDIENTE DE JORGE si modelado no resuelto.

**Referencias:** doc 06 (Onboarding, 3 modalidades, 12 pasos, pipeline de resolución), doc 09 (multi-tenant, roles), doc 04 (UI #4).
