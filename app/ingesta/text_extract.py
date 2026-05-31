"""
Extracción ligera de texto para el COTIZADOR (B2 §7).

DOCYAN LDE™ by XCID.

El cotizador necesita el texto del documento para medir tokens (tiktoken) ANTES
de ingerir. Esa medición ocurre en el BACKEND (`docyan-lde-api`), que NO carga el
stack pesado (Docling/torch vive en el worker). Por eso aquí se usa un extractor
ligero: pdfminer.six para PDF (sin torch), decode directo para texto plano.

El parseo RICO y multi-formato (tablas complejas, OCR, docx/xlsx/imágenes) lo
hace Docling en el worker durante la ingesta real. La estimación del cotizador es
una cota previa: si el extractor ligero subestima el texto (PDF escaneado sin
capa de texto), el cotizador lo reporta como advertencia y el worker re-mide.
"""
from __future__ import annotations

import pathlib


def extraer_texto(data: bytes, nombre_archivo: str) -> tuple[str, bool]:
    """
    Extrae texto para cotización. Devuelve (texto, confiable).

    `confiable=False` indica que el extractor ligero probablemente subestimó
    (p.ej. PDF escaneado sin capa de texto): el cotizador lo señala y la medición
    fina queda al worker con Docling+OCR.
    """
    ext = pathlib.Path(nombre_archivo).suffix.lower()

    if ext == ".pdf":
        return _extraer_pdf(data)
    if ext in {".txt", ".md", ".csv", ".json", ".xml"}:
        try:
            return data.decode("utf-8", errors="ignore"), True
        except Exception:
            return "", False
    # Otros formatos (docx/xlsx/pptx/imágenes): el parseo lo hace el worker.
    # Para cotización se intenta un decode best-effort; si no, se marca no confiable.
    texto = data.decode("utf-8", errors="ignore")
    confiable = len(texto.strip()) > 200
    return texto, confiable


def _extraer_pdf(data: bytes) -> tuple[str, bool]:
    import io

    try:
        from pdfminer.high_level import extract_text

        texto = extract_text(io.BytesIO(data)) or ""
    except Exception:
        return "", False
    # PDF sin capa de texto (escaneado): poco texto → no confiable, requiere OCR.
    confiable = len(texto.strip()) > 100
    return texto, confiable
