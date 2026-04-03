from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from app.api.auth import requiere_rol

router = APIRouter(prefix="/connectors", tags=["connectors"])


class DriveRequest(BaseModel):
    folder_id: str


@router.post("/drive/process")
async def procesar_drive(
    request: DriveRequest,
    ctx: dict = Depends(requiere_rol("admin", "editor"))
):
    """
    Procesa todos los documentos de una carpeta de Google Drive.
    Requiere GOOGLE_SERVICE_ACCOUNT_FILE o GOOGLE_CREDENTIALS_FILE en .env
    """
    try:
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
    ctx: dict = Depends(requiere_rol("admin", "editor", "viewer"))
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
    ctx: dict = Depends(requiere_rol("admin", "editor"))
):
    """
    Extrae y procesa datos de MicroSip ERP via API REST.
    Usa credenciales del .env si no se proporcionan.
    """
    try:
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
    ctx: dict = Depends(requiere_rol("admin", "editor"))
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
    ctx: dict = Depends(requiere_rol("admin", "editor"))
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
    ctx: dict = Depends(requiere_rol("admin", "editor"))
):
    """Extrae y procesa datos directamente de la BD de MicroSip."""
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
        resumen = connector.procesar_erp_db(org_id=ctx["org_id"])
        return resumen
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
class MicroSipFileRequest(BaseModel):
    directorio: str = None


@router.post("/microsip/files/process")
async def procesar_microsip_files(
    request: MicroSipFileRequest = None,
    ctx: dict = Depends(requiere_rol("admin", "editor"))
):
    """
    Procesa archivos exportados de MicroSip (XML CFDI, CSV, PDF).
    Coloca los archivos en el directorio configurado en MICROSIP_EXPORT_DIR.
    """
    try:
        from app.connectors.microsip import MicroSipFileConnector
        connector = MicroSipFileConnector(
            directorio=request.directorio if request else None
        )
        resumen = connector.procesar_directorio(org_id=ctx["org_id"])
        return resumen
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SQLConnectRequest(BaseModel):
    db_type: str = "mysql"
    host: str
    port: int = 3306
    database: str
    username: str
    password: str
    connection_string: str = None


class SQLQueryRequest(BaseModel):
    db_type: str = "mysql"
    host: str
    port: int = 3306
    database: str
    username: str
    password: str
    tabla: str = None
    tablas: list = None
    limite: int = 100
    connection_string: str = None


