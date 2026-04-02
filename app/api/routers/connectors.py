from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.api.auth import verificar_api_key

router = APIRouter(prefix="/connectors", tags=["connectors"])


class DriveRequest(BaseModel):
    folder_id: str


@router.post("/drive/process")
async def procesar_drive(
    request: DriveRequest,
    ctx: dict = Depends(verificar_api_key)
):
    """
    Procesa todos los documentos de una carpeta de Google Drive.
    Requiere GOOGLE_SERVICE_ACCOUNT_FILE o GOOGLE_CREDENTIALS_FILE en .env
    """
    try:
        import os
        os.environ["ORG_ID"] = ctx["org_id"]

        from app.connectors.google_drive import GoogleDriveConnector
        connector = GoogleDriveConnector()
        resumen = connector.procesar_carpeta(
            folder_id=request.folder_id,
            org_id=ctx["org_id"]
        )
        return resumen

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drive/files")
async def listar_drive(
    folder_id: str = None,
    ctx: dict = Depends(verificar_api_key)
):
    """Lista archivos disponibles en Google Drive."""
    try:
        from app.connectors.google_drive import GoogleDriveConnector
        connector = GoogleDriveConnector()
        archivos = connector.listar_archivos(folder_id=folder_id)
        return {"archivos": archivos, "total": len(archivos)}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        