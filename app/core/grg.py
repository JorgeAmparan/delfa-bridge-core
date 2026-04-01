import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


class GovernanceGuardrails:
    """
    GRG — Governance Guardrails | Panohayan™
    Evalúa entidades contra reglas configurables por organización.
    Aprueba, marca, redacta o manda a cuarentena según políticas.
    """

    def __init__(self):
        self.org_id = os.getenv("ORG_ID", "default")
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        self._reglas_cache = None

    # ── Reglas ───────────────────────────────────────────────────────────────

    def _cargar_reglas(self) -> list:
        """Carga reglas activas de la organización desde Supabase."""
        if self._reglas_cache is not None:
            return self._reglas_cache

        resultado = self.supabase.table("governance_rules").select(
            "*"
        ).eq("org_id", self.org_id).eq("is_active", True).execute()

        self._reglas_cache = resultado.data
        return self._reglas_cache

    def _invalidar_cache(self):
        self._reglas_cache = None

    def crear_regla(self, entity_class: str, rule_type: str,
                    action: str, condition: dict = None) -> str:
        """Crea una nueva regla de gobernanza."""
        resultado = self.supabase.table("governance_rules").insert({
            "org_id": self.org_id,
            "entity_class": entity_class,
            "rule_type": rule_type,
            "condition": condition or {},
            "action": action,
            "is_active": True
        }).execute()

        self._invalidar_cache()
        rule_id = resultado.data[0]["id"]
        print(f"  [GRG] Regla creada: {rule_type} para {entity_class} → {action}")
        return rule_id

    # ── Evaluación ───────────────────────────────────────────────────────────

    def _evaluar_condicion(self, condicion: dict,
                            entity_value: str) -> bool:
        """Evalúa si una entidad cumple la condición de una regla."""
        if not condicion:
            return True

        # Condición por valor mínimo numérico
        if "min_value" in condicion:
            try:
                valor_limpio = entity_value.replace(
                    "$", "").replace(",", "").replace(
                    "MXN", "").replace("USD", "").strip()
                # Extraer primer número
                import re
                numeros = re.findall(r'\d+\.?\d*', valor_limpio)
                if numeros:
                    valor_num = float(numeros[0])
                    if valor_num >= condicion["min_value"]:
                        return True
            except Exception:
                pass

        # Condición por palabras clave
        if "contains" in condicion:
            return condicion["contains"].lower() in entity_value.lower()

        # Condición por longitud mínima
        if "min_length" in condicion:
            return len(entity_value) >= condicion["min_length"]

        return True

    def evaluar_entidad(self, entity_id: str, entity_class: str,
                        entity_value: str) -> dict:
        """
        Evalúa una entidad contra todas las reglas activas.
        Retorna: {aprobada, accion, regla_id, razon}
        """
        reglas = self._cargar_reglas()

        # Filtrar reglas aplicables a esta entity_class
        reglas_aplicables = [
            r for r in reglas
            if r["entity_class"] == entity_class
            or r["entity_class"] == "*"
        ]

        for regla in reglas_aplicables:
            condicion = regla.get("condition") or {}
            if self._evaluar_condicion(condicion, entity_value):
                accion = regla["action"]
                rule_id = regla["id"]

                if accion == "block":
                    self._mandar_cuarentena(
                        entity_id, rule_id,
                        f"Bloqueado por regla: {regla['rule_type']}"
                    )
                    self._actualizar_estado_entidad(entity_id, "quarantined")
                    print(f"  [GRG] ❌ BLOQUEADO: {entity_class} = {entity_value[:40]}")
                    return {
                        "aprobada": False,
                        "accion": "block",
                        "regla_id": rule_id,
                        "razon": regla["rule_type"]
                    }

                elif accion == "flag":
                    print(f"  [GRG] ⚠️  MARCADO: {entity_class} = {entity_value[:40]}")
                    return {
                        "aprobada": True,
                        "accion": "flag",
                        "regla_id": rule_id,
                        "razon": regla["rule_type"]
                    }

                elif accion == "require_approval":
                    self._mandar_cuarentena(
                        entity_id, rule_id,
                        f"Requiere aprobación: {regla['rule_type']}"
                    )
                    self._actualizar_estado_entidad(entity_id, "quarantined")
                    print(f"  [GRG] 🔒 CUARENTENA: {entity_class} = {entity_value[:40]}")
                    return {
                        "aprobada": False,
                        "accion": "require_approval",
                        "regla_id": rule_id,
                        "razon": regla["rule_type"]
                    }

                elif accion == "redact":
                    self._redactar_entidad(entity_id)
                    print(f"  [GRG] 🔏 REDACTADO: {entity_class}")
                    return {
                        "aprobada": True,
                        "accion": "redact",
                        "regla_id": rule_id,
                        "razon": regla["rule_type"]
                    }

        # Sin reglas aplicables — aprobada
        return {
            "aprobada": True,
            "accion": "approved",
            "regla_id": None,
            "razon": "Sin restricciones"
        }

    def evaluar_documento(self, document_id: str) -> dict:
        """
        Evalúa todas las entidades activas de un documento.
        Retorna resumen de resultados.
        """
        print(f"\n  [GRG] Evaluando documento: {document_id}")

        resultado = self.supabase.table("entities").select(
            "id, entity_class, entity_value"
        ).eq("document_id", document_id).eq(
            "org_id", self.org_id
        ).eq("status", "active").execute()

        entidades = resultado.data
        resumen = {
            "total": len(entidades),
            "aprobadas": 0,
            "bloqueadas": 0,
            "cuarentena": 0,
            "marcadas": 0,
            "redactadas": 0
        }

        for entidad in entidades:
            resultado_eval = self.evaluar_entidad(
                entity_id=entidad["id"],
                entity_class=entidad["entity_class"],
                entity_value=entidad["entity_value"]
            )

            accion = resultado_eval["accion"]
            if accion == "approved":
                resumen["aprobadas"] += 1
            elif accion == "block":
                resumen["bloqueadas"] += 1
            elif accion == "require_approval":
                resumen["cuarentena"] += 1
            elif accion == "flag":
                resumen["marcadas"] += 1
            elif accion == "redact":
                resumen["redactadas"] += 1

        print(f"  [GRG] Resumen: {resumen}")
        return resumen

    # ── Acciones sobre entidades ─────────────────────────────────────────────

    def _actualizar_estado_entidad(self, entity_id: str, status: str):
        self.supabase.table("entities").update({
            "status": status
        }).eq("id", entity_id).execute()

    def _mandar_cuarentena(self, entity_id: str,
                           rule_id: str, reason: str):
        self.supabase.table("quarantine").insert({
            "entity_id": entity_id,
            "org_id": self.org_id,
            "rule_id": rule_id,
            "reason": reason,
            "resolved": False
        }).execute()

    def _redactar_entidad(self, entity_id: str):
        self.supabase.table("entities").update({
            "entity_value": "[REDACTADO]",
            "normalized_value": "[REDACTADO]"
        }).eq("id", entity_id).execute()


if __name__ == "__main__":
    print("=" * 60)
    print("  GRG — Governance Guardrails | Panohayan™")
    print("=" * 60)

    grg = GovernanceGuardrails()

    # Crear reglas de prueba
    print("\n  [TEST] Creando reglas de gobernanza...")

    # Regla 1 — montos mayores a $20,000 requieren aprobación
    grg.crear_regla(
        entity_class="monto_total",
        rule_type="monto_alto",
        action="require_approval",
        condition={"min_value": 20000}
    )

    # Regla 2 — marcar pagos periódicos para revisión
    grg.crear_regla(
        entity_class="pago_periodico",
        rule_type="revision_pagos",
        action="flag",
        condition={}
    )

    # Evaluar documento más reciente
    resultado = grg.supabase.table("documents").select(
        "id, name"
    ).eq("org_id", grg.org_id).order(
        "created_at", desc=True
    ).limit(1).execute()

    if resultado.data:
        doc = resultado.data[0]
        print(f"\n  [TEST] Evaluando: {doc['name']}")
        resumen = grg.evaluar_documento(doc["id"])
        print(f"\n  Resultado final: {resumen}")
    else:
        print("  No hay documentos para evaluar.")