@router.post("/sql/connect")
async def test_sql_connection(
    request: SQLConnectRequest,
    ctx: dict = Depends(requiere_rol("admin", "editor"))
):
    """Verifica conectividad a cualquier base de datos SQL."""
    try:
        from app.connectors.sql import SQLConnector
        connector = SQLConnector(
            db_type=request.db_type,
            host=request.host,
            port=request.port,
            database=request.database,
            username=request.username,
            password=request.password,
            connection_string=request.connection_string
        )
        connected = connector.conectar()
        tablas = connector.listar_tablas() if connected else []
        return {
            "connected": connected,
            "db_type": request.db_type,
            "database": request.database,
            "tablas": tablas
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sql/process")
async def procesar_sql(
    request: SQLQueryRequest,
    ctx: dict = Depends(requiere_rol("admin", "editor"))
):
    """
    Procesa tablas de una BD SQL a través del pipeline Panohayan™.
    Si tabla está definida, procesa solo esa tabla.
    Si tablas es una lista, procesa esas tablas.
    Si ninguno está definido, procesa toda la BD.
    """
    try:
        from app.connectors.sql import SQLConnector
        connector = SQLConnector(
            db_type=request.db_type,
            host=request.host,
            port=request.port,
            database=request.database,
            username=request.username,
            password=request.password,
            connection_string=request.connection_string
        )

        if request.tabla:
            resultado = connector.procesar_tabla(
                tabla=request.tabla,
                limite=request.limite,
                org_id=ctx["org_id"]
            )
        else:
            resultado = connector.procesar_base_completa(
                tablas=request.tablas,
                limite_por_tabla=request.limite,
                org_id=ctx["org_id"]
            )

        return resultado

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── WEBHOOK-BASED CONNECTORS ───────────────────────────────────────────────


class WebhookPayload(BaseModel):
    data: Optional[dict] = None
    text: Optional[str] = None
    content: Optional[str] = None
    body: Optional[str] = None
    message: Optional[str] = None
    files: Optional[list] = None
    attachments: Optional[list] = None

    class Config:
        extra = "allow"


def _webhook_endpoint(connector_class, payload: dict, secret: str,
                      org_id: str):
    """Helper para todos los endpoints webhook."""
    connector = connector_class()
    if not connector.validar_secret(secret):
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    return connector.procesar(payload, org_id=org_id)


@router.post("/webhook/receive")
async def webhook_generico(
    request: Request,
    ctx: dict = Depends(requiere_rol("admin", "editor"))
):
    """Webhook genérico — recibe cualquier payload JSON."""
    try:
        payload = await request.json()
        from app.connectors.webhook import GenericWebhookConnector
        connector = GenericWebhookConnector()
        secret = request.headers.get("X-Webhook-Secret", "")
        if not connector.validar_secret(secret):
            raise HTTPException(
                status_code=401, detail="Invalid webhook secret"
            )
        return connector.procesar(payload, org_id=ctx["org_id"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/make/webhook")
async def make_webhook(
    request: Request,
    ctx: dict = Depends(requiere_rol("admin", "editor"))
):
    """Recibe datos desde escenarios de Make (Integromat)."""
    try:
        payload = await request.json()
        from app.connectors.make import MakeConnector
        connector = MakeConnector()
        secret = request.headers.get("X-Webhook-Secret", "")
        if not connector.validar_secret(secret):
            raise HTTPException(
                status_code=401, detail="Invalid webhook secret"
            )
        return connector.procesar(payload, org_id=ctx["org_id"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/zapier/webhook")
async def zapier_webhook(
    request: Request,
    ctx: dict = Depends(requiere_rol("admin", "editor"))
):
    """Recibe datos desde Zaps de Zapier."""
    try:
        payload = await request.json()
        from app.connectors.zapier import ZapierConnector
        connector = ZapierConnector()
        secret = request.headers.get("X-Webhook-Secret", "")
        if not connector.validar_secret(secret):
            raise HTTPException(
                status_code=401, detail="Invalid webhook secret"
            )
        return connector.procesar(payload, org_id=ctx["org_id"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/n8n/webhook")
async def n8n_webhook(
    request: Request,
    ctx: dict = Depends(requiere_rol("admin", "editor"))
):
    """Recibe datos desde workflows de n8n."""
    try:
        payload = await request.json()
        from app.connectors.n8n import N8nConnector
        connector = N8nConnector()
        secret = request.headers.get("X-Webhook-Secret", "")
        if not connector.validar_secret(secret):
            raise HTTPException(
                status_code=401, detail="Invalid webhook secret"
            )
        return connector.procesar(payload, org_id=ctx["org_id"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bubble/process")
async def bubble_process(
    request: Request,
    ctx: dict = Depends(requiere_rol("admin", "editor"))
):
    """Recibe datos desde apps Bubble.io."""
    try:
        payload = await request.json()
        from app.connectors.bubble import BubbleConnector
        connector = BubbleConnector()
        return connector.procesar(payload, org_id=ctx["org_id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lovable/process")
async def lovable_process(
    request: Request,
    ctx: dict = Depends(requiere_rol("admin", "editor"))
):
    """Recibe datos desde apps generadas con Lovable."""
    try:
        payload = await request.json()
        from app.connectors.lovable import LovableConnector
        connector = LovableConnector()
        return connector.procesar(payload, org_id=ctx["org_id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chrome-ext/process")
async def chrome_ext_process(
    request: Request,
    ctx: dict = Depends(requiere_rol("admin", "editor"))
):
    """Recibe datos capturados por la extensión de Chrome."""
    try:
        payload = await request.json()
        from app.connectors.chrome_ext import ChromeExtConnector
        connector = ChromeExtConnector()
        return connector.procesar(payload, org_id=ctx["org_id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── API-BASED CONNECTORS ───────────────────────────────────────────────────


class NotionRequest(BaseModel):
    token: Optional[str] = None
    database_ids: Optional[list] = None
    page_ids: Optional[list] = None


@router.post("/notion/sync")
async def notion_sync(
    request: NotionRequest,
    ctx: dict = Depends(requiere_rol("admin", "editor"))
):
    """Sincroniza páginas y bases de datos de Notion."""
    try:
        from app.connectors.notion import NotionConnector
        connector = NotionConnector(
            token=request.token,
            database_ids=request.database_ids or [],
            page_ids=request.page_ids or []
        )
        return connector.sincronizar(org_id=ctx["org_id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class HubSpotRequest(BaseModel):
    api_key: Optional[str] = None
    objetos: Optional[list] = None


@router.post("/hubspot/sync")
async def hubspot_sync(
    request: HubSpotRequest,
    ctx: dict = Depends(requiere_rol("admin", "editor"))
):
    """Sincroniza contactos, deals y companies de HubSpot."""
    try:
        from app.connectors.hubspot import HubSpotConnector
        connector = HubSpotConnector(
            api_key=request.api_key,
            objetos=request.objetos
        )
        return connector.sincronizar(org_id=ctx["org_id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PipedriveRequest(BaseModel):
    api_token: Optional[str] = None
    domain: Optional[str] = None
    objetos: Optional[list] = None


@router.post("/pipedrive/sync")
async def pipedrive_sync(
    request: PipedriveRequest,
    ctx: dict = Depends(requiere_rol("admin", "editor"))
):
    """Sincroniza deals, persons y organizations de Pipedrive."""
    try:
        from app.connectors.pipedrive import PipedriveConnector
        connector = PipedriveConnector(
            api_token=request.api_token,
            domain=request.domain,
            objetos=request.objetos
        )
        return connector.sincronizar(org_id=ctx["org_id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class BindERPRequest(BaseModel):
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    objetos: Optional[list] = None


@router.post("/binderp/sync")
async def binderp_sync(
    request: BindERPRequest,
    ctx: dict = Depends(requiere_rol("admin", "editor"))
):
    """Sincroniza facturas, clientes, productos e inventario de Bind ERP."""
    try:
        from app.connectors.binderp import BindERPConnector
        connector = BindERPConnector(
            api_key=request.api_key,
            base_url=request.base_url,
            objetos=request.objetos
        )
        return connector.sincronizar(org_id=ctx["org_id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
