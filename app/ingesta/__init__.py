"""
Ingesta — cotizador pre-ingesta y protección financiera (B2 §7).

Este paquete es el GATE financiero de DOCYAN LDE: ningún documento se ingiere al
grafo sin pasar primero por el cotizador, que mide tokens (tiktoken), estima
costo y tiempo, verifica el presupuesto prepagado del tenant y exige
confirmación explícita. No hay bypass (Adenda §8 / CLAUDE.md §12; justificación:
incidente PoC 28-may-2026, $5,000 en Gemini por ingesta sin control de costo).
"""
from app.ingesta.cotizador import Cotizacion, Cotizador, DecisionCotizacion

__all__ = ["Cotizacion", "Cotizador", "DecisionCotizacion"]
