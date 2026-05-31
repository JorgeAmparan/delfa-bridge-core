"""
B2 §10 — test bloqueador: el selector elige el schema correcto según el tipo de
documento (manual técnico vs MSDS vs ficha técnica), por heurística, ≥90% de
precisión en los tipos del mercado alfa (§6.5).
"""
import pytest

from app.schemas_documentales.catalogo import CATALOGO
from app.schemas_documentales.selector import SchemaSelector

# Muestras representativas (texto + nombre de archivo) por tipo.
CASOS = [
    (
        "manual_tecnico",
        "IB-111-RDA Installation & Instruction Manual.pdf",
        "Installation and instruction manual. Follow each procedure step. "
        "WARNING: de-energize before maintenance. Required tools and PPE.",
    ),
    (
        "msds",
        "SDS-acetona.pdf",
        "Safety Data Sheet. Hazard identification. CAS number 67-64-1. "
        "GHS classification. First aid measures. Personal protective equipment.",
    ),
    (
        "ficha_tecnica",
        "datasheet-modelo-X200.pdf",
        "Product data sheet. Manufacturer: Acme. Model X200. Part number 4471. "
        "Technical features and catalog specifications.",
    ),
    (
        "calibracion",
        "certificado-calibracion-2026.pdf",
        "Certificado de calibración. Trazabilidad metrológica. Incertidumbre. "
        "ISO 17025. Fecha de vencimiento. Instrumento patrón.",
    ),
    (
        "especificacion",
        "spec-tolerancias.pdf",
        "Especificación técnica. Parámetro nominal con tolerancia mínimo/máximo. "
        "Unidad de medida. Requisito de rating.",
    ),
]


@pytest.fixture
def selector():
    # registry=None: el selector usa el catálogo directo; el generador NO se
    # invoca porque todos los casos calzan con el catálogo.
    return SchemaSelector(registry=None)


@pytest.mark.parametrize("esperado,nombre,texto", CASOS)
def test_clasifica_tipo_correcto(selector, esperado, nombre, texto):
    tipo, conf = selector.clasificar_heuristica(texto, nombre)
    assert tipo == esperado, f"esperaba {esperado}, obtuvo {tipo} (conf={conf:.2f})"


def test_precision_heuristica_supera_90pct(selector):
    aciertos = sum(
        1 for esperado, nombre, texto in CASOS
        if selector.clasificar_heuristica(texto, nombre)[0] == esperado
    )
    precision = aciertos / len(CASOS)
    assert precision >= 0.90, f"precisión heurística {precision:.0%} < 90%"


def test_seleccionar_devuelve_schema_de_catalogo(selector):
    esperado, nombre, texto = CASOS[0]
    res = selector.seleccionar(texto, nombre)
    assert res.tipo_documento == esperado
    assert res.origen == "catalogo"
    assert not res.fue_generado
    assert res.schema is CATALOGO[esperado]


def test_tipo_forzado_se_respeta(selector):
    # Un texto de MSDS pero el usuario fuerza manual_tecnico → gana lo forzado.
    res = selector.seleccionar("CAS number hazard", "x.pdf", tipo_forzado="manual_tecnico")
    assert res.tipo_documento == "manual_tecnico"
    assert res.confianza == 1.0
