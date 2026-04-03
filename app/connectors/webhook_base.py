import os
import hmac
import hashlib
import tempfile
import shutil
import base64
from abc import ABC, abstractmethod
from dotenv import load_dotenv
from app.core.matrix import TraceabilityMatrix

load_dotenv()


# ─── WEBHOOK CONNECTOR BASE | Panohayan™ ────────────────────────────────────
#
# Clase base para conectores que reciben datos via webhook/POST.
# Patrón: recibir payload → validar secret → extraer contenido → DII pipeline.
# Usado por: Make, Zapier, n8n, Bubble, Lovable, Chrome Extension, Webhook genérico.
# ─────────────────────────────────────────────────────────────────────────────


class WebhookConnector(ABC):
    """
    Clase base para conectores webhook/POST → DII pipeline.
    Subclases definen: CONNECTOR_NAME, SECRET_ENV_VAR, extraer_contenido().
    """

    CONNECTOR_NAME: str = "webhook"
    SECRET_ENV_VAR: str = None

    def validar_secret(self, secret_recibido: str) -> bool:
        """
        Valida el secret/token del webhook.
        Retorna True si no hay secret configurado (modo abierto).
        """
        if not self.SECRET_ENV_VAR:
            return True

        secret_esperado = os.getenv(self.SECRET_ENV_VAR)
        if not secret_esperado:
            return True

        return hmac.compare_digest(secret_recibido or "", secret_esperado)

    def validar_hmac(self, payload_bytes: bytes, signature: str,
                     secret_env_var: str = None) -> bool:
        """Valida HMAC-SHA256 signature (para webhooks que firman el body)."""
        secret = os.getenv(secret_env_var or self.SECRET_ENV_VAR, "")
        if not secret:
            return True

        expected = hmac.new(
            secret.encode(), payload_bytes, hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature or "", expected)

    @abstractmethod
    def extraer_contenido(self, payload: dict) -> str:
        """
        Extrae texto procesable del payload.
        Cada conector implementa su propio parsing.
        Retorna texto estructurado para DII.
        """
        pass

    def extraer_archivos(self, payload: dict) -> list:
        """
        Extrae archivos adjuntos del payload (base64).
        Retorna lista de rutas a archivos temporales.
        Override en subclases que soporten archivos.
        """
        archivos = []
        adjuntos = payload.get("files") or payload.get("attachments") or []

        for adjunto in adjuntos:
            if isinstance(adjunto, dict) and adjunto.get("content_base64"):
                nombre = adjunto.get("filename", "archivo.pdf")
                tmp_dir = tempfile.mkdtemp()
                ruta = os.path.join(tmp_dir, nombre)
                with open(ruta, "wb") as f:
                    f.write(base64.b64decode(adjunto["content_base64"]))
                archivos.append(ruta)

        return archivos

    def procesar(self, payload: dict, org_id: str = None) -> dict:
        """
        Pipeline completo: extraer → DII → GRG → TM.
        No override — flujo estándar inmutable.
        """
        from app.core.dii import DigestInputIntelligence
        from app.core.grg import GovernanceGuardrails

        _org_id = org_id or os.getenv("ORG_ID", "default")
        tm = TraceabilityMatrix(org_id=_org_id)
        name = self.CONNECTOR_NAME

        print(f"\n  [{name}] Procesando webhook payload")

        resumen = {
            "conector": name,
            "entidades_totales": 0,
            "documentos_procesados": 0,
            "errores": []
        }

        tmp_dirs = []

        try:
            # 1. Extraer texto del payload
            texto = self.extraer_contenido(payload)

            # 2. Procesar texto si hay contenido
            if texto and texto.strip():
                tmp_dir = tempfile.mkdtemp()
                tmp_dirs.append(tmp_dir)
                tmp_file = os.path.join(tmp_dir, f"{name}_payload.txt")
                with open(tmp_file, "w", encoding="utf-8") as f:
                    f.write(texto)

                dii = DigestInputIntelligence(org_id=_org_id)
                dii.data_path = tmp_dir
                entidades = dii.run_dii_pipeline()

                resumen["entidades_totales"] += len(entidades)
                resumen["documentos_procesados"] += 1

            # 3. Procesar archivos adjuntos si los hay
            archivos = self.extraer_archivos(payload)
            for ruta in archivos:
                dir_archivo = os.path.dirname(ruta)
                tmp_dirs.append(dir_archivo)

                dii = DigestInputIntelligence(org_id=_org_id)
                dii.data_path = dir_archivo
                entidades = dii.run_dii_pipeline()

                resumen["entidades_totales"] += len(entidades)
                resumen["documentos_procesados"] += 1

            # 4. GRG — evaluar último documento
            if resumen["documentos_procesados"] > 0:
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

            # 5. TM — registrar
            tm.log(
                component="DII",
                action=f"{name}_webhook_processed",
                detail={
                    "entidades": resumen["entidades_totales"],
                    "documentos": resumen["documentos_procesados"]
                }
            )

        except Exception as e:
            error = f"{name}: {str(e)}"
            resumen["errores"].append(error)
            print(f"  [{name}] Error: {error}")

        finally:
            for d in tmp_dirs:
                shutil.rmtree(d, ignore_errors=True)

        print(f"  [{name}] Resumen: {resumen}")
        return resumen
