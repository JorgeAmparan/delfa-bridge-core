# Sprint Contract B6 — GRG extendido (8 familias) + FAT extendido (9 familias + SHA-256)

**Producto:** DOCYAN LDE — Live Document Environment by XCID
**Bloque:** B6 | **Ejecutor:** Opus 4.8 vía Claude Code CLI
**Modo:** Una aprobación + ejecución completa + un reporte final.

---

## Prerequisitos
B3, B4 (al menos parcial). Paralelo con B4/B5.

## Contexto para Opus
GRG y FAT son la gobernanza central. Para un lab ISO 17025, la auditoría criptográfica es lo que hace que el sistema se tome en serio. GRG es **función técnica, no instrucción verbal** (diferenciador vs CAT tools, donde el lock es "regaño verbal" ignorable).

Estado (auditoría): GRG actual (`app/core/grg.py`, 252 LOC): block/flag/quarantine/redact, cache TTL, sin las 8 familias. FAT actual (`app/core/matrix.py`/`TraceabilityMatrix`, 159 LOC): logea en Supabase `audit_trail`, **sin hash chain SHA-256**.

## Alcance específico

### GRG extendido — 8 familias de reglas (doc 07)
Cada regla: trigger + condición + acción + registro FAT.

- **F1 Lock terminológico:** R-LT-01 (lock duro: reemplazo automático + `:SugerenciaTermino` reportada_al_cliente), R-LT-02 (reporte periódico mensual de sugerencias bloqueadas), R-LT-03 (anulación manual por revisor con justificación en FAT).
- **F2 Umbrales de confianza por criticidad:** R-UC-01 a R-UC-05. Umbrales: **seguridad ≥0.95, regulatorio ≥0.90, calidad ≥0.85, operacional ≥0.75, informativa ≥0.60**. Acción según tier y criticidad (ej. seguridad + confianza<umbral en Tier 1 → flag al cliente con disclaimer crítico, NO servir directo sin advertencia).
- **F3 Freno de alucinación:** fabricación numérica, fabricación de referencias normativas, fabricación de identificadores.
- **F4 Fidelidad de no-traducibles:** fórmulas químicas, unidades SI, marcas registradas, marcadores paramétricos `{variable}`.
- **F5 Validación por tipo de segmento:** CPS subtítulos, longitud etiquetas diagrama, imperativo en pasos, tono ANSI Z535 en advertencias.
- **F6 Consistencia cross-segmento:** intra-documento + cross-documento del mismo cliente (mismo término traducido igual en todas las apariciones).
- **F7 Consulta operativa:** 3 reglas para UI #1.
- **F8 Canal PWA vs WhatsApp:** 2 reglas.

`:ConfiguracionGRG` por tenant con umbrales ajustables. Cache: configuración del tenant 15min, sin cache para evaluación de segmentos individuales.

**Alcance por pista:** Pista A aplica GRG en producción + consulta. Pista B solo en consulta (la producción la hizo la agencia).

### FAT extendido — 9 familias + cadena criptográfica (doc 08)
Nodo `:EventoFAT` (evento_id, tipo_evento, timestamp ISO 8601 con tz, actor_tipo, actor_id, tenant_id, entidad_afectada_tipo/id, payload JSON, metadata JSON, `corrige_evento_id`, `hash_evento`, `hash_evento_anterior`).

**Cadena criptográfica:** algoritmo **SHA-256 sobre `(evento_id || timestamp || tipo_evento || payload || hash_evento_anterior)`**. Cada evento lleva hash del anterior del mismo tenant → cadena verificable. Alterar un evento intermedio rompe la cadena en posteriores.

**Inmutabilidad append-only:** eventos no se modifican ni eliminan. Corrección = nuevo evento con `corrige_evento_id` apuntando al original.

**9 familias de eventos:** F1 pipeline de traducción (Pista A), F2 revisión humana (Pista A Tier 2/3), F3 ingesta bilingüe (Pista B), F4 consulta operativa (ambas), F5 troubleshooting (Tipo 5), F6 alertas (Tipo 7), F7 gobernanza (GRG), F8 onboarding, F9 sistema y meta-FAT.

**Retención por familia (decisión #12):** 7 años producción/revisión/ingesta/gobernanza, 5 años onboarding, 3 años consulta/troubleshooting/alertas, 2 años sistema.

**Implementación física híbrida:** eventos críticos en FalkorDB, eventos de alta frecuencia en Supabase.

**Capacidades:** reconstrucción de estado en cualquier punto del tiempo; exportación auditable PDF/XML/JSON/CSV; verificador de integridad de la cadena (ejecutable bajo demanda y en CI).

**Vinculaciones al DKG/DTM:** `:AFECTA_DOCUMENTO`, `:AFECTA_SEGMENTO`, `:AFECTA_ENTIDAD`, `:AFECTA_ALERTA`, `:AFECTA_PROYECTO`, `:CORRIGE`, `:CONSECUENCIA_DE`.

## Componentes a construir
- `app/governance/grg_extendido.py` (evoluciona `grg.py`, 8 familias)
- `app/governance/configuracion_grg.py` (por tenant)
- `app/audit/fat_extendido.py` (evoluciona `matrix.py` + hash chain)
- `app/audit/integrity_checker.py`
- `app/audit/reports.py` (PDF/XML/JSON/CSV)
- `app/audit/retention.py` (política por familia)
- `migrations/008_fat_hash_chain.sql` (columnas hash + híbrido)

## Tests automatizados requeridos
- GRG: cada una de las 8 familias se activa con input que la dispara (al menos 1 regla por familia, con sus umbrales).
- F2 umbrales: segmento criticidad seguridad con confianza<0.95 → acción correcta por tier.
- Cuarentena: entidad en cuarentena no servida, FAT registra.
- Hash chain: cadena de 10 eventos; alterar cualquiera rompe verificación.
- Inmutabilidad: corrección crea nuevo evento con `corrige_evento_id`, no edita el original.
- Retención: política por familia elimina vencidos (con backup previo verificado).
- Reporte: por documento contiene eventos esperados; exporta en 4 formatos.
- Verificador de integridad corre en CI.

## Salida verificable
GRG flagea según las 8 familias con umbrales correctos. FAT registra todos los eventos con integridad criptográfica verificable (alterar evento rompe cadena). Reportes auditables exportables en 4 formatos. Reconstrucción de estado funcional.

## Notas para Opus sobre integración con código existente
- GRG actual (252 LOC) se evoluciona; preservar block/flag/quarantine/redact + cache TTL.
- FAT actual (`matrix.py`, 159 LOC) se evoluciona agregando hash chain; preservar consultas por documento/entidad/actividad.
- Governance Gate de B3 invoca este GRG extendido; mantener interfaz.
- Tabla `audit_trail` ya existe (migración B0); hash chain puede requerir columnas (`008`).
- Retención del FAT (Supabase) requiere rutina propia distinta del backup de grafo de B1.

## Reglas de ejecución
- No stubs, no mocks (excepto tests), no hardcoded. Las 8 familias GRG completas, las 9 familias FAT completas, hash chain real.
- Verdad operacional. PENDIENTE DE JORGE si modelado no resuelto.

**Referencias:** doc 07 (GRG, 8 familias con códigos R-LT/R-UC + umbrales), doc 08 (FAT, 9 familias + algoritmo SHA-256 exacto + retención + híbrido), doc 14 (B6).
