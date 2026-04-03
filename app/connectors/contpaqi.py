import os
from app.connectors.erp_mexicano_base import ERPMexicanoDBBase, ERPMexicanoFileBase
from dotenv import load_dotenv

load_dotenv()


# ─── CONTPAQI CONNECTOR | Panohayan™ ────────────────────────────────────────
#
# Conecta Delfa Bridge a CONTPAQi Comercial / Contabilidad.
# Patrón dual:
#   Opción A — Conexión directa a BD SQL Server (ODBC)
#   Opción B — Archivos exportados (XML CFDI, CSV reportes, PDF)
#
# CONTPAQi usa SQL Server como BD. Tablas principales:
#   admDocumentos, admClientes, admProductos, admMovimientos,
#   contPolizas, contCuentas
# ─────────────────────────────────────────────────────────────────────────────


class CONTPAQiDBConnector(ERPMexicanoDBBase):
    """Conexión directa a la BD de CONTPAQi via ODBC/SQL Server."""

    ERP_NAME = "contpaqi"
    ENV_PREFIX = "CONTPAQI"

    def extraer_datos(self) -> dict:
        datos = {}

        # Facturas / Documentos
        facturas = self._intentar_queries([
            """
            SELECT TOP 200
                d.CFOLIO as folio, d.CSERIE as serie,
                d.CFECHA as fecha, c.CRAZONSOCIAL as cliente,
                d.CSUBTOTAL as subtotal, d.CIMPUESTO1 as iva,
                d.CTOTAL as total, d.COBSERVACIONES as observaciones,
                d.CESTATUS as estatus
            FROM admDocumentos d
            LEFT JOIN admClientes c ON d.CIDCLIENTEPROVEEDOR = c.CIDCLIENTEPROVEEDOR
            WHERE d.CIDDOCUMENTODE = 4
            ORDER BY d.CFECHA DESC
            """,
            """
            SELECT TOP 200 * FROM admDocumentos
            WHERE CIDDOCUMENTODE = 4
            ORDER BY CFECHA DESC
            """,
        ], "facturas")
        if facturas:
            datos["facturas"] = facturas

        # Clientes
        clientes = self._intentar_queries([
            """
            SELECT TOP 200
                CCODIGOCLIENTE as codigo, CRAZONSOCIAL as razon_social,
                CRFC as rfc, CCURP as curp,
                CDENCOMERCIAL as nombre_comercial,
                CEMAIL1 as email, CTELEFONO1 as telefono,
                CTIPOCLIENTE as tipo, CESTATUS as estatus
            FROM admClientes
            WHERE CTIPOCLIENTE = 1
            ORDER BY CRAZONSOCIAL
            """,
            "SELECT TOP 200 * FROM admClientes ORDER BY CRAZONSOCIAL",
        ], "clientes")
        if clientes:
            datos["clientes"] = clientes

        # Proveedores
        proveedores = self._intentar_queries([
            """
            SELECT TOP 200
                CCODIGOCLIENTE as codigo, CRAZONSOCIAL as razon_social,
                CRFC as rfc, CEMAIL1 as email, CTELEFONO1 as telefono
            FROM admClientes
            WHERE CTIPOCLIENTE = 2
            ORDER BY CRAZONSOCIAL
            """,
        ], "proveedores")
        if proveedores:
            datos["proveedores"] = proveedores

        # Productos
        productos = self._intentar_queries([
            """
            SELECT TOP 200
                CCODIGOPRODUCTO as codigo, CNOMBREPRODUCTO as nombre,
                CPRECIO1 as precio, CSTATUSPRODUCTO as estatus,
                CTIPOPRODUCTO as tipo, CUNIDADBASE as unidad,
                CCLAVESAT as clave_sat
            FROM admProductos
            ORDER BY CNOMBREPRODUCTO
            """,
            "SELECT TOP 200 * FROM admProductos ORDER BY CNOMBREPRODUCTO",
        ], "productos")
        if productos:
            datos["productos"] = productos

        # Movimientos
        movimientos = self._intentar_queries([
            """
            SELECT TOP 200
                m.CNUMEROMOVIMIENTO as num_movimiento,
                m.CUNIDADES as unidades, m.CPRECIO as precio,
                m.CNETO as neto, p.CNOMBREPRODUCTO as producto
            FROM admMovimientos m
            LEFT JOIN admProductos p ON m.CIDPRODUCTO = p.CIDPRODUCTO
            ORDER BY m.CNUMEROMOVIMIENTO DESC
            """,
        ], "movimientos")
        if movimientos:
            datos["movimientos"] = movimientos

        # Pólizas contables (si es CONTPAQi Contabilidad)
        polizas = self._intentar_queries([
            """
            SELECT TOP 200
                CNUMPOLIZA as num_poliza, CTIPOPOLIZA as tipo,
                CFECHA as fecha, CCONCEPTO as concepto,
                CDIARIO as diario
            FROM contPolizas
            ORDER BY CFECHA DESC
            """,
        ], "polizas")
        if polizas:
            datos["polizas"] = polizas

        return datos


class CONTPAQiFileConnector(ERPMexicanoFileBase):
    """Procesamiento de archivos exportados de CONTPAQi."""

    ERP_NAME = "contpaqi"
    ENV_PREFIX = "CONTPAQI"
