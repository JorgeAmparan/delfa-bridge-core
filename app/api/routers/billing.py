import os
import stripe
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from app.api.auth import verificar_api_key
from dotenv import load_dotenv

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

router = APIRouter(prefix="/billing", tags=["billing"])

# ─── PLANES DE SUSCRIPCIÓN ────────────────────────────────────────────────────
# Configura estos IDs después de crear los productos en Stripe Dashboard

PLANES = {
    "starter": {
        "nombre": "Starter",
        "precio_id": os.getenv("STRIPE_PRICE_STARTER"),
        "descripcion": "3 conectores, 10K entidades/mes",
        "precio": "$X USD/mes"
    },
    "professional": {
        "nombre": "Professional",
        "precio_id": os.getenv("STRIPE_PRICE_PROFESSIONAL"),
        "descripcion": "8 conectores, 100K entidades/mes",
        "precio": "$X USD/mes"
    },
    "enterprise": {
        "nombre": "Enterprise",
        "precio_id": os.getenv("STRIPE_PRICE_ENTERPRISE"),
        "descripcion": "Conectores ilimitados, SLA",
        "precio": "Negociado"
    }
}


# ── Modelos ───────────────────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    plan: str
    email: str
    org_name: str
    success_url: str = "https://delfa.bridge/success"
    cancel_url: str = "https://delfa.bridge/cancel"


class PortalRequest(BaseModel):
    customer_id: str
    return_url: str = "https://delfa.bridge/dashboard"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/plans")
async def listar_planes():
    """Lista los planes disponibles de Delfa Bridge."""
    return {
        "planes": [
            {
                "id": plan_id,
                "nombre": info["nombre"],
                "descripcion": info["descripcion"],
                "precio": info["precio"]
            }
            for plan_id, info in PLANES.items()
        ]
    }


@router.post("/checkout")
async def crear_checkout(request: CheckoutRequest):
    """
    Crea una sesión de checkout en Stripe.
    Retorna URL para redirigir al usuario al pago.
    """
    plan = PLANES.get(request.plan)
    if not plan:
        raise HTTPException(
            status_code=400,
            detail=f"Plan no válido. Opciones: {list(PLANES.keys())}"
        )

    if not plan["precio_id"]:
        raise HTTPException(
            status_code=400,
            detail=f"Plan {request.plan} no configurado en Stripe todavía."
        )

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            customer_email=request.email,
            line_items=[{
                "price": plan["precio_id"],
                "quantity": 1
            }],
            metadata={
                "org_name": request.org_name,
                "plan": request.plan,
                "email": request.email
            },
            success_url=request.success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.cancel_url
        )

        return {
            "checkout_url": session.url,
            "session_id": session.id,
            "plan": request.plan
        }

    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/portal")
async def portal_cliente(request: PortalRequest):
    """
    Crea sesión del portal de cliente Stripe.
    Permite al cliente gestionar su suscripción, facturas y método de pago.
    """
    try:
        session = stripe.billing_portal.Session.create(
            customer=request.customer_id,
            return_url=request.return_url
        )
        return {"portal_url": session.url}

    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhook")
async def webhook_stripe(request: Request):
    """
    Webhook de Stripe — procesa eventos de suscripción.
    Configura esta URL en Stripe Dashboard → Webhooks.
    URL: https://delfa-api-production.up.railway.app/billing/webhook
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    if not webhook_secret:
        raise HTTPException(status_code=500, detail="STRIPE_WEBHOOK_SECRET no configurado")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Payload inválido")
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Firma inválida")

    # Manejar eventos de suscripción
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        await _activar_suscripcion(session)

    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        await _cancelar_suscripcion(subscription)

    elif event["type"] == "invoice.payment_failed":
        invoice = event["data"]["object"]
        await _pago_fallido(invoice)

    return {"status": "ok"}


# ── Handlers internos ─────────────────────────────────────────────────────────

async def _activar_suscripcion(session: dict):
    """
    Activa la suscripción después de pago exitoso.
    Genera API Key y notifica al cliente.
    """
    import secrets
    import hashlib

    email = session.get("customer_email")
    org_name = session.get("metadata", {}).get("org_name", "")
    plan = session.get("metadata", {}).get("plan", "starter")
    customer_id = session.get("customer")

    # Generar API Key única para esta organización
    raw_key = secrets.token_urlsafe(32)
    org_id = hashlib.sha256(email.encode()).hexdigest()[:16]
    api_key = f"db_{raw_key}"

    # Guardar en Supabase
    from supabase import create_client
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

    # Crear tabla api_keys si no existe — o insertar
    try:
        supabase.table("api_keys").insert({
            "org_id": org_id,
            "api_key": api_key,
            "email": email,
            "org_name": org_name,
            "plan": plan,
            "stripe_customer_id": customer_id,
            "is_active": True
        }).execute()
    except Exception as e:
        print(f"  [Billing] Error guardando API Key: {e}")

    print(f"  [Billing] ✅ Suscripción activada: {email} | Plan: {plan} | org_id: {org_id}")


async def _cancelar_suscripcion(subscription: dict):
    """Desactiva la API Key cuando se cancela la suscripción."""
    customer_id = subscription.get("customer")

    from supabase import create_client
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

    try:
        supabase.table("api_keys").update({
            "is_active": False
        }).eq("stripe_customer_id", customer_id).execute()
        print(f"  [Billing] ❌ Suscripción cancelada: {customer_id}")
    except Exception as e:
        print(f"  [Billing] Error cancelando suscripción: {e}")


async def _pago_fallido(invoice: dict):
    """Log de pago fallido."""
    customer_id = invoice.get("customer")
    print(f"  [Billing] ⚠️ Pago fallido: {customer_id}")
    