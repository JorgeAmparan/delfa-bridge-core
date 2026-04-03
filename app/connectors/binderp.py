import os
from app.connectors.api_base import APIConnector

# ─── BIND ERP CONNECTOR | Panohayan™ ────────────────────────────────────────
#
# Extrae facturas, clientes, productos e inventario de Bind ERP via API.
# ERP mexicano en la nube — autenticación por API Key.
# ─────────────────────────────────────────────────────────────────────────────


class BindERPConnector(APIConnector):

    CONNECTOR_NAME = "binderp"

    def __init__(self, api_key: str = None, base_url: str = None,
                 objetos: list = None):
        super().__init__()
        self.api_key = api_key or os.getenv("BINDERP_API_KEY", "")
        self.BASE_URL = (
            base_url or
            os.getenv("BINDERP_URL", "https://api.bind.com.mx/v1")
        ).rstrip("/")
        self.objetos = objetos or [
            "invoices", "clients", "products", "inventory"
        ]

    def autenticar(self) -> bool:
        if not self.api_key:
            print("  [BindERP] Error: BINDERP_API_KEY no configurado")
            return False

        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })

        try:
            response = self.session.get(
                f"{self.BASE_URL}/clients",
                params={"limit": 1},
                timeout=10
            )
            response.raise_for_status()
            print("  [BindERP] Autenticado correctamente")
            return True
        except Exception as e:
            print(f"  [BindERP] Error de autenticación: {e}")
            return False

    # Mapeo de objetos a endpoints de Bind ERP
    _ENDPOINTS = {
        "invoices": "/invoices",
        "clients": "/clients",
        "products": "/products",
        "inventory": "/inventory",
        "providers": "/providers",
        "payments": "/payments",
    }

    def _extraer_objeto(self, tipo: str, limite: int = 100) -> list:
        """Extrae registros de un endpoint de Bind ERP."""
        endpoint = self._ENDPOINTS.get(tipo, f"/{tipo}")
        registros = []

        try:
            page = 1
            while len(registros) < limite:
                data = self._get(
                    f"{self.BASE_URL}{endpoint}",
                    params={
                        "page": page,
                        "limit": min(50, limite - len(registros))
                    }
                )

                items = data if isinstance(data, list) else data.get("data", [])
                if not items:
                    break

                registros.extend(items)
                page += 1

                # Si recibimos menos del límite, no hay más páginas
                if len(items) < 50:
                    break

        except Exception as e:
            print(f"  [BindERP] Error extrayendo {tipo}: {e}")

        print(f"  [BindERP] {len(registros)} {tipo} obtenidos")
        return registros

    def extraer_datos(self) -> dict:
        datos = {}
        for obj in self.objetos:
            registros = self._extraer_objeto(obj)
            if registros:
                datos[obj] = registros
        return datos
