import os
import tempfile
import shutil
from ftplib import FTP
from app.core.matrix import TraceabilityMatrix
from dotenv import load_dotenv

load_dotenv()


# ─── FTP/SFTP CONNECTOR | Panohayan™ ────────────────────────────────────────
#
# Descarga archivos de servidores FTP/SFTP y los procesa via DII.
# Soporta FTP (ftplib) y SFTP (paramiko).
# ─────────────────────────────────────────────────────────────────────────────

EXTENSIONES_SOPORTADAS = {
    "pdf", "docx", "doc", "xlsx", "xls", "csv",
    "txt", "html", "htm", "xml", "json", "png",
    "jpg", "jpeg", "pptx"
}


class FTPConnector:

    CONNECTOR_NAME = "ftp"

    def __init__(self, host: str = None, port: int = None,
                 username: str = None, password: str = None,
                 protocol: str = None, remote_path: str = "/",
                 ssh_key_path: str = None):
        self.host = host or os.getenv("FTP_HOST", "")
        self.port = port or int(os.getenv("FTP_PORT", "21"))
        self.username = username or os.getenv("FTP_USER", "")
        self.password = password or os.getenv("FTP_PASSWORD", "")
        self.protocol = protocol or os.getenv("FTP_PROTOCOL", "ftp")
        self.remote_path = remote_path
        self.ssh_key_path = ssh_key_path
        self._client = None

    def conectar(self) -> bool:
        """Establece conexión FTP o SFTP."""
        if self.protocol == "sftp":
            return self._conectar_sftp()
        return self._conectar_ftp()

    def _conectar_ftp(self) -> bool:
        try:
            self._client = FTP()
            self._client.connect(self.host, self.port, timeout=10)
            self._client.login(self.username, self.password)
            print(f"  [FTP] Conectado a {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"  [FTP] Error de conexión: {e}")
            return False

    def _conectar_sftp(self) -> bool:
        try:
            import paramiko

            transport = paramiko.Transport((self.host, self.port or 22))

            if self.ssh_key_path and os.path.exists(self.ssh_key_path):
                key = paramiko.RSAKey.from_private_key_file(self.ssh_key_path)
                transport.connect(username=self.username, pkey=key)
            else:
                transport.connect(
                    username=self.username, password=self.password
                )

            self._client = paramiko.SFTPClient.from_transport(transport)
            print(f"  [SFTP] Conectado a {self.host}:{self.port or 22}")
            return True

        except ImportError:
            print("  [SFTP] Error: pip install paramiko")
            return False
        except Exception as e:
            print(f"  [SFTP] Error de conexión: {e}")
            return False

    def _listar_archivos_ftp(self, path: str) -> list:
        archivos = []
        items = self._client.nlst(path)
        for item in items:
            nombre = os.path.basename(item)
            ext = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
            if ext in EXTENSIONES_SOPORTADAS:
                archivos.append(item if "/" in item else f"{path}/{item}")
        return archivos

    def _listar_archivos_sftp(self, path: str) -> list:
        archivos = []
        for entry in self._client.listdir_attr(path):
            nombre = entry.filename
            ext = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
            if ext in EXTENSIONES_SOPORTADAS:
                full_path = f"{path.rstrip('/')}/{nombre}"
                archivos.append(full_path)
        return archivos

    def listar_archivos(self) -> list:
        if self.protocol == "sftp":
            return self._listar_archivos_sftp(self.remote_path)
        return self._listar_archivos_ftp(self.remote_path)

    def _descargar_ftp(self, remote_path: str, local_path: str):
        with open(local_path, "wb") as f:
            self._client.retrbinary(f"RETR {remote_path}", f.write)

    def _descargar_sftp(self, remote_path: str, local_path: str):
        self._client.get(remote_path, local_path)

    def descargar(self, remote_path: str, local_path: str):
        if self.protocol == "sftp":
            self._descargar_sftp(remote_path, local_path)
        else:
            self._descargar_ftp(remote_path, local_path)

    def sincronizar(self, org_id: str = None) -> dict:
        """Descarga archivos del servidor FTP/SFTP y los procesa via DII."""
        from app.core.dii import DigestInputIntelligence
        from app.core.grg import GovernanceGuardrails

        _org_id = org_id or os.getenv("ORG_ID", "default")
        tm = TraceabilityMatrix(org_id=_org_id)

        if not self.conectar():
            return {"error": f"No se pudo conectar a {self.protocol.upper()}"}

        resumen = {
            "conector": self.protocol,
            "archivos_procesados": 0,
            "entidades_totales": 0,
            "errores": []
        }

        archivos_remotos = self.listar_archivos()
        print(f"  [{self.protocol.upper()}] {len(archivos_remotos)} archivos encontrados")

        for remote_file in archivos_remotos:
            tmp_dir = tempfile.mkdtemp()
            filename = os.path.basename(remote_file)

            try:
                local_path = os.path.join(tmp_dir, filename)
                self.descargar(remote_file, local_path)
                print(f"  [{self.protocol.upper()}] Descargado: {filename}")

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
                    action="ftp_file_processed",
                    detail={"archivo": filename, "entidades": len(entidades)}
                )

            except Exception as e:
                resumen["errores"].append(f"{filename}: {str(e)}")
                print(f"  [{self.protocol.upper()}] Error: {e}")

            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        # Cerrar conexión
        try:
            if self.protocol == "sftp":
                self._client.close()
            else:
                self._client.quit()
        except Exception:
            pass

        print(f"  [{self.protocol.upper()}] Resumen: {resumen}")
        return resumen
