from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.auth import requiere_rol
from app.core.grg import GovernanceGuardrails

router = APIRouter(prefix="/governance", tags=["governance"])


class ReglaRequest(BaseModel):
    entity_class: str
    rule_type: str
    action: str
    condition: Optional[dict] = {}


@router.post("/rules")
async def crear_regla(
    request: ReglaRequest,
    ctx: dict = Depends(requiere_rol("admin", "editor"))
):
    """Crea una nueva regla de gobernanza para la organización."""
    grg = GovernanceGuardrails(org_id=ctx["org_id"])
    rule_id = grg.crear_regla(
        entity_class=request.entity_class,
        rule_type=request.rule_type,
        action=request.action,
        condition=request.condition
    )

    return {
        "status": "created",
        "rule_id": rule_id,
        "entity_class": request.entity_class,
        "action": request.action
    }


@router.get("/rules")
async def listar_reglas(ctx: dict = Depends(requiere_rol("admin", "editor", "viewer"))):
    """Lista todas las reglas activas de la organización."""
    from dotenv import load_dotenv
    from supabase import create_client

    # FUERA DE ALCANCE MVP (Adenda 31-may-2026): rutas de UI #3 PM (diferida).
    # Falla loud sin DOCYAN_ENABLE_GOVERNANCE=1.
    from app.core.supabase_client import require_module_enabled, require_supabase_config
    load_dotenv()

    require_module_enabled("governance")
    _url, _key = require_supabase_config("governance", service=True)
    supabase = create_client(_url, _key)

    resultado = supabase.table("governance_rules").select("*").eq(
        "org_id", ctx["org_id"]
    ).eq("is_active", True).execute()

    return {"reglas": resultado.data}
