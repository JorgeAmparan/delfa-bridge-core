"""
Gestor de presupuesto del tenant (B2 §7.1 / §7.2).

DOCYAN LDE™ by XCID.

Opera la tabla `tenant_budget` (migración 008): saldo prepagado finito sin
auto-recharge + hard caps por documento y por sesión. El cotizador lo consulta
como gate previo a cualquier ingesta.

Diseño testeable: el acceso al almacén se abstrae en `BudgetStore`. En
producción usa Supabase (`SupabaseBudgetStore`, service key — bypassa RLS igual
que auth). En tests se inyecta `InMemoryBudgetStore` para verificar la lógica de
caps/saldo sin una base real. NO hay bypass del gate (Adenda §8): incluso en
tests, el cotizador consulta un BudgetManager; lo que se mockea es el ALMACÉN,
nunca la decisión.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class TenantBudget:
    """Vista de dominio de una fila de `tenant_budget`."""

    tenant_id: str
    saldo_actual_usd: float
    hard_cap_por_documento: float = 5.0
    hard_cap_por_sesion: float = 20.0
    moneda: str = "USD"


class BudgetStore(Protocol):
    """Contrato de almacenamiento del presupuesto (Supabase o memoria)."""

    def get(self, tenant_id: str) -> TenantBudget | None: ...

    def upsert(self, budget: TenantBudget) -> TenantBudget: ...

    def set_balance(self, tenant_id: str, nuevo_saldo: float) -> TenantBudget: ...


# ── Almacén en memoria (tests / dev local) ────────────────────────────────────


@dataclass
class InMemoryBudgetStore:
    """Almacén volátil para tests. NO usar en producción."""

    _rows: dict[str, TenantBudget] = field(default_factory=dict)

    def get(self, tenant_id: str) -> TenantBudget | None:
        return self._rows.get(tenant_id)

    def upsert(self, budget: TenantBudget) -> TenantBudget:
        self._rows[budget.tenant_id] = budget
        return budget

    def set_balance(self, tenant_id: str, nuevo_saldo: float) -> TenantBudget:
        b = self._rows[tenant_id]
        b.saldo_actual_usd = nuevo_saldo
        return b


# ── Almacén Supabase (producción) ─────────────────────────────────────────────


class SupabaseBudgetStore:
    """Almacén real sobre la tabla `tenant_budget`. Usa SUPABASE_SERVICE_KEY."""

    TABLE = "tenant_budget"

    def __init__(self, client=None):
        self._client = client

    def _sb(self):
        if self._client is None:
            from supabase import create_client

            self._client = create_client(
                os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY")
            )
        return self._client

    @staticmethod
    def _row_to_budget(row: dict) -> TenantBudget:
        return TenantBudget(
            tenant_id=row["tenant_id"],
            saldo_actual_usd=float(row["saldo_actual_usd"]),
            hard_cap_por_documento=float(row.get("hard_cap_por_documento", 5.0)),
            hard_cap_por_sesion=float(row.get("hard_cap_por_sesion", 20.0)),
            moneda=row.get("moneda", "USD"),
        )

    def get(self, tenant_id: str) -> TenantBudget | None:
        res = (
            self._sb()
            .table(self.TABLE)
            .select("*")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if not res.data:
            return None
        return self._row_to_budget(res.data[0])

    def upsert(self, budget: TenantBudget) -> TenantBudget:
        self._sb().table(self.TABLE).upsert(
            {
                "tenant_id": budget.tenant_id,
                "saldo_actual_usd": budget.saldo_actual_usd,
                "hard_cap_por_documento": budget.hard_cap_por_documento,
                "hard_cap_por_sesion": budget.hard_cap_por_sesion,
                "moneda": budget.moneda,
            },
            on_conflict="tenant_id",
        ).execute()
        return budget

    def set_balance(self, tenant_id: str, nuevo_saldo: float) -> TenantBudget:
        self._sb().table(self.TABLE).update(
            {"saldo_actual_usd": nuevo_saldo}
        ).eq("tenant_id", tenant_id).execute()
        b = self.get(tenant_id)
        if b is None:
            raise KeyError(f"tenant_budget inexistente para {tenant_id}")
        return b


# ── Gestor de presupuesto ─────────────────────────────────────────────────────


@dataclass
class CapVerdict:
    """Resultado de verificar un costo estimado contra saldo y hard caps."""

    aprobado: bool
    motivo: str
    saldo_disponible: float
    falta_usd: float = 0.0  # cuánto falta si fue rechazado por saldo


class BudgetManager:
    """Lógica de saldo y hard caps sobre un BudgetStore."""

    def __init__(self, store: BudgetStore | None = None):
        self.store = store or SupabaseBudgetStore()

    def get_budget(self, tenant_id: str) -> TenantBudget | None:
        return self.store.get(tenant_id)

    def ensure_budget(
        self,
        tenant_id: str,
        saldo_inicial_usd: float = 0.0,
        hard_cap_por_documento: float = 5.0,
        hard_cap_por_sesion: float = 20.0,
    ) -> TenantBudget:
        """Crea el presupuesto si no existe (alta de tenant / setup de tests)."""
        existing = self.store.get(tenant_id)
        if existing is not None:
            return existing
        return self.store.upsert(
            TenantBudget(
                tenant_id=tenant_id,
                saldo_actual_usd=saldo_inicial_usd,
                hard_cap_por_documento=hard_cap_por_documento,
                hard_cap_por_sesion=hard_cap_por_sesion,
            )
        )

    def verificar(
        self,
        tenant_id: str,
        costo_estimado_usd: float,
        costo_sesion_acumulado_usd: float = 0.0,
    ) -> CapVerdict:
        """
        Verifica un costo estimado contra (1) hard cap por documento, (2) hard
        cap por sesión acumulada, (3) saldo prepagado disponible. El orden
        importa: los hard caps son límites de seguridad y se evalúan antes que
        el saldo, para dar un mensaje preciso.
        """
        budget = self.store.get(tenant_id)
        if budget is None:
            return CapVerdict(
                aprobado=False,
                motivo=(
                    f"El tenant '{tenant_id}' no tiene presupuesto configurado. "
                    "Configure tenant_budget antes de ingerir."
                ),
                saldo_disponible=0.0,
                falta_usd=costo_estimado_usd,
            )

        if costo_estimado_usd > budget.hard_cap_por_documento:
            return CapVerdict(
                aprobado=False,
                motivo=(
                    f"Costo estimado ${costo_estimado_usd:.4f} excede el hard cap "
                    f"por documento (${budget.hard_cap_por_documento:.2f}). "
                    "Ingesta rechazada."
                ),
                saldo_disponible=budget.saldo_actual_usd,
            )

        total_sesion = costo_sesion_acumulado_usd + costo_estimado_usd
        if total_sesion > budget.hard_cap_por_sesion:
            return CapVerdict(
                aprobado=False,
                motivo=(
                    f"El acumulado de la sesión ${total_sesion:.4f} excede el hard "
                    f"cap por sesión (${budget.hard_cap_por_sesion:.2f}). "
                    "Ingesta rechazada."
                ),
                saldo_disponible=budget.saldo_actual_usd,
            )

        if costo_estimado_usd > budget.saldo_actual_usd:
            return CapVerdict(
                aprobado=False,
                motivo=(
                    f"Saldo insuficiente: disponible ${budget.saldo_actual_usd:.4f}, "
                    f"se requieren ${costo_estimado_usd:.4f}. "
                    "Recargue el saldo prepagado para continuar."
                ),
                saldo_disponible=budget.saldo_actual_usd,
                falta_usd=round(costo_estimado_usd - budget.saldo_actual_usd, 4),
            )

        return CapVerdict(
            aprobado=True,
            motivo="Presupuesto suficiente y dentro de hard caps.",
            saldo_disponible=budget.saldo_actual_usd,
        )

    def debitar(self, tenant_id: str, monto_usd: float) -> TenantBudget:
        """
        Descuenta del saldo tras una ingesta efectivamente realizada. Se invoca
        DESPUÉS de procesar (con el costo real o el estimado confirmado), nunca
        antes de la confirmación del usuario.
        """
        budget = self.store.get(tenant_id)
        if budget is None:
            raise KeyError(f"tenant_budget inexistente para {tenant_id}")
        nuevo = round(budget.saldo_actual_usd - monto_usd, 4)
        return self.store.set_balance(tenant_id, nuevo)
