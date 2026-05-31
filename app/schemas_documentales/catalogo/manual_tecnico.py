"""
Schema: Manual técnico (B2 §6.2).

Procedimientos paso a paso, advertencias de seguridad, herramientas y EPP.
Mapeo de visualización: Tipo 2 (procedimientos paso a paso).
"""
from app.schemas_documentales.base import DocumentSchema, EntidadSchema, RelacionSchema

SCHEMA = DocumentSchema(
    tipo_documento="manual_tecnico",
    descripcion=(
        "Manual técnico / de instalación e instrucciones: procedimientos paso a "
        "paso, advertencias de seguridad, herramientas y equipo de protección."
    ),
    entidades=[
        EntidadSchema("Procedimiento", "Un procedimiento o instrucción operativa completa.",
                      ["nombre", "objetivo", "ambito"]),
        EntidadSchema("Paso", "Un paso individual dentro de un procedimiento.",
                      ["numero", "descripcion", "resultado_esperado"]),
        EntidadSchema("Advertencia", "Aviso de seguridad, precaución o peligro.",
                      ["severidad", "texto", "consecuencia"]),
        EntidadSchema("Herramienta", "Herramienta o instrumento requerido.",
                      ["nombre", "especificacion"]),
        EntidadSchema("EPP", "Equipo de protección personal requerido.",
                      ["nombre", "norma"]),
    ],
    relaciones=[
        RelacionSchema("CONTIENE_PASO", "Procedimiento", "Paso",
                       "Un procedimiento se compone de pasos ordenados."),
        RelacionSchema("TIENE_ADVERTENCIA", "Paso", "Advertencia",
                       "Un paso puede tener advertencias de seguridad asociadas."),
        RelacionSchema("REQUIERE_HERRAMIENTA", "Paso", "Herramienta",
                       "Un paso requiere herramientas específicas."),
        RelacionSchema("REQUIERE_EPP", "Procedimiento", "EPP",
                       "Un procedimiento exige equipo de protección personal."),
    ],
    prompt_extraccion=(
        "Eres un extractor de conocimiento de manuales técnicos industriales. "
        "Identifica procedimientos y descomponlos en sus pasos ordenados. "
        "Extrae toda advertencia de seguridad (peligro/precaución/nota) y vincúlala "
        "al paso o procedimiento correspondiente. Extrae herramientas y equipo de "
        "protección personal (EPP) mencionados. Ignora encabezados, pies de página, "
        "números de página y créditos editoriales. "
        "Responde SIEMPRE en español, conservando los términos técnicos y nombres de "
        "norma en su forma original."
    ),
    tipos_intencion_visualizacion=[2],
    palabras_clave=[
        "manual", "instruction", "installation", "instalación", "instrucciones",
        "procedimiento", "procedure", "paso", "step", "advertencia", "warning",
        "caution", "danger", "peligro", "mantenimiento", "maintenance", "operación",
    ],
)
