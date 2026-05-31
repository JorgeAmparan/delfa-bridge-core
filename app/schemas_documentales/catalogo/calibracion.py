"""
Schema: Certificado de calibración (B2 §6.2).

Instrumentos, certificados, mediciones, fechas de vencimiento, técnico.
Mapeo de visualización: Tipo 6 (eventos operativos) y Tipo 7 (alertas
administrativas de vencimiento — SOLO administrativas, CLAUDE.md §11.1).
"""
from app.schemas_documentales.base import DocumentSchema, EntidadSchema, RelacionSchema

SCHEMA = DocumentSchema(
    tipo_documento="calibracion",
    descripcion=(
        "Certificado de calibración de instrumentos: instrumento, certificado, "
        "mediciones registradas, fecha de vencimiento y técnico responsable."
    ),
    entidades=[
        EntidadSchema("Instrumento", "Instrumento o equipo calibrado.",
                      ["nombre", "modelo", "numero_serie", "fabricante"]),
        EntidadSchema("CertificadoCalibracion", "Certificado emitido.",
                      ["folio", "norma_referencia", "fecha_emision", "laboratorio"]),
        EntidadSchema("MedicionRegistrada", "Una medición o lectura registrada.",
                      ["magnitud", "valor", "unidad", "incertidumbre"]),
        EntidadSchema("FechaVencimiento", "Fecha de vencimiento de la calibración.",
                      ["fecha", "periodo"]),
        EntidadSchema("Tecnico", "Técnico o metrólogo responsable.",
                      ["nombre", "acreditacion"]),
    ],
    relaciones=[
        RelacionSchema("CERTIFICA", "CertificadoCalibracion", "Instrumento",
                       "Un certificado calibra un instrumento."),
        RelacionSchema("REGISTRA_MEDICION", "CertificadoCalibracion", "MedicionRegistrada",
                       "Un certificado registra mediciones."),
        RelacionSchema("VENCE_EN", "CertificadoCalibracion", "FechaVencimiento",
                       "Un certificado tiene fecha de vencimiento."),
        RelacionSchema("EMITIDO_POR", "CertificadoCalibracion", "Tecnico",
                       "Un certificado es emitido por un técnico."),
    ],
    prompt_extraccion=(
        "Eres un extractor de conocimiento de certificados de calibración "
        "metrológica. Extrae el instrumento calibrado (modelo, número de serie, "
        "fabricante), los datos del certificado (folio, norma de referencia, "
        "laboratorio), las mediciones registradas (magnitud, valor, unidad, "
        "incertidumbre), la fecha de vencimiento de la calibración y el técnico "
        "responsable. Las fechas de vencimiento son administrativas (vigencias), "
        "no decisiones operativas. Responde SIEMPRE en español, conservando "
        "unidades y nomenclatura metrológica en su forma original."
    ),
    tipos_intencion_visualizacion=[6, 7],
    palabras_clave=[
        "calibración", "calibration", "certificado", "certificate", "metrología",
        "metrology", "incertidumbre", "uncertainty", "trazabilidad", "traceability",
        "vencimiento", "instrumento", "patrón", "iso 17025", "acreditación",
    ],
)
