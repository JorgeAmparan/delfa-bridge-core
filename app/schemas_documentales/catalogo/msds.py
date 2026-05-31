"""
Schema: MSDS / Hoja de Datos de Seguridad (B2 §6.2).

Sustancias, riesgos, medidas de protección, equipo de protección, número CAS.
Mapeo de visualización: Tipo 6 (eventos operativos + alertas) y Tipo 7 (alertas
administrativas — SOLO administrativas, línea ABSOLUTA CLAUDE.md §11.1).
"""
from app.schemas_documentales.base import DocumentSchema, EntidadSchema, RelacionSchema

SCHEMA = DocumentSchema(
    tipo_documento="msds",
    descripcion=(
        "Hoja de Datos de Seguridad (MSDS/SDS): sustancias químicas, sus riesgos, "
        "medidas de protección, equipo de protección y número CAS."
    ),
    entidades=[
        EntidadSchema("Sustancia", "Una sustancia o mezcla química.",
                      ["nombre", "concentracion", "estado_fisico"]),
        EntidadSchema("Riesgo", "Un peligro o riesgo de la sustancia.",
                      ["tipo", "descripcion", "categoria_ghs"]),
        EntidadSchema("MedidaProteccion", "Medida de control o primeros auxilios.",
                      ["descripcion", "tipo"]),
        EntidadSchema("EquipoProteccion", "Equipo de protección personal requerido.",
                      ["nombre", "parte_cuerpo"]),
        EntidadSchema("NumeroCAS", "Identificador CAS de una sustancia.",
                      ["valor"]),
    ],
    relaciones=[
        RelacionSchema("TIENE_RIESGO", "Sustancia", "Riesgo",
                       "Una sustancia presenta riesgos."),
        RelacionSchema("REQUIERE_MEDIDA", "Riesgo", "MedidaProteccion",
                       "Un riesgo requiere medidas de protección."),
        RelacionSchema("REQUIERE_EQUIPO", "Sustancia", "EquipoProteccion",
                       "Manipular la sustancia exige equipo de protección."),
        RelacionSchema("IDENTIFICADA_POR", "Sustancia", "NumeroCAS",
                       "Una sustancia se identifica por su número CAS."),
    ],
    prompt_extraccion=(
        "Eres un extractor de conocimiento de Hojas de Datos de Seguridad (MSDS/SDS). "
        "Extrae cada sustancia química con su número CAS, sus riesgos (clasificación "
        "GHS si aparece), las medidas de protección y primeros auxilios, y el equipo "
        "de protección personal requerido. Vincula cada riesgo con su medida. "
        "NO emitas recomendaciones clínicas ni decisiones operativas: limítate a "
        "extraer la información presente en el documento (línea de seguridad "
        "regulatoria). Responde SIEMPRE en español, conservando nombres químicos y "
        "números CAS en su forma original."
    ),
    tipos_intencion_visualizacion=[6, 7],
    palabras_clave=[
        "msds", "sds", "safety data sheet", "hoja de datos de seguridad",
        "hoja de seguridad", "cas", "ghs", "hazard", "peligro", "first aid",
        "primeros auxilios", "pictograma", "sustancia", "química", "chemical",
    ],
)
