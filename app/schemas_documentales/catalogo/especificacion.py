"""
Schema: Especificación técnica (B2 §6.2).

Especificaciones, parámetros técnicos, tolerancias, unidades de medida.
Mapeo de visualización: Tipo 1 (datos puntuales) y Tipo 8 (comparativos entre
versiones).
"""
from app.schemas_documentales.base import DocumentSchema, EntidadSchema, RelacionSchema

SCHEMA = DocumentSchema(
    tipo_documento="especificacion",
    descripcion=(
        "Especificación técnica: especificaciones con parámetros técnicos, sus "
        "tolerancias y unidades de medida."
    ),
    entidades=[
        EntidadSchema("Especificacion", "Una especificación o requisito técnico.",
                      ["nombre", "descripcion", "categoria"]),
        EntidadSchema("ParametroTecnico", "Un parámetro técnico medible.",
                      ["nombre", "valor_nominal"]),
        EntidadSchema("Tolerancia", "Rango o tolerancia admisible de un parámetro.",
                      ["minimo", "maximo", "nominal"]),
        EntidadSchema("UnidadMedida", "Unidad de medida de un parámetro.",
                      ["simbolo", "nombre"]),
    ],
    relaciones=[
        RelacionSchema("DEFINE_PARAMETRO", "Especificacion", "ParametroTecnico",
                       "Una especificación define parámetros técnicos."),
        RelacionSchema("TIENE_TOLERANCIA", "ParametroTecnico", "Tolerancia",
                       "Un parámetro tiene una tolerancia admisible."),
        RelacionSchema("EXPRESADO_EN", "ParametroTecnico", "UnidadMedida",
                       "Un parámetro se expresa en una unidad de medida."),
    ],
    prompt_extraccion=(
        "Eres un extractor de conocimiento de especificaciones técnicas. "
        "Extrae cada especificación y sus parámetros técnicos con valor nominal, "
        "tolerancia (mínimo/máximo) y unidad de medida. Conserva los valores "
        "numéricos exactos y sus unidades. Ignora texto narrativo no técnico. "
        "Responde SIEMPRE en español, conservando símbolos de unidad y nomenclatura "
        "técnica en su forma original."
    ),
    tipos_intencion_visualizacion=[1, 8],
    palabras_clave=[
        "especificación", "specification", "spec", "parámetro", "parameter",
        "tolerancia", "tolerance", "rango", "nominal", "requisito", "requirement",
        "datasheet técnica", "rating", "valor", "unidad",
    ],
)
