"""
B2 §10 — test bloqueador: réplica del caso LGPGIR del PoC. Un documento fuera del
catálogo NO debe fallar con 0 relaciones; el generador dinámico produce un schema
con >0 relaciones.

El LLM se inyecta (no se llama a la API en tests). Lo que se verifica es el
contrato del generador: parseo, validación de coherencia y garantía de >0
relaciones útiles.
"""
import json

import pytest

from app.schemas_documentales.generador import GeneradorSchemas
from app.schemas_documentales.selector import SchemaSelector


def _llm_acta(_prompt: str) -> str:
    """Simula a Gemini derivando un schema para una 'acta de inspección'."""
    return json.dumps(
        {
            "tipo_documento": "acta_inspeccion_regulatoria",
            "descripcion": "Acta de inspección regulatoria",
            "entidades": [
                {"label": "Inspeccion", "descripcion": "Visita de inspección",
                 "propiedades": ["folio", "fecha", "autoridad"]},
                {"label": "Hallazgo", "descripcion": "No conformidad detectada",
                 "propiedades": ["descripcion", "gravedad"]},
                {"label": "AccionCorrectiva", "descripcion": "Acción requerida",
                 "propiedades": ["descripcion", "plazo"]},
            ],
            "relaciones": [
                {"label": "DETECTA", "origen": "Inspeccion", "destino": "Hallazgo",
                 "descripcion": "La inspección detecta hallazgos."},
                {"label": "REQUIERE_ACCION", "origen": "Hallazgo",
                 "destino": "AccionCorrectiva",
                 "descripcion": "Un hallazgo requiere acción correctiva."},
            ],
            "prompt_extraccion": "Extrae inspecciones, hallazgos y acciones correctivas.",
            "tipos_intencion_visualizacion": [6, 7],
        }
    )


def test_generador_produce_relaciones_positivas():
    g = GeneradorSchemas(llm_caller=_llm_acta)
    schema = g.generar("Acta de inspección de la autoridad sanitaria...",
                       {"industria": "alimentos", "pais": "Brasil"})
    assert schema.es_generado_dinamicamente
    assert len(schema.entidades) >= 1
    assert len(schema.relaciones) > 0, "el generador NO debe devolver 0 relaciones (caso LGPGIR)"
    # to_sdk_schema() requiere graphrag_sdk, que vive en el worker, NO en el
    # backend ni en requirements.test.txt (separación B0.5/B2). Se salta donde el
    # SDK no está (CI del backend) y corre donde sí (worker/dev).
    pytest.importorskip("graphrag_sdk")
    schema.to_sdk_schema()  # debe construir un GraphSchema válido del SDK


def test_generador_rechaza_schema_sin_relaciones():
    """Si el LLM devuelve 0 relaciones, el generador falla explícito (no silencioso)."""
    def _llm_vacio(_p):
        return json.dumps({
            "tipo_documento": "x", "descripcion": "",
            "entidades": [{"label": "A", "descripcion": "", "propiedades": []}],
            "relaciones": [],
            "prompt_extraccion": "", "tipos_intencion_visualizacion": [],
        })
    g = GeneradorSchemas(llm_caller=_llm_vacio)
    with pytest.raises(ValueError, match="0 relaciones"):
        g.generar("texto", {})


def test_generador_tolera_fences_markdown():
    def _llm_fenced(_p):
        return "```json\n" + _llm_acta(_p) + "\n```"
    g = GeneradorSchemas(llm_caller=_llm_fenced)
    schema = g.generar("texto", {})
    assert len(schema.relaciones) > 0


def test_selector_invoca_generador_fuera_de_catalogo():
    """Un documento sin palabras clave de catálogo cae al generador dinámico."""
    sel = SchemaSelector(registry=None, generador=GeneradorSchemas(llm_caller=_llm_acta))
    res = sel.seleccionar(
        "Acta de la visita de la autoridad. Se levanta el presente documento.",
        "acta-2026.pdf",
    )
    assert res.fue_generado
    assert res.origen == "generado"
    assert len(res.schema.relaciones) > 0
