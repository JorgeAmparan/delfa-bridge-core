import os
import email
import imaplib
import tempfile
import shutil
from email.header import decode_header
from app.core.matrix import TraceabilityMatrix
from dotenv import load_dotenv

load_dotenv()


# ─── IMAP CONNECTOR | Panohayan™ ────────────────────────────────────────────
#
# Extrae correos de cualquier servidor IMAP (genérico).
# Procesa cuerpo + adjuntos a través del pipeline DII.
# Para servicios sin API REST: cuentas corporativas, hosting propio, etc.
# ─────────────────────────────────────────────────────────────────────────────

EXTENSIONES_ADJUNTOS = {
    "pdf", "docx", "doc", "xlsx", "xls", "csv",
    "txt", "html", "htm", "png", "jpg", "jpeg", "pptx", "xml"
}


class IMAPConnector:

    CONNECTOR_NAME = "imap"

    def __init__(self, host: str = None, port: int = None,
                 username: str = None, password: str = None,
                 use_ssl: bool = True, folder: str = "INBOX",
                 search_criteria: str = "UNSEEN",
                 max_messages: int = 50):
        self.host = host or os.getenv("IMAP_HOST", "")
        self.port = port or int(os.getenv("IMAP_PORT", "993"))
        self.username = username or os.getenv("IMAP_USER", "")
        self.password = password or os.getenv("IMAP_PASSWORD", "")
        self.use_ssl = use_ssl
        self.folder = folder
        self.search_criteria = search_criteria
        self.max_messages = max_messages
        self._conn = None

    def conectar(self) -> bool:
        """Establece conexión IMAP."""
        if not all([self.host, self.username, self.password]):
            print("  [IMAP] Error: IMAP_HOST, IMAP_USER o IMAP_PASSWORD no configurados")
            return False

        try:
            if self.use_ssl:
                self._conn = imaplib.IMAP4_SSL(self.host, self.port)
            else:
                self._conn = imaplib.IMAP4(self.host, self.port)

            self._conn.login(self.username, self.password)
            print(f"  [IMAP] Conectado a {self.host}")
            return True

        except Exception as e:
            print(f"  [IMAP] Error de conexión: {e}")
            return False

    def _decode_header_value(self, value: str) -> str:
        """Decodifica headers con encodings variados."""
        if not value:
            return ""
        decoded_parts = decode_header(value)
        result = []
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                result.append(part.decode(charset or "utf-8", errors="replace"))
            else:
                result.append(str(part))
        return " ".join(result)

    def _extraer_cuerpo(self, msg: email.message.Message) -> str:
        """Extrae texto plano del correo."""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
        return ""

    def _guardar_adjuntos(self, msg: email.message.Message,
                          tmp_dir: str) -> list:
        """Extrae y guarda adjuntos soportados."""
        adjuntos = []

        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition", ""))
            if "attachment" not in content_disposition:
                continue

            filename = part.get_filename()
            if not filename:
                continue

            filename = self._decode_header_value(filename)
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if ext not in EXTENSIONES_ADJUNTOS:
                continue

            payload = part.get_payload(decode=True)
            if payload:
                ruta = os.path.join(tmp_dir, filename)
                with open(ruta, "wb") as f:
                    f.write(payload)
                adjuntos.append(ruta)

        return adjuntos

    def sincronizar(self, org_id: str = None) -> dict:
        """Extrae correos via IMAP y los procesa via DII."""
        from app.core.dii import DigestInputIntelligence
        from app.core.grg import GovernanceGuardrails

        _org_id = org_id or os.getenv("ORG_ID", "default")
        tm = TraceabilityMatrix(org_id=_org_id)

        if not self.conectar():
            return {"error": "No se pudo conectar via IMAP"}

        resumen = {
            "conector": "imap",
            "correos_procesados": 0,
            "adjuntos_procesados": 0,
            "entidades_totales": 0,
            "errores": []
        }

        try:
            self._conn.select(self.folder)
            _, msg_numbers = self._conn.search(None, self.search_criteria)
            ids = msg_numbers[0].split()

            # Limitar cantidad
            ids = ids[-self.max_messages:]
            print(f"  [IMAP] {len(ids)} correos encontrados")

        except Exception as e:
            return {"error": f"Error buscando correos: {str(e)}"}

        for msg_id in ids:
            tmp_dir = tempfile.mkdtemp()

            try:
                _, data = self._conn.fetch(msg_id, "(RFC822)")
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Extraer headers
                subject = self._decode_header_value(msg.get("Subject", ""))
                from_addr = self._decode_header_value(msg.get("From", ""))
                to_addr = self._decode_header_value(msg.get("To", ""))
                date = msg.get("Date", "")

                # Extraer cuerpo
                cuerpo = self._extraer_cuerpo(msg)

                # Crear texto estructurado
                lineas = [
                    "=== CORREO IMAP ===\n",
                    f"Subject: {subject}",
                    f"From: {from_addr}",
                    f"To: {to_addr}",
                    f"Date: {date}",
                ]
                if cuerpo:
                    lineas.append(f"\n--- CUERPO ---\n{cuerpo}")

                correo_file = os.path.join(tmp_dir, f"imap_{msg_id.decode()}.txt")
                with open(correo_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(lineas))

                # Adjuntos
                adjuntos = self._guardar_adjuntos(msg, tmp_dir)

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

                resumen["correos_procesados"] += 1
                resumen["adjuntos_procesados"] += len(adjuntos)
                resumen["entidades_totales"] += len(entidades)

                tm.log(
                    component="DII",
                    action="imap_processed",
                    detail={
                        "subject": subject,
                        "adjuntos": len(adjuntos),
                        "entidades": len(entidades)
                    }
                )

            except Exception as e:
                resumen["errores"].append(str(e))
                print(f"  [IMAP] Error: {e}")

            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        # Cerrar conexión
        try:
            self._conn.close()
            self._conn.logout()
        except Exception:
            pass

        print(f"  [IMAP] Resumen: {resumen}")
        return resumen
