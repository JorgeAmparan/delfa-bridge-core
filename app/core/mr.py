import os
from dotenv import load_dotenv

load_dotenv()

# ─── MODEL ROUTER | Panohayan™ ────────────────────────────────────────────────
#
# Selecciona el LLM más costo-eficiente según complejidad del documento.
# Agnóstico de proveedor — soporta Google, Anthropic y OpenAI.
#
# Tier 1: Gemini 2.5 Flash    — documentos simples, máximo ahorro
# Tier 2: Gemini 2.5 Flash    — tablas o documentos medianos
# Tier 3: Claude Sonnet 4.6   — legal/fiscal denso
# Tier 4: Claude Opus 4.6     — razonamiento profundo
# ─────────────────────────────────────────────────────────────────────────────

MODELOS = {
    "tier1": {
        "modelo": "gemini-2.5-flash",
        "proveedor": "google",
        "tier": 1,
        "descripcion": "Documentos simples — máximo ahorro"
    },
    "tier2": {
        "modelo": "gemini-2.5-flash",
        "proveedor": "google",
        "tier": 2,
        "descripcion": "Tablas o documentos medianos"
    },
    "tier3": {
        "modelo": "claude-sonnet-4-6",
        "proveedor": "anthropic",
        "tier": 3,
        "descripcion": "Legal/fiscal denso"
    },
    "tier4": {
        "modelo": "claude-opus-4-6",
        "proveedor": "anthropic",
        "tier": 4,
        "descripcion": "Razonamiento profundo"
    }
}


class ModelRouter:
    """
    MR — Model Router | Panohayan™
    Selecciona el LLM óptimo por costo-eficiencia según:
    - Tamaño del documento (chars)
    - Presencia de tablas
    - Tipo de documento
    - Tipo de tarea (extracción, razonamiento, normalización)
    """

    def __init__(self):
        self.override_modelo = os.getenv("MR_OVERRIDE_MODEL", None)

    def seleccionar(self, chars: int, tiene_tablas: bool,
                    source_type: str, doc_type: str = "general") -> dict:
        """
        Selecciona el modelo más costo-eficiente para el documento.
        """
        # Override manual desde .env si está configurado
        if self.override_modelo:
            for tier_info in MODELOS.values():
                if tier_info["modelo"] == self.override_modelo:
                    info = tier_info.copy()
                    info["override"] = True
                    return info

        # Tier 4 — documentos muy largos o razonamiento profundo
        if chars > 100000:
            return MODELOS["tier4"].copy()

        # Tier 3 — documentos legales/fiscales densos
        if source_type in ["pdf", "docx"] and chars > 50000:
            return MODELOS["tier3"].copy()

        if doc_type in ["reglamento", "contrato"] and chars > 30000:
            return MODELOS["tier3"].copy()

        # Tier 2 — tablas o documentos medianos
        if tiene_tablas or chars > 20000:
            return MODELOS["tier2"].copy()

        # Tier 1 — documentos simples
        return MODELOS["tier1"].copy()

    def seleccionar_para_intent(self) -> dict:
        """
        Modelo para análisis de intención — siempre Tier 1.
        El análisis de intención es simple y debe ser rápido y barato.
        """
        return MODELOS["tier1"].copy()

    def seleccionar_para_enriquecimiento(self, doc_type: str,
                                          chars: int) -> dict:
        """
        Modelo para enriquecimiento semántico post-extracción.
        """
        if doc_type in ["reglamento", "contrato"] and chars > 20000:
            return MODELOS["tier3"].copy()
        return MODELOS["tier2"].copy()

    def log_seleccion(self, modelo_info: dict):
        """Imprime la selección del router."""
        print(f"  [MR] Tier {modelo_info['tier']}: "
              f"{modelo_info['modelo']} "
              f"({modelo_info['descripcion']})")


# ── Instancia global ──────────────────────────────────────────────────────────
model_router = ModelRouter()


if __name__ == "__main__":
    print("=" * 60)
    print("  MR — Model Router | Panohayan™")
    print("=" * 60)

    mr = ModelRouter()

    casos = [
        {"chars": 5000,   "tiene_tablas": False, "source_type": "pdf",  "doc_type": "general"},
        {"chars": 25000,  "tiene_tablas": True,  "source_type": "xlsx", "doc_type": "general"},
        {"chars": 55000,  "tiene_tablas": False, "source_type": "pdf",  "doc_type": "contrato"},
        {"chars": 120000, "tiene_tablas": False, "source_type": "pdf",  "doc_type": "reglamento"},
    ]

    print()
    for caso in casos:
        seleccion = mr.seleccionar(**caso)
        print(f"  chars={caso['chars']:>7} | "
              f"tablas={str(caso['tiene_tablas']):<5} | "
              f"tipo={caso['doc_type']:<12} → "
              f"Tier {seleccion['tier']}: {seleccion['modelo']}")