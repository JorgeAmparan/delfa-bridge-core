import os
from app.connectors.erp_mexicano_base import ERPMexicanoDBBase, ERPMexicanoFileBase
from dotenv import load_dotenv

load_dotenv()


# ─── ASPEL CONNECTOR | Panohayan™ ───────────────────────────────────────────
#
# Conecta Delfa Bridge a Aspel SAE / COI / NOI.
# Patrón dual:
#   Opción A — Conexión directa a BD (SQL Server o Firebird según versión)
#   Opción B — Archivos exportados (XML CFDI, CSV reportes)
#
# Aspel SAE (Sistema Administrativo Empresarial) — tablas principales:
#   CLIE01 (clientes), PROV01 (proveedores), INVE01 (inventario),
#   FACT01/FACM01 (facturas), PAR_FACTM01 (partidas)
# Aspel COI (Contabilidad) — tablas:
#   CPOL01 (pólizas), CCUE01 (cuentas contables)
# ─────────────────────────────────────────────────────────────────────────────


class AspelDBConnector(ERPMexicanoDBBase):
    """Conexión directa a la BD de Aspel SAE/COI."""

    ERP_NAME = "aspel"
    ENV_PREFIX = "ASPEL"

    def __init__(self, *args, modulo: str = "sae", **kwargs):
        super().__init__(*args, **kwargs)
        self.modulo = modulo  # "sae" o "coi"

    def extraer_datos(self) -> dict:
        datos = {}

        if self.modulo in ("sae", "all"):
            datos.update(self._extraer_sae())

        if self.modulo in ("coi", "all"):
            datos.update(self._extraer_coi())

        return datos

    def _extraer_sae(self) -> dict:
        """Extrae datos de Aspel SAE."""
        datos = {}

        # Clientes
        clientes = self._intentar_queries([
            """
            SELECT TOP 200
                CVE_CLIEN as clave, STATUS as estatus,
                NOMBRE as nombre, RFC as rfc,
                CALLE as calle, COLONIA as colonia,
                CIUDAD as ciudad, ESTADO as estado,
                CODIGO as cp, TELEFONO as telefono,
                E_MAIL as email, LIMCRED as limite_credito,
                SALDO as saldo
            FROM CLIE01
            ORDER BY NOMBRE
            """,
            "SELECT TOP 200 * FROM CLIE01 ORDER BY NOMBRE",
        ], "clientes")
        if clientes:
            datos["clientes"] = clientes

        # Proveedores
        proveedores = self._intentar_queries([
            """
            SELECT TOP 200
                CVE_PROVE as clave, STATUS as estatus,
                NOMBRE as nombre, RFC as rfc,
                CALLE as calle, CIUDAD as ciudad,
                TELEFONO as telefono, E_MAIL as email
            FROM PROV01
            ORDER BY NOMBRE
            """,
            "SELECT TOP 200 * FROM PROV01 ORDER BY NOMBRE",
        ], "proveedores")
        if proveedores:
            datos["proveedores"] = proveedores

        # Inventario / Productos
        productos = self._intentar_queries([
            """
            SELECT TOP 200
                CVE_ART as clave, DESCR as descripcion,
                LIN_PROD as linea, UNI_MED as unidad,
                EXIST as existencia, PRECIO1 as precio,
                COST_ULT as costo_ultimo,
                CVE_PRODSERV as clave_sat
            FROM INVE01
            ORDER BY DESCR
            """,
            "SELECT TOP 200 * FROM INVE01 ORDER BY DESCR",
        ], "productos")
        if productos:
            datos["productos"] = productos

        # Facturas
        facturas = self._intentar_queries([
            """
            SELECT TOP 200
                CVE_DOC as folio, SERIE as serie,
                FECHA_DOC as fecha, CVE_CLIEN as cliente,
                IMPORTE as importe, IMP_TOT1 as iva,
                CAN_TOT as total, STATUS as estatus,
                UUID as uuid
            FROM FACM01
            ORDER BY FECHA_DOC DESC
            """,
            "SELECT TOP 200 * FROM FACT01 ORDER BY FECHA_DOC DESC",
        ], "facturas")
        if facturas:
            datos["facturas"] = facturas

        # Cuentas por cobrar
        cxc = self._intentar_queries([
            """
            SELECT TOP 200
                NUM_CXC as numero, CVE_CLIEN as cliente,
                DOC_CXC as documento, FECHA_CXC as fecha,
                IMPORTE as importe, SALDO as saldo,
                FECHA_VEN as vencimiento
            FROM CUEN_M01
            WHERE SALDO > 0
            ORDER BY FECHA_VEN
            """,
        ], "cuentas_por_cobrar")
        if cxc:
            datos["cuentas_por_cobrar"] = cxc

        return datos

    def _extraer_coi(self) -> dict:
        """Extrae datos de Aspel COI (contabilidad)."""
        datos = {}

        # Pólizas
        polizas = self._intentar_queries([
            """
            SELECT TOP 200
                TIPO_POLI as tipo, NUM_POLIZ as numero,
                FECHA as fecha, CONCEPTO as concepto,
                DIESSION as periodo
            FROM CPOL01
            ORDER BY FECHA DESC
            """,
            "SELECT TOP 200 * FROM CPOL01 ORDER BY FECHA DESC",
        ], "polizas")
        if polizas:
            datos["polizas"] = polizas

        # Cuentas contables
        cuentas = self._intentar_queries([
            """
            SELECT TOP 200
                NUM_CTA as cuenta, DESC_CTA as descripcion,
                TIPO_CTA as tipo, ACUM_ANT as acumulado_anterior,
                SALDO_FIN as saldo_final
            FROM CCUE01
            ORDER BY NUM_CTA
            """,
        ], "cuentas_contables")
        if cuentas:
            datos["cuentas_contables"] = cuentas

        return datos


class AspelFileConnector(ERPMexicanoFileBase):
    """Procesamiento de archivos exportados de Aspel."""

    ERP_NAME = "aspel"
    ENV_PREFIX = "ASPEL"
