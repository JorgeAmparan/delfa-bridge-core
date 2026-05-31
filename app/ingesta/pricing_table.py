"""
Tabla de precios y modelo de uso de tokens del pipeline de ingesta (B2 §7).

DOCYAN LDE™ by XCID.

Dos piezas:

  1. PRECIOS por modelo (USD por 1M de tokens, input/output). Son los precios
     públicos vigentes de los modelos validados en el PoC (Adenda §3). Se aíslan
     aquí para que actualizarlos sea un cambio de un solo archivo, fechado.

  2. MODELO DE USO — cómo se traducen los tokens *del documento* (medidos con
     tiktoken) a tokens *facturables* del pipeline GraphRAG-SDK. El pipeline NO
     manda el documento crudo una sola vez: lo trocea y por cada chunk envía el
     prompt de extracción (instrucciones + schema) y recibe triples; luego una
     pasada de QA (gpt-4o-mini) y una de resolución. Los multiplicadores capturan
     ese patrón. Están CALIBRADOS contra los baselines reales del PoC (ver
     test_cotizador_baselines.py): NOM 32 pp ≈ $0.036, Ley 61 pp ≈ $0.046.

Importante: la estimación es eso, una estimación previa. tiktoken no es el
tokenizador exacto de Gemini, pero es la referencia que la Adenda §8 fija para el
cotizador y es conservador (cl100k/o200k tienden a contar igual o más que el
tokenizador de Gemini para texto técnico latino). Se documenta como aproximación.
"""
from __future__ import annotations

from dataclasses import dataclass

# Fecha de la tabla de precios. Actualizar junto con los valores.
PRICING_AS_OF = "2026-05-28"


@dataclass(frozen=True)
class ModelPricing:
    """Precio de un modelo en USD por 1M de tokens."""

    model: str
    input_usd_per_1m: float
    output_usd_per_1m: float

    def cost(self, input_tokens: float, output_tokens: float) -> float:
        return (
            input_tokens / 1_000_000 * self.input_usd_per_1m
            + output_tokens / 1_000_000 * self.output_usd_per_1m
        )


# ── Precios vigentes (Adenda §3 — modelos validados con el PoC NOM-052) ───────
# Gemini 2.5 Flash: extracción + resolution (prefijo gemini/ vía LiteLLM).
# gpt-4o-mini: QA / consulta.
PRICING: dict[str, ModelPricing] = {
    "gemini/gemini-2.5-flash": ModelPricing(
        model="gemini/gemini-2.5-flash",
        input_usd_per_1m=0.30,
        output_usd_per_1m=2.50,
    ),
    "gpt-4o-mini": ModelPricing(
        model="gpt-4o-mini",
        input_usd_per_1m=0.15,
        output_usd_per_1m=0.60,
    ),
}


# ── Modelo de uso del pipeline (calibrado contra baselines PoC) ───────────────
# Por cada token de documento medido con tiktoken, cuántos tokens factura cada
# fase. Derivados para reproducir NOM 32pp ≈ $0.036 (ver test de baselines):
#   extracción Gemini: input ≈ doc×1.0 (chunk + prompt overhead ~ se compensan),
#                       output ≈ doc×0.5 (triples extraídos),
#   QA gpt-4o-mini:     input ≈ doc×0.3, output ≈ doc×0.1.
# Estos factores son la perilla de calibración; si cambian los precios o el
# comportamiento del SDK, se re-calibran contra baselines y se ajusta el test.
EXTRACTION_INPUT_RATIO = 1.0
EXTRACTION_OUTPUT_RATIO = 0.5
QA_INPUT_RATIO = 0.3
QA_OUTPUT_RATIO = 0.1

# Costo computacional de embeddings BGE-M3 self-hosted. No es un costo de API
# (el embedder es propio), pero es reportable como costo marginal de cómputo.
# Estimación conservadora en USD por 1M de tokens embebidos (electricidad+amort.).
BGE_M3_COMPUTE_USD_PER_1M = 0.01

# ── Modelo de tiempo (Adenda §8 — PoC: Gemini Flash 642s para una NOM 32pp) ───
# Throughput efectivo observado incluyendo latencia de red y rate limiting.
SECONDS_PER_1K_DOC_TOKENS = 642.0 / 22.4  # ≈ 28.7 s por 1k tokens (NOM 32pp≈22.4k)


def model_pricing(model: str) -> ModelPricing:
    """Devuelve el pricing de un modelo o lanza KeyError explícito."""
    if model not in PRICING:
        raise KeyError(
            f"Modelo sin precio en pricing_table: '{model}'. "
            f"Modelos conocidos: {sorted(PRICING)}. Actualizar pricing_table.py."
        )
    return PRICING[model]
