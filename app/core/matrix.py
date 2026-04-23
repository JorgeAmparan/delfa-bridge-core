import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


class TraceabilityMatrix:
    """
    TM — Traceability Matrix | Panohayan™
    Logger centralizado de trazabilidad.
    Registra cada acción de cada componente sobre cada entidad.
    Permite reconstruir el estado completo en cualquier momento histórico.
    """

    # Componentes válidos
    COMPONENTES = ["DII", "EDB", "GRG", "TM", "MR", "API", "INTENT", "RI"]

    # Acciones válidas
    ACCIONES = [
        "document_registered",
        "document_processed",
        "document_failed",
        "extracted",
        "embedded",
        "searched",
        "approved",
        "flagged",
        "quarantined",
        "blocked",
        "redacted",
        "resolved",
        "api_call",
        "intent_analyzed",
        "response_generated"
    ]

    def __init__(self, org_id: str = None):
        self.org_id = org_id or os.getenv("ORG_ID", "default")
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )

    # ── Log principal ────────────────────────────────────────────────────────

    def log(self,
            component: str,
            action: str,
            document_id: str = None,
            entity_id: str = None,
            actor: str = "system",
            before_value: dict = None,
            after_value: dict = None,
            detail: dict = None) -> str:
        """
        Registra una acción en el audit trail.
        Retorna el ID del registro creado.
        """
        try:
            resultado = self.supabase.table("audit_trail").insert({
                "org_id": self.org_id,
                "document_id": document_id,
                "entity_id": entity_id,
                "component": component,
                "action": action,
                "actor": actor,
                "before_value": before_value or {},
                "after_value": after_value or {},
                "detail": detail or {}
            }).execute()

            return resultado.data[0]["id"]

        except Exception as e:
            print(f"  [TM] Error registrando acción: {e}")
            return None

    # ── Consultas de trazabilidad ────────────────────────────────────────────

    def get_document_trail(self, document_id: str) -> list:
        """
        Trazabilidad completa de un documento.
        Retorna todas las acciones en orden cronológico.
        """
        resultado = self.supabase.table("audit_trail").select(
            "*"
        ).eq("document_id", document_id).eq(
            "org_id", self.org_id
        ).order("created_at").execute()

        return resultado.data

    def get_entity_trail(self, entity_id: str) -> list:
        """
        Trazabilidad completa de una entidad específica.
        """
        resultado = self.supabase.table("audit_trail").select(
            "*"
        ).eq("entity_id", entity_id).eq(
            "org_id", self.org_id
        ).order("created_at").execute()

        return resultado.data

    def get_recent_activity(self, limit: int = 20) -> list:
        """
        Actividad reciente de la organización.
        """
        resultado = self.supabase.table("audit_trail").select(
            "component, action, actor, created_at, detail"
        ).eq("org_id", self.org_id).order(
            "created_at", desc=True
        ).limit(limit).execute()

        return resultado.data

    def get_component_summary(self) -> dict:
        """
        Resumen de actividad por componente.
        """
        resultado = self.supabase.table("audit_trail").select(
            "component, action"
        ).eq("org_id", self.org_id).execute()

        resumen = {}
        for registro in resultado.data:
            comp = registro["component"]
            if comp not in resumen:
                resumen[comp] = {}
            accion = registro["action"]
            resumen[comp][accion] = resumen[comp].get(accion, 0) + 1

        return resumen

    def reconstruir_estado_entidad(self, entity_id: str) -> dict:
        """
        Reconstruye el historial completo de una entidad.
        Muestra cómo evolucionó desde su extracción hasta hoy.
        """
        trail = self.get_entity_trail(entity_id)

        historial = []
        for registro in trail:
            historial.append({
                "timestamp": registro["created_at"],
                "componente": registro["component"],
                "accion": registro["action"],
                "actor": registro["actor"],
                "detalle": registro.get("detail", {})
            })

        return {
            "entity_id": entity_id,
            "total_eventos": len(historial),
            "historial": historial
        }


if __name__ == "__main__":
    print("=" * 60)
    print("  TM — Traceability Matrix | Panohayan™")
    print("=" * 60)

    tm = TraceabilityMatrix()

    # Resumen de actividad por componente
    print("\n  [TEST] Resumen de actividad por componente:")
    resumen = tm.get_component_summary()
    for componente, acciones in resumen.items():
        print(f"\n    {componente}:")
        for accion, count in acciones.items():
            print(f"      → {accion}: {count}")

    # Actividad reciente
    print("\n  [TEST] Actividad reciente:")
    actividad = tm.get_recent_activity(limit=5)
    for a in actividad:
        print(f"    [{a['component']}] {a['action']} — {a['created_at'][:19]}")

    # Trazabilidad del documento más reciente
    resultado = tm.supabase.table("documents").select(
        "id, name"
    ).eq("org_id", tm.org_id).order(
        "created_at", desc=True
    ).limit(1).execute()

    if resultado.data:
        doc = resultado.data[0]
        print(f"\n  [TEST] Trail del documento: {doc['name']}")
        trail = tm.get_document_trail(doc["id"])
        print(f"  Total eventos: {len(trail)}")
        for evento in trail[:5]:
            print(f"    [{evento['component']}] {evento['action']} "
                  f"— {evento['created_at'][:19]}")
