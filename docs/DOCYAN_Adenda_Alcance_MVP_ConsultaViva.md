# DOCYAN LDE™ — Adenda de Alcance MVP (Consulta Viva)

**XCID SA de CV — DOCYAN LDE™ by XCID — Mayo 2026**
**Documento de alcance — rige sobre el plan de bloques para la fase de validación**

> Esta adenda fija el **alcance del MVP de validación** de DOCYAN. No modifica
> el modelado arquitectónico cerrado (15 decisiones del Paso C). No elimina
> bloques. Reordena qué se construye encima del modelo en MVP1, dejando los
> bloques de traducción como **capacidad latente activable** cuando el primer
> cliente la pida. Esta adenda rige sobre `Plan_Desarrollo_MVP_DOCYAN_v2_postPoC.md`
> y sobre la sección "MVP demo-able" anterior.

---

## Decisión de alcance

**DOCYAN se valida como herramienta de consulta viva de información documental
en contexto, por tipo, donde se necesita, navegable de lo general a lo
granular.** La traducción rigurosa queda como capacidad latente: el modelo se
construye igual, los pisos de aplicación se construyen cuando un cliente la
solicite explícitamente.

Por qué este reordenamiento es coherente y no contradice nada cerrado:

1. La Visión (`DOCYAN_Vision_Propuesta_de_Valor.md`) ya define que el sustantivo
   es conocimiento vivo (Nivel 1), la traducción es Nivel 2 (complemento), y la
   inteligencia organizacional es Nivel 3 (foso).
2. El Playbook de Consulta (`DOCYAN_Vision_Playbooks_de_Consulta.md`) materializa
   el gancho del Nivel 1 sobre las consultas, no sobre la traducción.
3. La regla de pitch ya dice: entrar por el gancho (Nivel 1), revelar el foso
   (Nivel 3) una vez adentro, presentar la traducción (Nivel 2) como garantía y
   extensión.
4. Mercado de validación elegido por Jorge: "consulta viva con quien sea,
   traducción on-demand". No hay casamiento con Pista A o B.

---

## Lo que entra al MVP de validación

Numeración del plan postPoC (`docs/Plan_Desarrollo_MVP_DOCYAN_v2_postPoC.md`).

| # | Bloque | Por qué entra |
|---|--------|---------------|
| B0 | Fundación, migración, rebrand | Construido. Sin esto nada existe. |
| B0.5 | Cleanup conectores legacy | Construido. |
| B0.6 | Cierre de secrets del backend en producción | Construido (CI verde), pendiente merge a main. |
| B1 | DKG sobre GraphRAG-SDK + sistema de esquemas | Construido. Es el grafo de consulta. |
| B1.5 | Frontend lint hotfix | Construido. |
| B2 | Worker de ingesta + cotizador + librería de schemas | Construido (CI verde), pendiente merge a main. |
| B2.1 | Redis compartido | Construido y desplegado en Fly. |
| B2.2 | Cierre de deploy del worker | Construido (CI verde), pendiente deploy real. |
| B3 | DTM (Translation Memory) — **solo cimientos** | El schema, segregación por par lingüístico, lock terminológico modelado, schema bilingüe. Sin motor de traducción encima. |
| B4 | Master Orchestrator + Tokens QR + Cotizador integrado | El QR escaneable que resuelve a contexto es el diferenciador físico de "consulta donde se necesita". |
| B7 | GRG + FAT extendidos | El pedigree clickeable a fuente y la cadena criptográfica son sustento del Nivel 1 y del Nivel 3. **No es traducción.** |
| B8 | Clasificador Intención + Pipelines de consulta + Chat persistente | La consulta clasificada y servida con contexto. |
| B9 | UI #1 Consulta PWA — render condicional por tipo + navegación general→detalle + anotaciones + alertas administrativas + superficie de Nivel 3 visible | La cara del producto al operador. |
| B10 | WhatsApp + Channel Adapter | Canal alternativo de consulta — encaja en el Nivel 1. |
| B13 | UI #4 Onboarding | Sin onboarding no hay activación de cliente piloto. |

**Mercado de validación:** quien quiera consulta viva — laboratorios, maquiladoras,
agencias que necesiten dar acceso navegable a sus propios manuales internos, etc.
No se restringe a Pista A o B desde la oferta.

---

## Lo que sale del MVP (diferido, no eliminado)

| # | Bloque | Estado |
|---|--------|--------|
| B5 | Motor Traducción Rigurosa (Pista A) | Diferido. Contrato existente queda en `docs/sprints/`. |
| B6 | Ingesta Bilingüe (Pista B) — TMX/XLIFF/TBX/SDLXLIFF/Bilingual DOCX | Diferido. |
| B11 | UI #2 Revisión Lingüística | Diferido. |
| B12 | UI #3 PM Dashboard (gestión de proyectos de traducción) | Diferido. Si se necesita gestión de proyectos no traducción, se evalúa al cierre del MVP. |
| B14 | Tipos 9-11 + Hardening | Diferido a post-validación. Hardening mínimo se incluye en B13 (onboarding) y en deploy de producción del MVP. |

**Disparador único de reactivación:** primer cliente que solicite traducción
rigurosa de un corpus documental. En ese momento se retoman los Sprint Contracts
B5 → B6 → B11 en orden. Sin migraciones, sin retrabajo sobre el modelo: los
cimientos están en B3.

