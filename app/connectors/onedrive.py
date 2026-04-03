import os
import io
import tempfile
import shutil
from app.connectors.msgraph_base import MSGraphConnector
from app.core.matrix import TraceabilityMatrix
from dotenv import load_dotenv

load_dotenv()


# ─── ONEDRIVE CONNECTOR | Panohayan™ ────────────────────────────────────────
#
# Descarga archivos de OneDrive via Microsoft Graph.
# Soporta: PDF, DOCX, XLSX, PPTX, CSV, TXT
# ─────────────────────────────────────────────────────────────────────────────

EXTENSIONES_SOPORTADAS = {
    "pdf", "docx", "doc", "xlsx", "xls", "csv",
    "txt", "html", "pptx", "png", "jpg", "jpeg"
}


class OneDriveConnector(MSGraphConnector):

    CONNECTOR_NAME = "onedrive"

    def __init__(self, client_id: str = None, client_secret: str = None,
                 tenant_id: str = None, user_id: str = None,
                 folder_path: str = None):
        super().__init__(client_id, client_secret, tenant_id)
        self.user_id = user_id or os.getenv("ONEDRIVE_USER_ID", "")
        self.folder_path = folder_path or ""

    def _user_prefix(self) -> str:
        if self.user_id:
            return f"/users/{self.user_id}/drive"
        return "/me/drive"

    def listar_archivos(self, folder_path: str = None) -> list:
        """Lista archivos en una carpeta de OneDrive."""
        path = folder_path or self.folder_path
        prefix = self._user_prefix()

        if path:
            endpoint = f"{prefix}/root:/{path}:/children"
        else:
            endpoint = f"{prefix}/root/children"

        items = self._graph_get_all(endpoint)

        archivos = []
        for item in items:
            if "file" not in item:
                continue
            nombre = item.get("name", "")
            extension = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
            if extension in EXTENSIONES_SOPORTADAS:
                archivos.append({
                    "id": item["id"],
                    "name": nombre,
                    "size": item.get("size", 0),
                    "lastModified": item.get("lastModifiedDateTime", ""),
                    "mimeType": item.get("file", {}).get("mimeType", "")
                })

        print(f"  [OneDrive] {len(archivos)} archivos soportados")
        return archivos

    def _descargar_archivo(self, item_id: str, filename: str,
                           tmp_dir: str) -> str:
        """Descarga un archivo de OneDrive."""
        prefix = self._user_prefix()
        url = f"{self.BASE_URL}{prefix}/items/{item_id}/content"

        response = self.session.get(url, timeout=60, allow_redirects=True)
        response.raise_for_status()

        ruta = os.path.join(tmp_dir, filename)
        with open(ruta, "wb") as f:
            f.write(response.content)

        print(f"  [OneDrive] Descargado: {filename}")
        return ruta

    def extraer_datos(self) -> dict:
        # No usado directamente — sincronizar() maneja el flujo
        return {}

    def sincronizar(self, org_id: str = None) -> dict:
        """Descarga archivos de OneDrive y los procesa via DII."""
        from app.core.dii import DigestInputIntelligence
        from app.core.grg import GovernanceGuardrails

        _org_id = org_id or os.getenv("ORG_ID", "default")
        tm = TraceabilityMatrix(org_id=_org_id)

        if not self.autenticar():
            return {"error": "No se pudo autenticar con OneDrive"}
        self._autenticado = True

        resumen = {
            "conector": "onedrive",
            "archivos_procesados": 0,
            "entidades_totales": 0,
            "errores": []
        }

        archivos = self.listar_archivos()

        for archivo in archivos:
            tmp_dir = tempfile.mkdtemp()

            try:
                self._descargar_archivo(
                    item_id=archivo["id"],
                    filename=archivo["name"],
                    tmp_dir=tmp_dir
                )

                dii = DigestInputIntelligence(org_id=_org_id)
                dii.data_path = tmp_dir
                entidades = dii.run_dii_pipeline()

                from supabase import create_client
                supabase = create_client(
                    os.getenv("SUPABASE_URL"),
                    os.getenv("SUPABASE_KEY")
                )
                doc = supabase.table("documents").select("id").eq(
                    "org_id", _org_id
                ).order("created_at", desc=True).limit(1).execute()

                if doc.data:
                    grg = GovernanceGuardrails(org_id=_org_id)
                    grg.evaluar_documento(doc.data[0]["id"])

                resumen["archivos_procesados"] += 1
                resumen["entidades_totales"] += len(entidades)

                tm.log(
                    component="DII",
                    action="onedrive_file_processed",
                    detail={
                        "file_name": archivo["name"],
                        "entidades": len(entidades)
                    }
                )

            except Exception as e:
                resumen["errores"].append(f"{archivo['name']}: {str(e)}")
                print(f"  [OneDrive] Error: {e}")

            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        print(f"  [OneDrive] Resumen: {resumen}")
        return resumen
