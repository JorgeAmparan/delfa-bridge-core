import os
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Para desarrollo — API key hardcodeada en .env
# En producción vendrá de Supabase tabla api_keys
DEV_API_KEY = os.getenv("API_KEY", "delfa-dev-key-2026")
DEV_ORG_ID = os.getenv("ORG_ID", "delfa-demo")


async def verificar_api_key(api_key: str = Security(API_KEY_HEADER)) -> dict:
    """
    Verifica la API Key y retorna el contexto de la organización.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key requerida. Incluye el header X-API-Key."
        )

    # En desarrollo — verificación simple contra .env
    if api_key == DEV_API_KEY:
        return {
            "org_id": DEV_ORG_ID,
            "plan": "development",
            "api_key": api_key
        }

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="API Key inválida."
    )