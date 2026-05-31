"""
Catálogo del mercado alfa — 5 tipos documentales (B2 §6.2).

Todos presentes desde el diseño (Adenda §6): ninguno se descarta ni se difiere.
Ajustables por feedback de pilotos. Cada módulo exporta `SCHEMA: DocumentSchema`.
"""
from app.schemas_documentales.base import DocumentSchema
from app.schemas_documentales.catalogo import (
    calibracion,
    especificacion,
    ficha_tecnica,
    manual_tecnico,
    msds,
)

# Catálogo indexado por tipo_documento.
CATALOGO: dict[str, DocumentSchema] = {
    manual_tecnico.SCHEMA.tipo_documento: manual_tecnico.SCHEMA,
    msds.SCHEMA.tipo_documento: msds.SCHEMA,
    calibracion.SCHEMA.tipo_documento: calibracion.SCHEMA,
    especificacion.SCHEMA.tipo_documento: especificacion.SCHEMA,
    ficha_tecnica.SCHEMA.tipo_documento: ficha_tecnica.SCHEMA,
}

__all__ = ["CATALOGO"]
