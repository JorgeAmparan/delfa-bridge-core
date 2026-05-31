"""
Cotizador pre-ingesta (B2 §7 — CRÍTICO, Adenda §8).

DOCYAN LDE™ by XCID.

GATE financiero inviolable: antes de invocar a GraphRAG-SDK, este módulo

  1. mide los tokens del documento con tiktoken,
  2. estima costo (extracción Gemini 2.5 Flash + QA gpt-4o-mini + embeddings BGE-M3),
  3. estima tiempo de procesamiento,
  4. verifica saldo prepagado del tenant y hard caps (por documento y por sesión),
  5. decide: RECHAZADO (saldo o hard cap) o APROBADO_REQUIERE_CONFIRMACION,
  6. nunca ingiere por su cuenta: la ingesta solo procede con confirmación explícita.

No hay bypass (CLAUDE.md §12 / §14). Para tests que necesiten saltar el costo
real se mockea el ALMACÉN de presupuesto (InMemoryBudgetStore), nunca la decisión.

Justificación operativa: incidente PoC 28-may-2026 ($5,000 en Gemini por una
ingesta sin control de costo, timeout 600s, escritura parcial).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum

from app.ingesta import pricing_table as pt
from app.ingesta.budget_manager import BudgetManager

# Encoding de tiktoken para medir. o200k_base es el de gpt-4o/gpt-4o-mini; se usa
# como referencia única para todo el documento (aproximación documentada para la
# parte Gemini — ver pricing_table). Carga perezosa: tiktoken es dep del worker
# y del backend (B0) pero la importación se hace al medir, no al importar módulo.
TIKTOKEN_ENCODING = "o200k_base"


class DecisionCotizacion(str, Enum):
    aprobado_requiere_confirmacion = "aprobado_requiere_confirmacion"
    rechazado_presupuesto = "rechazado_presupuesto"
    rechazado_hard_cap = "rechazado_hard_cap"


@dataclass
class DesgloseCosto:
    """Desglose por fase del pipeline, en USD."""

    extraccion_usd: float
    qa_usd: float
    embeddings_usd: float

    @property
    def total_usd(self) -> float:
        return round(self.extraccion_usd + self.qa_usd + self.embeddings_usd, 6)


@dataclass
class Cotizacion:
    """Resultado de cotizar un documento. Es el objeto que el endpoint devuelve."""

    tenant_id: str
    tipo_documento: str | None
    tokens_documento: int
    costo_estimado_usd: float
    desglose: DesgloseCosto
    tiempo_estimado_seg: float
    decision: DecisionCotizacion
    motivo: str
    saldo_disponible_usd: float
    falta_usd: float = 0.0
    pricing_as_of: str = pt.PRICING_AS_OF
    # Detalle de tokens facturables estimados por fase (transparencia para el PM).
    detalle_tokens: dict = field(default_factory=dict)

    @property
    def aprobado(self) -> bool:
        return self.decision == DecisionCotizacion.aprobado_requiere_confirmacion

    def to_dict(self) -> dict:
        d = asdict(self)
        d["decision"] = self.decision.value
        d["costo_total_usd"] = self.desglose.total_usd
        d["aprobado"] = self.aprobado
        return d


def contar_tokens(texto: str) -> int:
    """Cuenta tokens con tiktoken (Adenda §8). Fallback robusto si no carga."""
    try:
        import tiktoken

        enc = tiktoken.get_encoding(TIKTOKEN_ENCODING)
        return len(enc.encode(texto))
    except Exception:
        # Fallback conservador (sobreestima): ~4 chars por token para texto latino.
        # Nunca subestima el costo, que es el riesgo a evitar.
        return max(1, len(texto) // 4)


def estimar_costo(tokens_documento: int) -> tuple[DesgloseCosto, dict]:
    """
    Traduce tokens del documento a costo USD usando el modelo de uso calibrado
    (pricing_table). Devuelve el desglose y el detalle de tokens facturables.
    """
    gemini = pt.model_pricing("gemini/gemini-2.5-flash")
    mini = pt.model_pricing("gpt-4o-mini")

    extr_in = tokens_documento * pt.EXTRACTION_INPUT_RATIO
    extr_out = tokens_documento * pt.EXTRACTION_OUTPUT_RATIO
    qa_in = tokens_documento * pt.QA_INPUT_RATIO
    qa_out = tokens_documento * pt.QA_OUTPUT_RATIO

    extraccion_usd = gemini.cost(extr_in, extr_out)
    qa_usd = mini.cost(qa_in, qa_out)
    # Embeddings BGE-M3: se embeben los tokens del documento (cómputo propio).
    embeddings_usd = tokens_documento / 1_000_000 * pt.BGE_M3_COMPUTE_USD_PER_1M

    desglose = DesgloseCosto(
        extraccion_usd=round(extraccion_usd, 6),
        qa_usd=round(qa_usd, 6),
        embeddings_usd=round(embeddings_usd, 6),
    )
    detalle = {
        "extraccion_input_tokens": int(extr_in),
        "extraccion_output_tokens": int(extr_out),
        "qa_input_tokens": int(qa_in),
        "qa_output_tokens": int(qa_out),
        "embeddings_tokens": int(tokens_documento),
    }
    return desglose, detalle


def estimar_tiempo_seg(tokens_documento: int) -> float:
    """Estima tiempo de procesamiento (Adenda §8: PoC NOM 32pp ≈ 642s)."""
    return round(tokens_documento / 1000 * pt.SECONDS_PER_1K_DOC_TOKENS, 1)


class Cotizador:
    """Cotizador pre-ingesta. Punto único de decisión de gasto de ingesta."""

    def __init__(self, budget_manager: BudgetManager | None = None):
        self.budget = budget_manager or BudgetManager()

    def cotizar(
        self,
        tenant_id: str,
        texto_documento: str,
        tipo_documento: str | None = None,
        costo_sesion_acumulado_usd: float = 0.0,
    ) -> Cotizacion:
        """
        Cotiza un documento y decide si la ingesta puede proceder. NO ingiere.

        Devuelve una Cotizacion con la decisión:
          - rechazado_hard_cap   → excede cap por documento o por sesión.
          - rechazado_presupuesto → saldo prepagado insuficiente.
          - aprobado_requiere_confirmacion → procede SOLO con confirmación explícita.
        """
        tokens = contar_tokens(texto_documento)
        desglose, detalle = estimar_costo(tokens)
        costo = desglose.total_usd
        tiempo = estimar_tiempo_seg(tokens)

        verdict = self.budget.verificar(
            tenant_id, costo, costo_sesion_acumulado_usd
        )

        if verdict.aprobado:
            decision = DecisionCotizacion.aprobado_requiere_confirmacion
            motivo = (
                f"Estimación ${costo:.4f} USD (~{tiempo:.0f}s). "
                "Presupuesto suficiente. Requiere confirmación explícita para ingerir."
            )
        elif "hard cap" in verdict.motivo.lower():
            decision = DecisionCotizacion.rechazado_hard_cap
            motivo = verdict.motivo
        else:
            decision = DecisionCotizacion.rechazado_presupuesto
            motivo = verdict.motivo

        return Cotizacion(
            tenant_id=tenant_id,
            tipo_documento=tipo_documento,
            tokens_documento=tokens,
            costo_estimado_usd=costo,
            desglose=desglose,
            tiempo_estimado_seg=tiempo,
            decision=decision,
            motivo=motivo,
            saldo_disponible_usd=verdict.saldo_disponible,
            falta_usd=verdict.falta_usd,
            detalle_tokens=detalle,
        )
