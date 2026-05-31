"""
B2 §10 — test bloqueador: si el presupuesto del tenant es insuficiente, el
cotizador RECHAZA la ingesta con mensaje claro y NO la procesa.

El gate no tiene bypass (CLAUDE.md §14): aquí se mockea el ALMACÉN de presupuesto
(InMemoryBudgetStore), nunca la decisión del cotizador.
"""
from app.ingesta.budget_manager import BudgetManager, InMemoryBudgetStore
from app.ingesta.cotizador import Cotizador, DecisionCotizacion

TEXTO = "Procedimiento de instalación. " * 2000  # documento no trivial


def _cotizador(saldo, cap_doc=5.0, cap_ses=20.0):
    store = InMemoryBudgetStore()
    bm = BudgetManager(store=store)
    bm.ensure_budget(
        "tenant_x",
        saldo_inicial_usd=saldo,
        hard_cap_por_documento=cap_doc,
        hard_cap_por_sesion=cap_ses,
    )
    return Cotizador(budget_manager=bm)


def test_saldo_insuficiente_rechaza():
    cz = _cotizador(saldo=0.0001)
    c = cz.cotizar("tenant_x", TEXTO, tipo_documento="manual_tecnico")
    assert c.decision == DecisionCotizacion.rechazado_presupuesto
    assert not c.aprobado
    assert "insuficiente" in c.motivo.lower()
    assert c.falta_usd > 0


def test_tenant_sin_presupuesto_configurado_rechaza():
    bm = BudgetManager(store=InMemoryBudgetStore())  # sin ensure_budget
    cz = Cotizador(budget_manager=bm)
    c = cz.cotizar("tenant_nuevo", TEXTO)
    assert not c.aprobado
    assert "presupuesto" in c.motivo.lower()


def test_excede_hard_cap_por_documento_rechaza():
    cz = _cotizador(saldo=100.0, cap_doc=0.0001)
    c = cz.cotizar("tenant_x", TEXTO)
    assert c.decision == DecisionCotizacion.rechazado_hard_cap
    assert "hard cap" in c.motivo.lower()


def test_excede_hard_cap_por_sesion_rechaza():
    cz = _cotizador(saldo=100.0, cap_doc=100.0, cap_ses=0.001)
    # Costo acumulado de sesión alto fuerza el rechazo por cap de sesión.
    c = cz.cotizar("tenant_x", TEXTO, costo_sesion_acumulado_usd=0.0)
    assert c.decision == DecisionCotizacion.rechazado_hard_cap
    assert "sesión" in c.motivo.lower() or "sesion" in c.motivo.lower()


def test_rechazo_no_devuelve_aprobacion():
    """Un rechazo nunca debe marcar aprobado=True (no hay ingesta)."""
    cz = _cotizador(saldo=0.0)
    c = cz.cotizar("tenant_x", TEXTO)
    assert c.aprobado is False
