# CLAUDE.md — Panohayan DLE™ by XCID

> **Archivo de contexto operativo para Claude Code CLI (Opus 4.7).**
> Este archivo se lee al inicio de cada sesión. NO es documentación arquitectónica — para eso existen los Sprint Contracts y los docs 00-14 que Jorge pega en cada sesión cuando aplica. Este archivo es **cómo trabajar en este repo**.

---

## 1. Producto

**Panohayan DLE™ — Document Localization Engine — by XCID**
Empresa: XCID SA de CV. Fundador: Jorge Luis Amparán Hernández.

Panohayan DLE™ es la marca propia; XCID es la empresa matriz; XCID Inside es el motor invisible. En código y en assets visibles al usuario final usar **Panohayan DLE™**. En código interno (clases, paquetes, módulos) usar `panohayan_dle` o `panohayan` según contexto.

**NO es una herramienta CAT.** Es una capa de gobernanza lingüística + documento vivo consultable vía QR + IA con renderización condicional por tipo de intención.

**Dos pistas comerciales paralelas** (no secuenciales):

- **Pista A** — México industrial directo: laboratorios ISO 17025, maquiladoras IMMEX corredor T-MEC. Motor de Traducción Rigurosa de 6 fases.
- **Pista B** — Internacional vía agencias profesionales: ingesta bilingüe (TMX/XLIFF/etc.) + alineamiento Vecalign+Hunalign + consulta multilingüe. **Sin motor de traducción**.

---

## 2. Cómo trabajar en este repo

### 2.1. Un Sprint = una aprobación + ejecución completa + un reporte

El flujo es:

1. Jorge pega un Sprint Contract en CLI.
2. Tú (Opus) ejecutas el Sprint Contract **completo**, sin pedir confirmaciones intermedias.
3. Generas **un reporte final** al terminar.
4. Jorge revisa el reporte y aprueba el siguiente sprint.

**NO** iteres en multi-fases dentro del mismo sprint. **NO** preguntes "¿quieres que continúe?" entre componentes del mismo bloque. Si encuentras un bloqueador real, lo documentas en el reporte y sigues con lo que sí puedes ejecutar.

### 2.2. Verdad operacional sobre proyección optimista

Lo aprendiste por las malas en el repo previo (auditoría 25 abril 2026: reportaste "tests pasando" cuando había cero tests). Esto **no se repite**.

En cada reporte final:

- ✅ "X funciona, verificado con test Y que pasa con output Z" → afirmación válida.
- ❌ "X debería funcionar" → afirmación inválida. Verifica o no lo digas.
- ❌ "Pendiente de prueba con datos reales" usado como muletilla para no testear → inválido.

Si algo no se ejecutó, dilo explícito. Si algo se ejecutó parcialmente, di qué parte sí y qué parte no. Si encontraste un bloqueador, di cuál es con detalle técnico.

### 2.3. Tests automatizados desde día 1

