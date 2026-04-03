import os
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# API key de desarrollo desde .env
DEV_API_KEY = os.getenv("API_KEY", "delfa-dev-key-2026")
DEV_ORG_ID = os.getenv("ORG_ID", "delfa-demo")


async def verificar_api_key(api_key: str = Security(API_KEY_HEADER)) -> dict:
    """
    Verifica la API Key contra:
    1. Key de desarrollo en .env (para testing)
    2. Tabla api_keys en Supabase (para producción)
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key requerida. Incluye el header X-API-Key."
        )

    # Verificación desarrollo
    if api_key == DEV_API_KEY:
        return {
            "org_id": DEV_ORG_ID,
            "plan": "development",
            "api_key": api_key
        }

    # Verificación producción — Supabase
    try:
        supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )

        resultado = supabase.table("api_keys").select(
            "org_id, plan, email, org_name, is_active"
        ).eq("api_key", api_key).eq("is_active", True).execute()

        if resultado.data:
            cliente = resultado.data[0]
            return {
                "org_id": cliente["org_id"],
                "plan": cliente["plan"],
                "email": cliente["email"],
                "org_name": cliente["org_name"],
                "api_key": api_key
            }

    except Exception as e:
        print(f"  [Auth] Error verificando API Key: {e}")

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="API Key inválida o inactiva."
    )
    