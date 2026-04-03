import os
import xmlrpc.client
import tempfile
import shutil
from app.core.matrix import TraceabilityMatrix
from dotenv import load_dotenv

load_dotenv()


# ─── ODOO CONNECTOR | Panohayan™ ────────────────────────────────────────────
#
# Extrae datos de Odoo via XML-RPC (JSON-RPC compatible).
# Soporta modelos configurables: res.partner, sale.order, account.move, etc.
# Autenticación: user/pass + database name.
# ─────────────────────────────────────────────────────────────────────────────


class OdooConnector:

    CONNECTOR_NAME = "odoo"

    # Modelos por defecto (los más comunes para PYMEs)
    DEFAULT_MODELS = {
        "res.partner": {
            "fields": ["name", "email", "phone", "street", "city",
                        "country_id", "vat", "company_type"],
            "label": "contactos"
        },
        "sale.order": {
            "fields": ["name", "partner_id", "date_order", "amount_total",
                        "state", "user_id"],
            "label": "ordenes_venta"
        },
        "account.move": {
            "fields": ["name", "partner_id", "invoice_date", "amount_total",
                        "state", "move_type", "payment_state"],
            "label": "facturas"
        },
        "product.product": {
            "fields": ["name", "default_code", "list_price", "qty_available",
                        "categ_id", "type"],
            "label": "productos"
        }
    }

    def __init__(self, url: str = None, db: str = None,
                 username: str = None, password: str = None,
                 modelos: dict = None):
        self.url = (url or os.getenv("ODOO_URL", "")).rstrip("/")
        self.db = db or os.getenv("ODOO_DB", "")
        self.username = username or os.getenv("ODOO_USER", "")
        self.password = password or os.getenv("ODOO_PASSWORD", "")
        self.modelos = modelos or self.DEFAULT_MODELS
        self.uid = None
        self._models = None

    def autenticar(self) -> bool:
        """Autentica con Odoo via XML-RPC."""
        if not all([self.url, self.db, self.username, self.password]):
            print("  [Odoo] Error: ODOO_URL, ODOO_DB, ODOO_USER o ODOO_PASSWORD no configurados")
            return False

        try:
            common = xmlrpc.client.ServerProxy(
                f"{self.url}/xmlrpc/2/common", allow_none=True
            )
            self.uid = common.authenticate(
                self.db, self.username, self.password, {}
            )

            if not self.uid:
                print("  [Odoo] Error: credenciales inválidas")
                return False

            self._models = xmlrpc.client.ServerProxy(
                f"{self.url}/xmlrpc/2/object", allow_none=True
            )

            print(f"  [Odoo] Autenticado: uid={self.uid} en {self.db}")
            return True

        except Exception as e:
            print(f"  [Odoo] Error de autenticación: {e}")
            return False

    def _search_read(self, model: str, fields: list,
                     domain: list = None, limit: int = 200) -> list:
        """Ejecuta search_read en un modelo de Odoo."""
        try:
            registros = self._models.execute_kw(
                self.db, self.uid, self.password,
                model, "search_read",
                [domain or []],
                {"fields": fields, "limit": limit}
            )
            return registros or []
        except Exception as e:
            print(f"  [Odoo] Error en {model}: {e}")
            return []

    def _datos_a_texto(self, datos: list, label: str) -> str:
        """Convierte registros de Odoo a texto estructurado."""
        if not datos:
            return ""

        lineas = [f"=== {label.upper()} — ODOO ===\n"]
        for item in datos:
            lineas.append("---")
            for key, value in item.items():
                if key == "id":
                    continue
                # many2one fields vienen como [id, name]
                if isinstance(value, (list, tuple)) and len(value) == 2:
                    value = value[1]
                if value is not None and value is not False and str(value).strip():
                    lineas.append(f"{key}: {value}")

        return "\n".join(lineas)

    def sincronizar(self, org_id: str = None) -> dict:
        """Extrae datos de Odoo y los procesa via DII pipeline."""
        from app.core.dii import DigestInputIntelligence
        from app.core.grg import GovernanceGuardrails

        _org_id = org_id or os.getenv("ORG_ID", "default")
        tm = TraceabilityMatrix(org_id=_org_id)

        if not self.autenticar():
            return {"error": "No se pudo autenticar con Odoo"}

        print(f"\n  [Odoo] Extrayendo {len(self.modelos)} modelos")

        resumen = {
            "conector": "odoo",
            "entidades_totales": 0,
            "modelos_procesados": [],
            "errores": []
        }

        for model, config in self.modelos.items():
            fields = config.get("fields", [])
            label = config.get("label", model)

            datos = self._search_read(model, fields)
            if not datos:
                continue

            texto = self._datos_a_texto(datos, label)
            if not texto:
                continue

            tmp_dir = tempfile.mkdtemp()

            try:
                tmp_file = os.path.join(tmp_dir, f"odoo_{label}.txt")
                with open(tmp_file, "w", encoding="utf-8") as f:
                    f.write(texto)

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
                ).eq("name", f"odoo_{label}.txt").order(
                    "created_at", desc=True
                ).limit(1).execute()

                if doc.data:
                    grg = GovernanceGuardrails(org_id=_org_id)
                    grg.evaluar_documento(doc.data[0]["id"])

                resumen["entidades_totales"] += len(entidades)
                resumen["modelos_procesados"].append({
                    "modelo": model,
                    "label": label,
                    "registros": len(datos),
                    "entidades": len(entidades)
                })

                tm.log(
                    component="DII",
                    action="odoo_synced",
                    detail={"modelo": model, "registros": len(datos)}
                )

            except Exception as e:
                resumen["errores"].append(f"{model}: {str(e)}")
                print(f"  [Odoo] Error procesando {model}: {e}")

            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        print(f"  [Odoo] Resumen: {resumen}")
        return resumen