---

## Cimientos de traducción que SE CONSERVAN en MVP

Estos no se difieren — se construyen en B3 aunque no se expongan en UI:

- Schema DTM completo con segregación estricta por par lingüístico.
- TM dual (TM Cliente con prioridad sobre TM Agencia) modelada en el grafo.
- Lock terminológico como propiedad técnica de segmentos/términos, no como UI.
- Estructura bilingüe en el modelo de documentos (para no rehacer migraciones).

Esto protege los tres escenarios previstos por Jorge: cliente que pida
traducción incluida, funnel de marketing de traducción hacia DOCYAN, o
desarrollo a medida sobre el modelo existente.

---

## Camino crítico del backend para MVP

Módulos del backend `app/` que están **en alcance MVP** y deben operar contra
Supabase en producción:

- `app/core/edb.py` — Entity Data Brain (Nivel 3 visible desde MVP1).
- `app/core/grg.py` — Guardrail Governance (sustento de Nivel 1 + 3).
- `app/core/matrix.py` — audit_trail / FAT (pedigree clickeable, cadena
  criptográfica).
- `app/core/ri.py` — Resilient Infrastructure (lee `edb.supabase`).
- `app/api/auth.py` — auth + JWT (ya usa service_role).
- `app/ingesta/budget_manager.py` — cotizador (gate financiero, sin bypass).
- `app/ingesta/document_store.py` — bucket `ingest-tmp` para el worker.
- Módulos de consulta, clasificador de intención, MO, QR, FAT extendido (B4,
  B7, B8) cuando se construyan sobre estos cimientos.

Módulos del backend que están **fuera de alcance MVP** (su refactor a
service_role o su validación de secrets se difiere al sprint donde se necesiten):

- `app/core/dii.py` — código legacy del predecesor; mientras no se ejercite, no
  bloquea. Candidato a eliminación en sprint futuro de limpieza.
- `app/api/billing.py` — Stripe se difiere por decisión cerrada (cobro manual en
  fase piloto). Su refactor a service_role se hace cuando se active Stripe (3-5
  clientes).
- `app/api/governance.py` — si toca rutas de UI #3 PM (que se difiere), se
  difiere su validación de secrets.
- `app/mcp_server` — el servidor MCP no es parte del MVP. Su uso se evalúa en
  hardening.
- Conectores externos legacy no usados.

**Implicación operativa concreta para B0.7** (cambio a service_role): se acota a
los módulos del camino crítico: `edb`, `grg`, `matrix`, `ri`, `budget_manager`,
`document_store`. El resto (`dii`, `billing`, `governance`, `mcp_server`,
conectores) se etiqueta como "fuera de alcance MVP" y su validación de secrets
queda explícitamente diferida hasta su sprint de activación. **No es un
"pendiente no bloqueante" — es alcance declarado.**

---

## Lo que esta adenda NO cambia

- 15 decisiones del Paso C: todas vigentes.
- Stack técnico final: vigente.
- Modelado del grafo PKG/DKG y DTM: vigente, incluyendo elementos de traducción
  que quedan latentes.
- Línea de seguridad regulatoria absoluta (alertas solo administrativas, nunca
  decisiones clínicas u operativas): vigente.
- Regla operativa inviolable de no contactar prospectos hasta producto
  demostrable: vigente.
- Cobro manual en fase piloto: vigente.
- Posicionamiento, jerarquía de tres niveles, regla de pitch: vigente.
- Mercados Pista A y Pista B siguen siendo válidos comercialmente; lo que cambia
  es que la validación inicial no depende de cuál se gane primero.

---

## Plan de ejecución resultante (orden definitivo)

1. Merge de `sprint/B0.6-backend-secrets-closure` a `main`.
2. Sprint **B0.7-acotado** — refactor a `SUPABASE_SERVICE_KEY` solo en los 6
   módulos del camino crítico listados arriba. Etiquetar el resto como fuera de
   MVP. Eliminar `SUPABASE_KEY` (anon) del stack.
3. Jorge corre `flyctl secrets set` con los 2 secrets faltantes del backend
   (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`).
4. Jorge corre `scripts/smoke_test_backend.py` contra producción.
5. Jorge corre el bloque de secrets del worker y `flyctl deploy --app
   docyan-lde-ingest --config worker/fly.toml` (ya verificado con
   `--build-only`).
6. Jorge corre `flyctl machines destroy 7847940f92d508 --app docyan-lde-ingest`
   para eliminar la zombi del primer deploy mal hecho.
7. Jorge aplica las migraciones 008/009 en Supabase.
8. Smoke test del worker (`scripts/smoke_test_ingesta.py`).
9. Merge unificado de B2 + B2.1 + B2.2 + B0.7 a `main`.
10. Generación de los siguientes Sprint Contracts del MVP en orden: B3
    (cimientos DTM solamente) → B4 (MO + QR + Cotizador integrado) → B7 (GRG +
    FAT extendidos) → B8 (clasificador + pipelines) → B9 (UI #1 PWA) → B10
    (WhatsApp) → B13 (onboarding).
11. Cierre de MVP demo-able sobre cliente piloto cuando los 10 anteriores estén
    en producción con tests pasando.

---

*Fin de adenda de alcance MVP. Rige sobre Plan postPoC y sobre el criterio MVP
demo-able anterior. Aprobada por Jorge el 31 mayo 2026.*
