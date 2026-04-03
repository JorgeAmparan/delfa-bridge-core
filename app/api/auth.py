import os
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, HTTPException, Security, Depends, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# ── Config ───────────────────────────────────────────────────────────────────

JWT_SECRET = os.getenv("JWT_SECRET", "delfa-jwt-secret-change-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
BEARER_SCHEME = HTTPBearer(auto_error=False)

DEV_API_KEY = os.getenv("API_KEY", "delfa-dev-key-2026")
DEV_ORG_ID = os.getenv("ORG_ID", "delfa-demo")

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Helpers ──────────────────────────────────────────────────────────────────

def _supabase() -> Client:
    """Cliente Supabase con service_role key — bypasea RLS para operaciones de auth."""
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _create_access_token(user: dict) -> str:
    payload = {
        "sub": user["id"],
        "org_id": user["org_id"],
        "role": user["role"],
        "email": user["email"],
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _create_refresh_token(user_id: str) -> tuple[str, datetime]:
    raw_token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    _supabase().table("refresh_tokens").insert({
        "user_id": user_id,
        "token_hash": _hash_token(raw_token),
        "expires_at": expires_at.isoformat(),
    }).execute()

    return raw_token, expires_at


# ── Modelos ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    org_name: str | None = None
    role: str = "viewer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Auth unificado (JWT + API Key) ───────────────────────────────────────────

async def verificar_credenciales(
    api_key: str = Security(API_KEY_HEADER),
    bearer: HTTPAuthorizationCredentials = Security(BEARER_SCHEME),
) -> dict:
    """
    Acepta JWT (Authorization: Bearer) o API Key (X-API-Key).
    Retorna ctx dict compatible con el existente + user_id y role.
    """

    # ── Opcion 1: JWT Bearer ──
    if bearer and bearer.credentials:
        try:
            payload = jwt.decode(bearer.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return {
                "org_id": payload["org_id"],
                "user_id": payload["sub"],
                "role": payload["role"],
                "email": payload["email"],
                "plan": None,
                "api_key": None,
            }
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expirado.")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Token invalido.")

    # ── Opcion 2: API Key ──
    if api_key:
        # Dev key
        if api_key == DEV_API_KEY:
            return {
                "org_id": DEV_ORG_ID,
                "plan": "development",
                "api_key": api_key,
                "user_id": None,
                "role": "admin",
                "email": None,
            }

        # Produccion — tabla api_keys
        try:
            sb = _supabase()
            resultado = sb.table("api_keys").select(
                "org_id, plan, email, org_name, is_active"
            ).eq("api_key", api_key).eq("is_active", True).execute()

            if resultado.data:
                cliente = resultado.data[0]
                return {
                    "org_id": cliente["org_id"],
                    "plan": cliente["plan"],
                    "email": cliente.get("email"),
                    "org_name": cliente.get("org_name"),
                    "api_key": api_key,
                    "user_id": None,
                    "role": "admin",
                }
        except Exception as e:
            print(f"  [Auth] Error verificando API Key: {e}")

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Autenticacion requerida. Usa header Authorization: Bearer <jwt> o X-API-Key."
    )


async def verificar_credenciales_opcional(
    api_key: str = Security(API_KEY_HEADER),
    bearer: HTTPAuthorizationCredentials = Security(BEARER_SCHEME),
) -> dict | None:
    """
    Igual que verificar_credenciales pero retorna None si no hay auth.
    Para endpoints con auth opcional (ej: auto-registro).
    """
    if not bearer and not api_key:
        return None
    return await verificar_credenciales(api_key=api_key, bearer=bearer)


# Backward compat: alias para que routers existentes no rompan
verificar_api_key = verificar_credenciales


# ── Decorador de permisos ────────────────────────────────────────────────────

def requiere_rol(*roles_permitidos: str):
    """
    Dependency que valida el rol del usuario contra la lista permitida.
    Uso: Depends(requiere_rol("admin", "editor"))
    """
    async def _check(ctx: dict = Depends(verificar_credenciales)):
        if ctx.get("role") not in roles_permitidos:
            raise HTTPException(
                status_code=403,
                detail=f"Rol '{ctx.get('role')}' no tiene permiso. Requiere: {', '.join(roles_permitidos)}"
            )
        return ctx
    return _check


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/register")
async def register(
    request: RegisterRequest,
    ctx: dict | None = Depends(verificar_credenciales_opcional),
):
    """
    Registra un usuario.
    - Primer usuario de una org: se auto-registra como admin (sin auth).
    - Usuarios adicionales: requiere JWT de un admin de esa org.
    """
    sb = _supabase()

    # Verificar email duplicado
    existe = sb.table("users").select("id").eq("email", request.email).execute()
    if existe.data:
        raise HTTPException(status_code=409, detail="Email ya registrado.")

    if ctx and ctx.get("user_id"):
        # ── Admin creando usuario adicional ──
        if ctx.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Solo admin puede crear usuarios.")

        org_id = ctx["org_id"]
        role = request.role if request.role in ("admin", "editor", "viewer") else "viewer"
    else:
        # ── Auto-registro: primer usuario de la org ──
        if not request.org_name:
            raise HTTPException(
                status_code=400,
                detail="org_name requerido para registrar una nueva organizacion."
            )
        org_id = hashlib.sha256(request.email.encode()).hexdigest()[:16]

        # Verificar que no existan usuarios en esta org
        org_users = sb.table("users").select("id").eq("org_id", org_id).limit(1).execute()
        if org_users.data:
            raise HTTPException(
                status_code=403,
                detail="Esta organizacion ya tiene usuarios. Pide a un admin que te registre."
            )
        role = "admin"

    # Crear usuario
    password_hash = bcrypt.hashpw(request.password.encode(), bcrypt.gensalt()).decode()
    nuevo = sb.table("users").insert({
        "org_id": org_id,
        "email": request.email,
        "password_hash": password_hash,
        "role": role,
        "name": request.name,
    }).execute()

    user = nuevo.data[0]

    return {
        "status": "created",
        "user_id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "org_id": user["org_id"],
    }


@router.post("/login")
async def login(request: LoginRequest):
    """Login con email + password. Retorna access_token + refresh_token."""
    sb = _supabase()

    resultado = sb.table("users").select(
        "id, org_id, email, password_hash, role, name, is_active"
    ).eq("email", request.email).execute()

    if not resultado.data:
        raise HTTPException(status_code=401, detail="Credenciales invalidas.")

    user = resultado.data[0]

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Usuario desactivado.")

    if not bcrypt.checkpw(request.password.encode(), user["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Credenciales invalidas.")

    access_token = _create_access_token(user)
    refresh_token, expires_at = _create_refresh_token(user["id"])

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "org_id": user["org_id"],
        },
    }


