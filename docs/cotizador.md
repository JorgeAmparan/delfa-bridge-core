# Cotizador pre-ingesta (B2 §7 — CRÍTICO)

> **DOCYAN LDE™ by XCID.** Gate financiero **inviolable**: ningún documento se
> ingiere al grafo sin pasar por el cotizador. **No hay bypass** (CLAUDE.md §14).
> Justificación: incidente PoC 28-may-2026 ($5,000 en Gemini por una ingesta sin
> control de costo, timeout 600s, escritura parcial).

## Qué hace (`app/ingesta/cotizador.py`)

Antes de cualquier ingesta:

1. **Mide tokens** del documento con `tiktoken` (encoding `o200k_base`).
2. **Estima costo** USD: extracción (Gemini 2.5 Flash) + QA (gpt-4o-mini) +
   embeddings (BGE-M3, costo de cómputo marginal).
3. **Estima tiempo** de procesamiento (PoC: NOM 32pp ≈ 642s).
4. **Verifica presupuesto** del tenant (tabla `tenant_budget`) + hard caps.
5. **Decide**: `rechazado_hard_cap`, `rechazado_presupuesto`, o
   `aprobado_requiere_confirmacion`.
6. **Nunca ingiere por su cuenta**: la ingesta procede solo con confirmación
   explícita del usuario.

## Modelo de costo (`pricing_table.py`)

Precios vigentes (fechados, `PRICING_AS_OF`) por 1M de tokens:

| Modelo | Input | Output |
|---|---|---|
| `gemini/gemini-2.5-flash` | $0.30 | $2.50 |
| `gpt-4o-mini` | $0.15 | $0.60 |

**Modelo de uso** (cómo se traducen los tokens del documento a tokens
facturables del pipeline GraphRAG-SDK), calibrado contra baselines del PoC:

```
extracción Gemini: input ≈ doc×1.0, output ≈ doc×0.5
QA gpt-4o-mini:     input ≈ doc×0.3, output ≈ doc×0.1
embeddings BGE-M3:  doc×1.0 tokens × costo de cómputo marginal
```

### Validación contra baselines del PoC (±15%)

| Caso | Tokens | Estimado | Baseline | Error |
|---|---|---|---|---|
| NOM 32pp | 22,400 | $0.0373 | $0.036 | +3.6% |
| Ley 61pp | 28,000 | $0.0466 | $0.046 | +1.3% |
| Corpus 50 NOM + 10 leyes | — | ~$2.27 | $2.26 | +0.4% |

Cubierto por `tests/test_cotizador_baselines.py`. `tiktoken` no es el tokenizador
exacto de Gemini, pero es la referencia que fija la Adenda §8 y es conservador
(tiende a contar igual o más para texto técnico latino).

## Protección financiera multinivel (`budget_manager.py`, tabla `tenant_budget`)

- **Saldo prepagado finito sin auto-recharge**: el cliente recarga manualmente.
- **Hard cap por documento** (default $5 USD alfa).
- **Hard cap por sesión** de ingesta (default $20 USD alfa).
- El cotizador es el **guard previo** a invocar a GraphRAG-SDK.

Orden de verificación: hard cap por documento → hard cap por sesión → saldo
disponible (mensaje preciso en cada rechazo, con `falta_usd` si es por saldo).

## Cómo el PM ve y maneja el budget

La tabla `tenant_budget` (migración 008, RLS por `tenant_id`) guarda
`saldo_actual_usd`, los dos hard caps, `ultima_recarga`. `BudgetManager` expone
`get_budget`, `ensure_budget`, `verificar` y `debitar` (se descuenta el saldo tras
una ingesta efectivamente realizada, nunca antes de confirmar). En B11 (PM
Dashboard) se expondrá la gestión visual; aquí queda la base operativa.

## Endpoints (`app/api/routers/ingesta.py`)

```
POST /ingesta/documents            → cotiza + crea job (pending/rejected), NO ingiere
POST /ingesta/documents/{id}/confirm → si aprobado, encola al worker
GET  /ingesta/documents/{id}       → estado del job
```

## Regla para tests

El cotizador **es un gate sin bypass**. Para tests que necesiten saltar el costo
real se mockea el **almacén** de presupuesto (`InMemoryBudgetStore`), **nunca la
decisión** del cotizador. Ver `tests/test_cotizador_*.py`.
