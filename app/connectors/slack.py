import os
import tempfile
import shutil
from app.connectors.api_base import APIConnector
from app.core.matrix import TraceabilityMatrix
from dotenv import load_dotenv

load_dotenv()


# ─── SLACK CONNECTOR | Panohayan™ ───────────────────────────────────────────
#
# Extrae mensajes de canales de Slack via Bot Token.
# Procesa conversaciones y archivos compartidos a través del pipeline DII.
# ─────────────────────────────────────────────────────────────────────────────


class SlackConnector(APIConnector):

    CONNECTOR_NAME = "slack"
    BASE_URL = "https://slack.com/api"

    def __init__(self, bot_token: str = None, channels: list = None,
                 max_messages: int = 200):
        super().__init__()
        self.bot_token = bot_token or os.getenv("SLACK_BOT_TOKEN", "")
        self.channels = channels or []
        self.max_messages = max_messages

    def autenticar(self) -> bool:
        if not self.bot_token:
            print("  [Slack] Error: SLACK_BOT_TOKEN no configurado")
            return False

        self.session.headers.update({
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json; charset=utf-8"
        })

        try:
            response = self.session.get(
                f"{self.BASE_URL}/auth.test", timeout=10
            )
            data = response.json()
            if not data.get("ok"):
                print(f"  [Slack] Error: {data.get('error')}")
                return False

            print(f"  [Slack] Autenticado: {data.get('team', '')} / {data.get('user', '')}")
            return True

        except Exception as e:
            print(f"  [Slack] Error de autenticación: {e}")
            return False

    def _listar_canales(self) -> list:
        """Lista canales accesibles si no se especificaron."""
        try:
            data = self._get(
                f"{self.BASE_URL}/conversations.list",
                params={"types": "public_channel,private_channel", "limit": 100}
            )
            canales = data.get("channels", [])
            print(f"  [Slack] {len(canales)} canales accesibles")
            return [{"id": c["id"], "name": c["name"]} for c in canales]
        except Exception as e:
            print(f"  [Slack] Error listando canales: {e}")
            return []

    def _obtener_mensajes(self, channel_id: str) -> list:
        """Obtiene mensajes recientes de un canal."""
        mensajes = []

        try:
            params = {"channel": channel_id, "limit": min(200, self.max_messages)}
            data = self._get(f"{self.BASE_URL}/conversations.history", params=params)

            for msg in data.get("messages", []):
                if msg.get("subtype") in ("channel_join", "channel_leave", "bot_message"):
                    continue
                mensajes.append({
                    "user": msg.get("user", "unknown"),
                    "text": msg.get("text", ""),
                    "ts": msg.get("ts", ""),
                    "files": [
                        {"name": f.get("name", ""), "url": f.get("url_private", "")}
                        for f in msg.get("files", [])
                    ]
                })

        except Exception as e:
            print(f"  [Slack] Error obteniendo mensajes: {e}")

        return mensajes

    def _descargar_archivo_slack(self, url: str, filename: str,
                                 tmp_dir: str) -> str:
        """Descarga archivo compartido en Slack."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            ruta = os.path.join(tmp_dir, filename)
            with open(ruta, "wb") as f:
                f.write(response.content)
            return ruta
        except Exception as e:
            print(f"  [Slack] Error descargando {filename}: {e}")
            return None

    def extraer_datos(self) -> dict:
        return {}

    def sincronizar(self, org_id: str = None) -> dict:
        """Extrae mensajes de canales de Slack y los procesa via DII."""
        from app.core.dii import DigestInputIntelligence
        from app.core.grg import GovernanceGuardrails

        _org_id = org_id or os.getenv("ORG_ID", "default")
        tm = TraceabilityMatrix(org_id=_org_id)

        if not self.autenticar():
            return {"error": "No se pudo autenticar con Slack"}
        self._autenticado = True

        resumen = {
            "conector": "slack",
            "canales_procesados": 0,
            "mensajes_totales": 0,
            "archivos_descargados": 0,
            "entidades_totales": 0,
            "errores": []
        }

        # Resolver canales
        if self.channels:
            canales = [{"id": c, "name": c} for c in self.channels]
        else:
            canales = self._listar_canales()

        for canal in canales:
            tmp_dir = tempfile.mkdtemp()

            try:
                mensajes = self._obtener_mensajes(canal["id"])
                if not mensajes:
                    continue

                # Convertir mensajes a texto
                lineas = [f"=== SLACK — #{canal['name']} ===\n"]
                for msg in mensajes:
                    lineas.append(f"[{msg['ts']}] {msg['user']}: {msg['text']}")

                texto_file = os.path.join(tmp_dir, f"slack_{canal['name']}.txt")
                with open(texto_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(lineas))

                # Descargar archivos compartidos
                archivos_descargados = 0
                for msg in mensajes:
                    for archivo in msg.get("files", []):
                        if archivo.get("url") and archivo.get("name"):
                            ruta = self._descargar_archivo_slack(
                                archivo["url"], archivo["name"], tmp_dir
                            )
                            if ruta:
                                archivos_descargados += 1

                # DII pipeline
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
                resumen["archivos_descargados"] += archivos_descargados
                resumen["entidades_totales"] += len(entidades)

                tm.log(
                    component="DII",
                    action="slack_channel_processed",
                    detail={
                        "channel": canal["name"],
                        "mensajes": len(mensajes),
                        "archivos": archivos_descargados,
                        "entidades": len(entidades)
                    }
                )

            except Exception as e:
                resumen["errores"].append(f"#{canal['name']}: {str(e)}")
                print(f"  [Slack] Error en #{canal['name']}: {e}")

            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        print(f"  [Slack] Resumen: {resumen}")
        return resumen
