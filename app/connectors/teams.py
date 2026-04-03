import os
import tempfile
import shutil
from app.connectors.msgraph_base import MSGraphConnector
from app.core.matrix import TraceabilityMatrix
from dotenv import load_dotenv

load_dotenv()


# ─── MICROSOFT TEAMS CONNECTOR | Panohayan™ ─────────────────────────────────
#
# Extrae mensajes y archivos de canales de Microsoft Teams via Graph API.
# Hereda de MSGraphConnector (auth Azure AD con msal).
# Soporta: mensajes de canales, archivos compartidos, respuestas (replies).
# ─────────────────────────────────────────────────────────────────────────────

EXTENSIONES_ARCHIVOS = {
    "pdf", "docx", "doc", "xlsx", "xls", "csv",
    "txt", "html", "pptx", "png", "jpg", "jpeg"
}


class TeamsConnector(MSGraphConnector):

    CONNECTOR_NAME = "teams"

    def __init__(self, client_id: str = None, client_secret: str = None,
                 tenant_id: str = None, team_id: str = None,
                 channel_ids: list = None, max_messages: int = 200):
        super().__init__(client_id, client_secret, tenant_id)
        self.team_id = team_id or os.getenv("TEAMS_TEAM_ID", "")
        self.channel_ids = channel_ids or []
        self.max_messages = max_messages

    def listar_teams(self) -> list:
        """Lista teams accesibles."""
        try:
            data = self._graph_get("/teams")
            teams = data.get("value", [])
            print(f"  [Teams] {len(teams)} teams encontrados")
            return [
                {"id": t["id"], "displayName": t.get("displayName", "")}
                for t in teams
            ]
        except Exception as e:
            print(f"  [Teams] Error listando teams: {e}")
            return []

    def listar_canales(self, team_id: str = None) -> list:
        """Lista canales de un team."""
        tid = team_id or self.team_id
        if not tid:
            print("  [Teams] Error: team_id no especificado")
            return []

        try:
            data = self._graph_get(f"/teams/{tid}/channels")
            canales = data.get("value", [])
            print(f"  [Teams] {len(canales)} canales en team")
            return [
                {"id": c["id"], "displayName": c.get("displayName", "")}
                for c in canales
            ]
        except Exception as e:
            print(f"  [Teams] Error listando canales: {e}")
            return []

    def _obtener_mensajes(self, team_id: str, channel_id: str) -> list:
        """Obtiene mensajes de un canal."""
        try:
            mensajes = self._graph_get_all(
                f"/teams/{team_id}/channels/{channel_id}/messages",
                limite=self.max_messages
            )

            resultado = []
            for msg in mensajes:
                if msg.get("messageType") != "message":
                    continue

                from_user = msg.get("from", {}).get("user", {})
                body = msg.get("body", {})
                content = body.get("content", "")

                # Limpiar HTML del body
                if body.get("contentType") == "html" and content:
                    import re
                    content = re.sub(r"<[^>]+>", " ", content)
                    content = re.sub(r"\s+", " ", content).strip()

                resultado.append({
                    "id": msg.get("id", ""),
                    "user": from_user.get("displayName", "unknown"),
                    "text": content,
                    "createdDateTime": msg.get("createdDateTime", ""),
                    "attachments": msg.get("attachments", [])
                })

            return resultado

        except Exception as e:
            print(f"  [Teams] Error obteniendo mensajes: {e}")
            return []

    def _obtener_archivos_canal(self, team_id: str, channel_id: str) -> list:
        """Obtiene archivos de la carpeta del canal en SharePoint."""
        try:
            data = self._graph_get(
                f"/teams/{team_id}/channels/{channel_id}/filesFolder"
            )
            folder_url = data.get("webUrl", "")
            drive_id = data.get("parentReference", {}).get("driveId", "")
            item_id = data.get("id", "")

            if not drive_id or not item_id:
                return []

            items = self._graph_get_all(
                f"/drives/{drive_id}/items/{item_id}/children"
            )

            archivos = []
            for item in items:
                if "file" not in item:
                    continue
                nombre = item.get("name", "")
                ext = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
                if ext in EXTENSIONES_ARCHIVOS:
                    archivos.append({
                        "id": item["id"],
                        "name": nombre,
                        "drive_id": drive_id,
                        "download_url": item.get("@microsoft.graph.downloadUrl", "")
                    })

            return archivos

        except Exception as e:
            print(f"  [Teams] Error obteniendo archivos: {e}")
            return []

    def _descargar_archivo(self, download_url: str, filename: str,
                           tmp_dir: str) -> str:
        """Descarga archivo de Teams/SharePoint."""
        try:
            response = self.session.get(download_url, timeout=60)
            response.raise_for_status()
            ruta = os.path.join(tmp_dir, filename)
            with open(ruta, "wb") as f:
                f.write(response.content)
            return ruta
        except Exception as e:
            print(f"  [Teams] Error descargando {filename}: {e}")
            return None

    def extraer_datos(self) -> dict:
        return {}

    def sincronizar(self, org_id: str = None) -> dict:
        """Extrae mensajes y archivos de Teams y los procesa via DII."""
        from app.core.dii import DigestInputIntelligence
        from app.core.grg import GovernanceGuardrails

        _org_id = org_id or os.getenv("ORG_ID", "default")
        tm = TraceabilityMatrix(org_id=_org_id)

        if not self.autenticar():
            return {"error": "No se pudo autenticar con Teams"}
        self._autenticado = True

        if not self.team_id:
            return {"error": "team_id es requerido"}

        resumen = {
            "conector": "teams",
            "canales_procesados": 0,
            "mensajes_totales": 0,
            "archivos_procesados": 0,
            "entidades_totales": 0,
            "errores": []
        }

        # Resolver canales
        if self.channel_ids:
            canales = [{"id": c, "displayName": c} for c in self.channel_ids]
        else:
            canales = self.listar_canales()

        for canal in canales:
            tmp_dir = tempfile.mkdtemp()
            canal_nombre = canal.get("displayName", canal["id"])

            try:
                # Mensajes del canal
                mensajes = self._obtener_mensajes(self.team_id, canal["id"])

                if mensajes:
                    lineas = [f"=== TEAMS — {canal_nombre} ===\n"]
                    for msg in mensajes:
                        lineas.append(
                            f"[{msg['createdDateTime']}] {msg['user']}: {msg['text']}"
                        )

                    texto_file = os.path.join(
                        tmp_dir, f"teams_{canal_nombre}.txt"
                    )
                    with open(texto_file, "w", encoding="utf-8") as f:
                        f.write("\n".join(lineas))

                # Archivos del canal
                archivos = self._obtener_archivos_canal(self.team_id, canal["id"])
                archivos_descargados = 0
                for archivo in archivos:
                    url = archivo.get("download_url", "")
                    if url:
                        ruta = self._descargar_archivo(
                            url, archivo["name"], tmp_dir
                        )
                        if ruta:
                            archivos_descargados += 1

                # DII pipeline
                if mensajes or archivos_descargados:
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

                    resumen["canales_procesados"] += 1
                    resumen["mensajes_totales"] += len(mensajes)
                    resumen["archivos_procesados"] += archivos_descargados
                    resumen["entidades_totales"] += len(entidades)

                    tm.log(
                        component="DII",
                        action="teams_channel_processed",
                        detail={
                            "channel": canal_nombre,
                            "mensajes": len(mensajes),
                            "archivos": archivos_descargados,
                            "entidades": len(entidades)
                        }
                    )

            except Exception as e:
                resumen["errores"].append(f"{canal_nombre}: {str(e)}")
                print(f"  [Teams] Error en {canal_nombre}: {e}")

            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        print(f"  [Teams] Resumen: {resumen}")
        return resumen