@router.post("/refresh")
async def refresh(request: RefreshRequest):
    """Rota el refresh token y emite nuevo access_token."""
    sb = _supabase()
    token_hash = _hash_token(request.refresh_token)

    resultado = sb.table("refresh_tokens").select(
        "id, user_id, expires_at, revoked"
    ).eq("token_hash", token_hash).execute()

    if not resultado.data:
        raise HTTPException(status_code=401, detail="Refresh token invalido.")

    token_row = resultado.data[0]

    if token_row["revoked"]:
        raise HTTPException(status_code=401, detail="Refresh token revocado.")

    if datetime.fromisoformat(token_row["expires_at"]) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expirado.")

    # Revocar token usado
    sb.table("refresh_tokens").update(
        {"revoked": True}
    ).eq("id", token_row["id"]).execute()

    # Obtener usuario
    user_result = sb.table("users").select(
        "id, org_id, email, role, name, is_active"
    ).eq("id", token_row["user_id"]).execute()

    if not user_result.data or not user_result.data[0]["is_active"]:
        raise HTTPException(status_code=403, detail="Usuario desactivado.")

    user = user_result.data[0]
    access_token = _create_access_token(user)
    new_refresh, expires_at = _create_refresh_token(user["id"])

    return {
        "access_token": access_token,
        "refresh_token": new_refresh,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.get("/me")
async def me(ctx: dict = Depends(verificar_credenciales)):
    """Retorna info del usuario autenticado."""
    sb = _supabase()

    if not ctx.get("user_id"):
        # Auth via API Key (sin user en tabla users)
        return {
            "auth_type": "api_key",
            "org_id": ctx["org_id"],
            "email": ctx.get("email"),
            "role": ctx.get("role"),
            "plan": ctx.get("plan"),
        }

    user_result = sb.table("users").select(
        "id, org_id, email, name, role, is_active, created_at"
    ).eq("id", ctx["user_id"]).execute()

    if not user_result.data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    user = user_result.data[0]
    return {
        "auth_type": "jwt",
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "org_id": user["org_id"],
        "is_active": user["is_active"],
        "created_at": user["created_at"],
    }
