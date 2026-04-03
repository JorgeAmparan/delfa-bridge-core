import os
import tempfile
import shutil
import requests
from abc import ABC, abstractmethod
from dotenv import load_dotenv
from app.core.matrix import TraceabilityMatrix

load_dotenv()


# ─── API CONNECTOR BASE | Panohayan™ ────────────────────────────────────────
#
# Clase base para conectores que extraen datos via REST API.
# Patrón: autenticarse → listar/extraer → texto estructurado → DII pipeline.
# Usado por: Notion, HubSpot, Pipedrive, Bind ERP.
# ─────────────────────────────────────────────────────────────────────────────


class APIConnector(ABC):
    """
    Clase base para conectores REST API → DII pipeline.
    Subclases definen: CONNECTOR_NAME, BASE_URL, autenticar(), extraer_datos().
    """

    CONNECTOR_NAME: str = "api"
    BASE_URL: str = ""

    def __init__(self):
        self.session = requests.Session()
        self._autenticado = False

    @abstractmethod
    def autenticar(self) -> bool:
        """
        Configura autenticación en self.session (headers, tokens, etc.).
        Retorna True si fue exitoso.
        """
        pass

    @abstractmethod
    def extraer_datos(self) -> dict:
        """
        Extrae datos de la API externa.
        Retorna dict donde key=tipo (e.g. "contacts", "deals")
        y value=lista de registros (dicts).
        """
        pass

    def _get(self, url: str, params: dict = None) -> dict:
        """GET autenticado con manejo de errores."""
        if not self._autenticado:
            if not self.autenticar():
                raise ConnectionError(
                    f"No se pudo autenticar con {self.CONNECTOR_NAME}"
                )
            self._autenticado = True

        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def _post(self, url: str, json: dict = None,
              params: dict = None) -> dict:
        """POST autenticado con manejo de errores."""
        if not self._autenticado:
            if not self.autenticar():
                raise ConnectionError(
                    f"No se pudo autenticar con {self.CONNECTOR_NAME}"
                )
            self._autenticado = True

        response = self.session.post(
            url, json=json, params=params, timeout=30
        )
        response.raise_for_status()
        return response.json()

    def datos_a_texto(self, datos: list, tipo: str) -> str:
        """
        Convierte lista de dicts a texto estructurado para DII.
        Override para formateo específico por conector.
        """
        if not datos:
            return ""

        lineas = [f"=== {tipo.upper()} — {self.CONNECTOR_NAME.upper()} ===\n"]

        for item in datos:
            lineas.append("---")
            if isinstance(item, dict):
                for key, value in item.items():
                    if value is not None and str(value).strip():
                        lineas.append(f"{key}: {value}")
            else:
                lineas.append(str(item))

        return "\n".join(lineas)

    def sincronizar(self, org_id: str = None) -> dict:
        """
        Pipeline completo: autenticar → extraer → DII → GRG → TM.
        No override — flujo estándar inmutable.
        """
        from app.core.dii import DigestInputIntelligence
        from app.core.grg import GovernanceGuardrails

        _org_id = org_id or os.getenv("ORG_ID", "default")
        tm = TraceabilityMatrix(org_id=_org_id)
        name = self.CONNECTOR_NAME

        print(f"\n  [{name}] Iniciando sincronización")

        if not self.autenticar():
            return {"error": f"No se pudo autenticar con {name}"}
        self._autenticado = True

        resumen = {
            "conector": name,
            "entidades_totales": 0,
            "tipos_procesados": [],
            "errores": []
        }

        try:
            datos_por_tipo = self.extraer_datos()
        except Exception as e:
            return {"error": f"Error extrayendo datos: {str(e)}"}

        for tipo, datos in datos_por_tipo.items():
            if not datos:
                continue

            texto = self.datos_a_texto(datos, tipo)
            if not texto:
                continue

            tmp_dir = tempfile.mkdtemp()

            try:
                tmp_file = os.path.join(
                    tmp_dir, f"{name}_{tipo}.txt"
                )
                with open(tmp_file, "w", encoding="utf-8") as f:
                    f.write(texto)

                dii = DigestInputIntelligence(org_id=_org_id)
                dii.data_path = tmp_dir
                entidades = dii.run_dii_pipeline()

                # GRG
                from supabase import create_client
                supabase = create_client(
                    os.getenv("SUPABASE_URL"),
                    os.getenv("SUPABASE_KEY")
                )
                doc = supabase.table("documents").select("id").eq(
                    "org_id", _org_id
                ).eq(
                    "name", f"{name}_{tipo}.txt"
                ).order("created_at", desc=True).limit(1).execute()

                if doc.data:
                    grg = GovernanceGuardrails(org_id=_org_id)
                    grg.evaluar_documento(doc.data[0]["id"])

                resumen["entidades_totales"] += len(entidades)
                resumen["tipos_procesados"].append({
                    "tipo": tipo,
                    "registros": len(datos),
                    "entidades": len(entidades)
                })

                tm.log(
                    component="DII",
                    action=f"{name}_synced",
                    detail={
                        "tipo": tipo,
                        "registros": len(datos),
                        "entidades": len(entidades)
                    }
                )

            except Exception as e:
                error = f"{tipo}: {str(e)}"
                resumen["errores"].append(error)
                print(f"  [{name}] Error procesando {tipo}: {e}")

            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        print(f"  [{name}] Resumen: {resumen}")
        return resumen