**Decisión cerrada (Paso C #14)**: testing balanceado 60-70% backend / 40-50% frontend, GitHub Actions en CI.

- Backend: `pytest` con `pytest-asyncio` + `httpx.AsyncClient` para tests de FastAPI.
- Frontend: `Vitest` (unit) + `Playwright` (E2E).
- **Sin tests = sprint no terminado.** No reportes "completado" si no hay tests escritos y pasando para el componente nuevo.
- Cobertura objetivo ≥75% en módulos nuevos.

### 2.4. Disciplina de contratos backend↔frontend

- Backend: schemas Pydantic v2 estrictos exportan OpenAPI 3.1.
- Frontend: tipos TypeScript generados con `openapi-typescript` desde el OpenAPI del backend.
- **Regenerar tipos cada vez que backend cambia** — automatizar en CI antes del build del frontend.
- No hardcodear tipos en frontend; siempre desde el contrato.

### 2.5. Multi-tenant strict

Cada query a FalkorDB, Supabase o Redis lleva `tenant_id` resuelto del usuario logueado. Helper `tenant_scoped_query` en B1.

Tests E2E deben verificar que no hay leaks entre tenants. Esta es regla inviolable, no opcional.

### 2.6. PENDIENTE DE JORGE

Cuando encuentres algo no resuelto en el modelado o en el Sprint Contract:

- Marca explícitamente como `PENDIENTE DE JORGE` en el reporte.
- **No inventes la respuesta.** No tomes decisiones de modelado o arquitectura por tu cuenta.
- Sigue ejecutando lo demás que sí puedes.
- En el reporte: lista todos los PENDIENTE DE JORGE en orden de criticidad.

### 2.7. Decisiones cerradas que NO se re-validan

Las 15 decisiones del Paso C están cerradas. **No vuelvas a abrirlas.** Si un Sprint Contract menciona una decisión, asume que está tomada.

Si genuinamente crees que una decisión está mal y tienes argumento técnico concreto: lo escribes en el reporte como "Observación técnica para Jorge" — pero **ejecutas igual** lo que dice el Sprint Contract. La decisión de cambiar es de Jorge, no tuya.

---

## 3. Stack técnico (cerrado, no negociable)

### Backend
- Python 3.11
- FastAPI + Pydantic v2
- httpx + asyncio + uvicorn
- Gestión de dependencias: `uv` (o `pip` con `pyproject.toml`)

### Bases de datos
- **FalkorDB**: PKG (Panohayan Knowledge Graph) + PTM (Panohayan Translation Memory). Self-hosted en Fly.io.
- **Supabase (PostgreSQL)**: operacional + FAT spillover + auth.
- **pgvector**: embeddings (extensión Supabase).
- **Redis**: sesiones MO + scheduler backend APScheduler. Self-hosted en Fly.io.

### LLMs (vía Model Router existente — 4 tiers)
- Claude Sonnet 4.6
- Gemini 2.5 Pro
- **Tier medio piloto para todo.** Ruteo por criticidad presente pero desactivado hasta primer cliente.

### Embeddings
- **BGE-M3 self-hosted** desde día 1. NO OpenAI text-embedding.

### Matching fuzzy
- Híbrido Levenshtein + BGE-M3 dos pasadas.
- Score 70/30 bandas altas, 30/70 bandas bajas.
- Umbral mínimo léxico ≥30% para invocar vectorial.
- Tabulador estándar industria: 100% / 95-99% / 85-94% / 75-84% / 50-74% / 0-49%.

### Alineadores Pista B
- **Vecalign primario + Hunalign fallback.** Ambos día 1.

### Frontend
- TypeScript estricto
- Next.js 15 App Router + React 19
- Tailwind CSS
- shadcn/ui sobre Radix Primitives
- react-i18next (independiente del framework)

### Hosting
- **Fly.io**: backend + FalkorDB + Redis.
- **Vercel**: frontend (las 4 UIs).

### WhatsApp
- **360dialog directo** (BSP único, sin Twilio). Decisión #8.

### Scheduler
- **APScheduler con backend Redis.** Decisión #3.

---

## 4. Glosario canónico (memoriza, no inventes)

| Sigla | Significado | Notas |
|---|---|---|
| **PKG** | Panohayan Knowledge Graph | Sobre FalkorDB. Multi-tenant strict. |
| **PTM** | Panohayan Translation Memory | Sobre FalkorDB. Segregación estricta por par lingüístico. **No es TM tradicional.** |
| **DLE** | Document Localization Engine | El producto completo. |
| **MO** | Master Orchestrator | Pieza central. Doc 05. |
| **DII** | Document Ingestion Intelligence | Existe 1,759 líneas en repo. NO reescribir. |
| **EDB** | Entity Data **Brain** | Almacén **activo** que propone. **NO** "Entity Database". |
| **GRG** | Guardrail Governance | Existe 307 líneas. Extendido en doc 07. |
| **FAT** | Foundation Audit Trail | Existe 196 líneas. Extendido en doc 08. |
| **MR** | Model Router | Existe 135 líneas. 4 tiers. |
| **RI** | Resilient Infrastructure | — |
| **CAT** | Computer-Aided Translation | **Referencia comparativa, NO stack de Panohayan.** Trados/MemoQ/Phrase/XTM/SmartCAT. |

### Cosas eliminadas (no las uses)

- ❌ **Kiuey**: alucinación de Gemini en exploración inicial. Cualquier referencia a Kiuey en código o docs es bug, debe limpiarse.
- ❌ **Rol "Traductor humano"**: ELIMINADO del modelo de roles. El Motor de Traducción ocupa esa función. Los humanos en el flujo son **revisores**, no traductores.
- ❌ **"TM tradicional"**: Panohayan PTM es grafo ontológico, no una TM convencional. No la trates como una.
- ❌ **"Entity Database"**: es Entity Data **Brain**. Almacén activo.

---

## 5. Las 15 decisiones del Paso C (cerradas — referencia rápida)

| # | Decisión | Compromiso |
|---|---|---|
| 1 | Embeddings | BGE-M3 self-hosted desde día 1 |
| 2 | Matching fuzzy | Híbrido Levenshtein + BGE-M3, score 70/30 altas, 30/70 bajas, umbral léxico ≥30% |
| 3 | Scheduler | APScheduler + Redis |
| 4 | Alineador Pista B | Vecalign primario + Hunalign fallback |
| 5 | i18n UI | react-i18next |
| 6 | Sesiones MO | Redis con TTL diferenciado + spillover Supabase para completadas |
| 7a | Hosting backend | Fly.io |
| 7b | Hosting frontend | Vercel |
| 8 | WhatsApp BSP | 360dialog directo, sin markup |
| 9 | Framework frontend | Next.js 15 App Router + React 19 + Tailwind |
| 10 | Componentes UI | shadcn/ui sobre Radix Primitives |
| 11 | Versionado PKG | In-place + aristas `:VERSION_HISTORICA` |
| 12 | Backup FalkorDB | RPO 15min, RTO 4h, retención 7 años producción / 3 años operativo |
| 13 | Pricing | Mantener precios actuales hasta primer cliente real |
| 14 | Testing | Balanceado 60-70% backend / 40-50% frontend, CI GitHub Actions |
| 15 | Criticidad por segmento | OBLIGATORIA en Onboarding Step 9, delegable a "DII infiere automática" |

---

## 6. Plan de 14 bloques (Paso D)

| # | Bloque | Salida verificable |
|---|---|---|
| B0 | Fundación + migración | Repo en Fly.io + Vercel, tests pasando en CI |
| B1 | PKG | Schema FalkorDB multi-tenant + versionado |
| B2 | PTM | Schema PTM + segregación por par + TM dual + lock |
| B3 | MO + Tokens QR | QR escaneable resuelve a contexto |
| B4 | Motor Traducción Rigurosa (Pista A) | Doc traducido en formato original con scoring |
| B5 | Ingesta Bilingüe (Pista B) | Agencia carga TMX/XLIFF, ingiere correctamente |
| B6 | GRG + FAT extendidos | Reglas + cadena criptográfica + reportes |
| B7 | Clasificador Intención + Pipelines 1-8 | Consulta clasifica y ejecuta pipeline correcto |
| B8 | UI #1 Consulta Operativa PWA | Operador consulta vía PWA con renderización condicional |
| B9 | WhatsApp + Channel Adapter | Operador consulta vía WhatsApp en su idioma |
| B10 | UI #2 Revisión Lingüística | Revisor humano valida documento completo |
| B11 | UI #3 PM Dashboard | PM gestiona proyectos, asigna revisores, cotiza |
| B12 | UI #4 Onboarding | Cliente nuevo completa onboarding y queda activo |
| B13 | Tipos 9-11 potenciales + Hardening | Producto vendible primer cliente, monitoreado |

Paralelismos posibles: B4↔B5, B6 paralelo a B4/B5, B8↔B10.

---

## 7. Estructura del repo

```
/
├── apps/
│   ├── consulta/             # UI #1 PWA (B8)
│   ├── reviewer/             # UI #2 Revisión Lingüística (B10)
│   ├── pm-dashboard/         # UI #3 PM Dashboard (B11)
│   └── onboarding/           # UI #4 Onboarding Wizard (B12)
├── panohayan/                # Backend Python (paquete principal)
│   ├── dii/                  # Document Ingestion Intelligence (existente)
│   ├── edb/                  # Entity Data Brain (existente)
│   ├── grg/                  # Guardrail Governance (existente, extendido en B6)
│   ├── fat/                  # Foundation Audit Trail (existente, extendido en B6)
│   ├── mr/                   # Model Router (existente)
│   ├── ri/                   # Resilient Infrastructure (existente)
│   ├── pkg/                  # PKG client (B1)
│   ├── ptm/                  # PTM client (B2)
│   ├── mo/                   # Master Orchestrator (B3)
│   ├── pipelines/            # Pipelines por intent type (B4, B5, B7)
│   ├── channels/             # Channel adapters (B9: WhatsApp)
│   └── api/                  # FastAPI routers
├── scripts/                  # Utilidades operativas
├── docs/                     # Documentación interna del repo (runbooks, etc.)
├── tests/                    # Tests backend (pytest)
├── .github/workflows/        # GitHub Actions CI
├── Dockerfile                # Backend container
├── fly.toml                  # Fly.io config
├── pyproject.toml            # Deps Python
└── CLAUDE.md                 # Este archivo
```

---

## 8. Convenciones de código

### Python
- Type hints obligatorios en funciones públicas.
- Pydantic v2 para schemas de API.
- `async`/`await` por default en handlers FastAPI.
- Docstrings en español o inglés (consistente por módulo).
- `ruff` + `black` configurados; formatear antes de commit.
- Variables de entorno via `pydantic-settings`.

### TypeScript
- `strict: true` en tsconfig.
- Tipos generados desde OpenAPI, no hardcoded.
- Componentes React con tipos de props explícitos.
- `eslint` + `prettier` configurados.
- Estado global: Zustand o Jotai cuando aplique (no Redux).

### Commits
- Conventional commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`.
- Referenciar bloque cuando aplique: `feat(B2): add PTM segment versioning`.

### Branches
- `main`: producción.
- `develop` o feature branches por sprint: `sprint/B2-ptm`.

---

## 9. Variables de entorno principales

Documentadas en `.env.example`. Las críticas:

```
# Auth
JWT_SECRET=<random 64+ chars>
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# Databases
FALKORDB_HOST=
FALKORDB_PORT=
REDIS_URL=

# LLMs (vía Model Router)
ANTHROPIC_API_KEY=
GOOGLE_AI_API_KEY=

# Embeddings (BGE-M3 self-hosted)
BGE_M3_ENDPOINT=

# WhatsApp
WA_360DIALOG_API_KEY=
WA_360DIALOG_WEBHOOK_SECRET=

# Sentry (B13)
SENTRY_DSN=

# CORS
ALLOWED_ORIGINS=https://consulta.panohayan.com,https://reviewer.panohayan.com,...
```

**NO commitear secrets.** `gitleaks` corre en CI.

---

## 10. Política de auditoría / FAT

Cada acción significativa en el sistema dispara un evento FAT (Foundation Audit Trail) con SHA-256 hash chain.

9 familias de eventos (definidas en B6):
- `consulta` — consultas operativas.
- `revision` — acciones del revisor lingüístico.
- `ingesta` — carga de documentos / pares Pista B.
- `governance` — cambios de configuración GRG, lock, etc.
- `troubleshooting` — sesiones Tipo 5.
- `alertas` — disparos de Tipo 7.
- `onboarding` — flujo de UI #4.
- `system` — operaciones internas (webhook failures, scheduler runs).
- `auth` — login, logout, password reset.

**No agregues eventos fuera de estas familias sin justificación documentada.**

Retención (Decisión #12):
- 7 años: producción, revisión, ingesta, governance.
- 5 años: onboarding.
- 3 años: consulta, troubleshooting, alertas.
- 2 años: system.

---

## 11. Marco regulatorio que el producto satisface

NOM-018-STPS-2015, NOM-026-STPS-2008, LFT Art. 132, NOM-035-STPS-2018, IATF 16949, AS9100, ISO 17025, FDA, EU Organic.

**No es requisito que conozcas estas normas al detalle**, pero sí que entiendas que el producto **opera en industrias reguladas** y por eso:

- Compliance ≠ nice-to-have. La cadena hash de FAT es regulatoria, no opcional.
- Lock terminológico ≠ feature cosmética. Es diferenciador defendible vs CAT tools.
- Multi-tenant strict ≠ paranoia. Es contractual con clientes regulados.

---

## 12. Contexto comercial — REGLA OPERATIVA INVIOLABLE

**SIN MENSAJES A CONTACTOS COMERCIALES HASTA QUE EL PRODUCTO SEA DEMO-ABLE.**

Vender un producto que no existe quema relaciones reales. No generes contenido tipo "email de pitch", "propuesta comercial", "mensaje de outreach" para contactos reales hasta que Jorge lo solicite explícitamente con producto en mano.

Contactos referidos en project knowledge (NO acción):
- México: Laboratorio Estándar, Daniel Calderón (Intermex Juárez), Elías Chacón (T-Hub), Sergio León.
- Internacional: Hafida Santoudy (NY), Sonia (Octagon Madrid, contacto Magna International).

---

## 13. Cuando algo se rompa

Orden de escalamiento:

1. **Diagnóstico real**: lee logs, ejecuta tests, inspecciona estado real. **NO supongas.**
2. **Verdad operacional**: si está roto, di que está roto. No "debería funcionar después de reiniciar".
3. **Documenta en el reporte**: bloqueador específico, intento de solución, qué se necesita para resolver.
4. **NO bloquees todo el sprint por un componente**: continúa con lo demás que sí puedes ejecutar.
5. **Si requiere decisión de Jorge**: marca `PENDIENTE DE JORGE` con detalle técnico suficiente para que decida sin tener que investigar.

---

## 14. Identidad del proyecto

- **Empresa**: XCID SA de CV
- **Producto**: Panohayan DLE™
- **Fundador**: Jorge Luis Amparán Hernández (25 años en corredor industrial T-MEC + industria traducción profesional internacional)
- **Su corrección sobre flujos operativos es ley operativa, no opinable.**

Si Jorge contradice algo en este CLAUDE.md, **gana Jorge**. Este archivo es una guía, no un dogma.

---

## 15. Fuentes de verdad

Por orden de prioridad cuando algo entra en conflicto:

1. **Mensaje directo de Jorge en la sesión actual.**
2. **Sprint Contract activo** (lo que Jorge pega al inicio de la sesión).
3. **Docs 00-14 del modelado arquitectónico** (en project knowledge de Jorge, pegados cuando aplica).
4. **Este CLAUDE.md.**
5. **Estado actual del código en main.**

Cuando hay conflicto entre 3 y 5 (modelado vs código existente): seguir el modelado. El código existente del repo previo (`delfa-bridge-core` migrado) tiene deuda técnica que se está limpiando bloque por bloque.

---

*XCID SA de CV — Panohayan DLE™ by XCID — Mayo 2026 — Confidencial.*
