import os
import base64
import tempfile
import shutil
from app.connectors.msgraph_base import MSGraphConnector
from app.core.matrix import TraceabilityMatrix
from dotenv import load_dotenv

load_dotenv()


# ─── OUTLOOK CONNECTOR | Panohayan™ ─────────────────────────────────────────
#
# Extrae correos y adjuntos de Outlook/Office 365 via Microsoft Graph.
# Procesa cuerpo + adjuntos a través del pipeline DII.
# ─────────────────────────────────────────────────────────────────────────────

EXTENSIONES_ADJUNTOS = {
    "pdf", "docx", "doc", "xlsx", "xls", "csv",
    "txt", "html", "htm", "png", "jpg", "jpeg", "pptx"
}


class OutlookConnector(MSGraphConnector):

    CONNECTOR_NAME = "outlook"

    def __init__(self, client_id: str = None, client_secret: str = None,
                 tenant_id: str = None, user_id: str = None,
                 folder: str = "inbox", max_results: int = 50,
                 filter_query: str = None):
        super().__init__(client_id, client_secret, tenant_id)
        self.user_id = user_id or os.getenv("OUTLOOK_USER_ID", "")
        self.folder = folder
        self.max_results = max_results
        self.filter_query = filter_query

    def _user_prefix(self) -> str:
        if self.user_id:
            return f"/users/{self.user_id}"
        return "/me"

    def _listar_correos(self) -> list:
        """Lista correos de la carpeta especificada."""
        prefix = self._user_prefix()
        endpoint = f"{prefix}/mailFolders/{self.folder}/messages"

        params = {
            "$top": self.max_results,
            "$orderby": "receivedDateTime desc",
            "$select": "id,subject,from,toRecipients,receivedDateTime,body,hasAttachments"
        }

        if self.filter_query:
            params["$filter"] = self.filter_query

        try:
            data = self._graph_get(endpoint, params=params)
            correos = data.get("value", [])
            print(f"  [Outlook] {len(correos)} correos encontrados")
            return correos
        except Exception as e:
            print(f"  [Outlook] Error listando correos: {e}")
            return []

    def _descargar_adjuntos(self, message_id: str, tmp_dir: str) -> list:
        """Descarga adjuntos soportados de un correo."""
        prefix = self._user_prefix()
        endpoint = f"{prefix}/messages/{message_id}/attachments"
        adjuntos_descargados = []

        try:
            data = self._graph_get(endpoint)
            for att in data.get("value", []):
                if att.get("@odata.type") != "#microsoft.graph.fileAttachment":
                    continue

                nombre = att.get("name", "")
                extension = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
                if extension not in EXTENSIONES_ADJUNTOS:
                    continue

                content = att.get("contentBytes", "")
                if content:
                    ruta = os.path.join(tmp_dir, nombre)
                    with open(ruta, "wb") as f:
                        f.write(base64.b64decode(content))
                    adjuntos_descargados.append(ruta)
                    print(f"  [Outlook] Adjunto: {nombre}")

        except Exception as e:
            print(f"  [Outlook] Error descargando adjuntos: {e}")

        return adjuntos_descargados

    def _correo_a_texto(self, correo: dict) -> str:
        """Convierte un correo de Graph API a texto estructurado."""
        lineas = ["=== CORREO DE OUTLOOK ===\n"]

        lineas.append(f"Subject: {correo.get('subject', '')}")
        lineas.append(f"Date: {correo.get('receivedDateTime', '')}")

        from_addr = correo.get("from", {}).get("emailAddress", {})
        lineas.append(f"From: {from_addr.get('name', '')} <{from_addr.get('address', '')}>")

        to_list = correo.get("toRecipients", [])
        to_addrs = ", ".join(
            f"{r.get('emailAddress', {}).get('name', '')} <{r.get('emailAddress', {}).get('address', '')}>"
            for r in to_list
        )
        if to_addrs:
            lineas.append(f"To: {to_addrs}")

        body = correo.get("body", {})
        content = body.get("content", "")
        if body.get("contentType") == "html" and content:
            import re
            content = re.sub(r"<[^>]+>", " ", content)
            content = re.sub(r"\s+", " ", content).strip()

        if content:
            lineas.append(f"\n--- CUERPO ---\n{content}")

        return "\n".join(lineas)

    def extraer_datos(self) -> dict:
        return {}

    def sincronizar(self, org_id: str = None) -> dict:
        """Extrae correos + adjuntos de Outlook y los procesa via DII."""
        from app.core.dii import DigestInputIntelligence
        from app.core.grg import GovernanceGuardrails

        _org_id = org_id or os.getenv("ORG_ID", "default")
        tm = TraceabilityMatrix(org_id=_org_id)

        if not self.autenticar():
            return {"error": "No se pudo autenticar con Outlook"}
        self._autenticado = True

        resumen = {
            "conector": "outlook",
            "correos_procesados": 0,
            "adjuntos_procesados": 0,
            "entidades_totales": 0,
            "errores": []
        }

        correos = self._listar_correos()

        for correo in correos:
            tmp_dir = tempfile.mkdtemp()

            try:
                texto = self._correo_a_texto(correo)
                correo_file = os.path.join(tmp_dir, f"outlook_{correo['id'][:12]}.txt")
                with open(correo_file, "w", encoding="utf-8") as f:
                    f.write(texto)

                adjuntos = []
                if correo.get("hasAttachments"):
                    adjuntos = self._descargar_adjuntos(correo["id"], tmp_dir)

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

                resumen["correos_procesados"] += 1
                resumen["adjuntos_procesados"] += len(adjuntos)
                resumen["entidades_totales"] += len(entidades)

                tm.log(
                    component="DII",
                    action="outlook_processed",
                    detail={
                        "message_id": correo["id"],
                        "subject": correo.get("subject", ""),
                        "adjuntos": len(adjuntos),
                        "entidades": len(entidades)
                    }
                )

            except Exception as e:
                resumen["errores"].append(f"{correo.get('subject', correo['id'])}: {str(e)}")
                print(f"  [Outlook] Error: {e}")

            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        print(f"  [Outlook] Resumen: {resumen}")
        return resumen
