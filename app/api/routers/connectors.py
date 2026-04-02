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
    
class MicroSipRequest(BaseModel):
    base_url: str = None
    username: str = None
    password: str = None
    selected_db: str = None


@router.post("/microsip/process")
async def procesar_microsip(
    request: MicroSipRequest = None,
    ctx: dict = Depends(verificar_api_key)
):
    """
    Extrae y procesa datos de MicroSip ERP via API REST.
    Usa credenciales del .env si no se proporcionan.
    """
    try:
        import os
        os.environ["ORG_ID"] = ctx["org_id"]

        from app.connectors.microsip import MicroSipConnector
        connector = MicroSipConnector(
            base_url=request.base_url if request else None,
            username=request.username if request else None,
            password=request.password if request else None,
            selected_db=request.selected_db if request else None
        )
        resumen = connector.procesar_erp(org_id=ctx["org_id"])
        return resumen

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/microsip/login")
async def test_microsip_login(
    request: MicroSipRequest,
    ctx: dict = Depends(verificar_api_key)
):
    """Verifica conectividad con MicroSip ERP."""
    try:
        from app.connectors.microsip import MicroSipConnector
        connector = MicroSipConnector(
            base_url=request.base_url,
            username=request.username,
            password=request.password,
            selected_db=request.selected_db
        )
        success = connector.login()
        return {
            "connected": success,
            "base_url": request.base_url,
            "selected_db": request.selected_db
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class MicroSipDBRequest(BaseModel):
    db_type: str = "mysql"
    host: str
    port: int = 3306
    database: str
    username: str
    password: str


@router.post("/microsip/db/connect")
async def test_microsip_db(
    request: MicroSipDBRequest,
    ctx: dict = Depends(verificar_api_key)
):
    """Verifica conectividad directa a la BD de MicroSip."""
    try:
        from app.connectors.microsip import MicroSipDBConnector
        connector = MicroSipDBConnector(
            db_type=request.db_type,
            host=request.host,
            port=request.port,
            database=request.database,
            username=request.username,
            password=request.password
        )
        connected = connector.conectar()
        tablas = connector.listar_tablas() if connected else []
        return {
            "connected": connected,
            "db_type": request.db_type,
            "host": request.host,
            "database": request.database,
            "tablas_disponibles": tablas
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/microsip/db/process")
async def procesar_microsip_db(
    request: MicroSipDBRequest,
    ctx: dict = Depends(verificar_api_key)
):
    """Extrae y procesa datos directamente de la BD de MicroSip."""
    try:
        import os
        os.environ["ORG_ID"] = ctx["org_id"]

        from app.connectors.microsip import MicroSipDBConnector
        connector = MicroSipDBConnector(
            db_type=request.db_type,
            host=request.host,
            port=request.port,
            database=request.database,
            username=request.username,
            password=request.password
        )
        resumen = connector.procesar_erp_db(org_id=ctx["org_id"])
        return resumen
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
class MicroSipFileRequest(BaseModel):
    directorio: str = None


@router.post("/microsip/files/process")
async def procesar_microsip_files(
    request: MicroSipFileRequest = None,
    ctx: dict = Depends(verificar_api_key)
):
    """
    Procesa archivos exportados de MicroSip (XML CFDI, CSV, PDF).
    Coloca los archivos en el directorio configurado en MICROSIP_EXPORT_DIR.
    """
    try:
        import os
        os.environ["ORG_ID"] = ctx["org_id"]

        from app.connectors.microsip import MicroSipFileConnector
        connector = MicroSipFileConnector(
            directorio=request.directorio if request else None
        )
        resumen = connector.procesar_directorio(org_id=ctx["org_id"])
        return resumen
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

        