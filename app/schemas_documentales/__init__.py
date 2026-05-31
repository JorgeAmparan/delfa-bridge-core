"""
Librería de schemas documentales por TIPO de documento (B2 §6).

DOCYAN LDE™ by XCID.

Componente CENTRAL del producto (Adenda §6). Hallazgo del PoC: el schema de
extracción debe corresponder al TIPO de documento + contexto del usuario, no solo
al dominio — un schema de norma técnica (NOM-052) extrajo 0 relaciones de una ley
general (LGPGIR). Dos capas:

  1. Catálogo del mercado alfa (5 tipos): manual_tecnico, msds, calibracion,
     especificacion, ficha_tecnica. Cada uno define entidades, relaciones, prompt
     de extracción y mapeo a tipo(s) de intención de visualización.
  2. Generador dinámico (Gemini 2.5 Flash): deriva un schema en runtime cuando el
     documento no calza con el catálogo, en vez de fallar con 0 relaciones.

La librería NO duplica la ontología base del DKG (`app/graph/schemas/
dkg_ontology.py`): la ontología es el grafo objetivo; esta librería controla
*cómo se extrae* hacia ese grafo. Los nodos extraídos se conectan al grafo
unificado del doc 01.

Topología (B1): este paquete vive en el backend (proyecto compartido). El worker
lo importa. `to_sdk_schema()` importa graphrag_sdk de forma perezosa, así el
backend puede importar la librería sin tener el SDK instalado.
"""
from app.schemas_documentales.base import (
    DocumentSchema,
    EntidadSchema,
    RelacionSchema,
)
from app.schemas_documentales.registry import SchemaRegistry
from app.schemas_documentales.selector import SchemaSelector

__all__ = [
    "DocumentSchema",
    "EntidadSchema",
    "RelacionSchema",
    "SchemaRegistry",
    "SchemaSelector",
]
