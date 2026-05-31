"""
B2 §10 — test bloqueador: el cotizador produce estimaciones coherentes con los
baselines reales del PoC (Adenda §8), tolerancia ±15%.

Baselines PoC 28-may-2026:
  - NOM 32 pp ≈ $0.036 USD
  - Ley 61 pp ≈ $0.046 USD

El cotizador trabaja sobre TOKENS (tiktoken), no páginas. Se usa la densidad
observada en el PoC (NOM ≈ 700 tok/pp → 32pp ≈ 22,400 tokens) para mapear el
baseline a un tamaño en tokens y verificar que la estimación cae dentro de ±15%.
"""
from app.ingesta.cotizador import estimar_costo

TOLERANCIA = 0.15


def _err(est: float, base: float) -> float:
    return abs(est - base) / base


def test_baseline_nom_32pp():
    # NOM 32 pp ≈ 22,400 tokens → baseline $0.036
    desglose, _ = estimar_costo(22_400)
    assert _err(desglose.total_usd, 0.036) <= TOLERANCIA, (
        f"NOM: estimado ${desglose.total_usd:.4f} fuera de ±15% de $0.036"
    )


def test_baseline_ley_densidad_menor():
    # Ley general: más páginas pero menor densidad de extracción (LGPGIR del PoC).
    # 61 pp con densidad menor ≈ 28,000 tokens → baseline $0.046
    desglose, _ = estimar_costo(28_000)
    assert _err(desglose.total_usd, 0.046) <= TOLERANCIA, (
        f"Ley: estimado ${desglose.total_usd:.4f} fuera de ±15% de $0.046"
    )


def test_costo_monotono_crece_con_tokens():
    """Más tokens ⇒ más costo (sanidad del modelo)."""
    chico, _ = estimar_costo(5_000)
    grande, _ = estimar_costo(50_000)
    assert grande.total_usd > chico.total_usd


def test_extraccion_domina_el_costo():
    """La extracción Gemini debe dominar el costo (patrón del PoC)."""
    desglose, _ = estimar_costo(22_400)
    assert desglose.extraccion_usd > desglose.qa_usd > desglose.embeddings_usd


def test_corpus_grande_coherente():
    """
    Corpus PoC: 50 normas + 10 leyes ≈ $2.26 USD. Aproximamos como la suma de
    50 NOMs (22.4k) + 10 leyes (28k); debe quedar dentro de ±15% de $2.26.
    """
    una_nom, _ = estimar_costo(22_400)
    una_ley, _ = estimar_costo(28_000)
    total = 50 * una_nom.total_usd + 10 * una_ley.total_usd
    assert _err(total, 2.26) <= TOLERANCIA, f"corpus estimado ${total:.2f} fuera de ±15% de $2.26"
