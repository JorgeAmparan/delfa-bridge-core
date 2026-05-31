"""
B2 §10 — test bloqueador: un schema generado queda persistido en el registry y es
reutilizable; los schemas generados que demuestran utilidad se proponen como
candidatos a catálogo permanente.

Usa InMemorySchemaStore (sin Supabase). El gate de persistencia se prueba, no se
saltea.
"""
import json

from app.schemas_documentales.generador import GeneradorSchemas
from app.schemas_documentales.registry import (
    UMBRAL_CANDIDATO_CATALOGO,
    InMemorySchemaStore,
    SchemaRegistry,
)
from app.schemas_documentales.selector import SchemaSelector


def _llm(_p):
    return json.dumps({
        "tipo_documento": "acta_inspeccion",
        "descripcion": "Acta de inspección",
        "entidades": [
            {"label": "Inspeccion", "descripcion": "", "propiedades": ["folio"]},
            {"label": "Hallazgo", "descripcion": "", "propiedades": ["gravedad"]},
        ],
        "relaciones": [
            {"label": "DETECTA", "origen": "Inspeccion", "destino": "Hallazgo",
             "descripcion": ""},
        ],
        "prompt_extraccion": "Extrae inspecciones y hallazgos.",
        "tipos_intencion_visualizacion": [6],
    })


def test_schema_generado_persiste_y_es_reutilizable():
    registry = SchemaRegistry(store=InMemorySchemaStore())
    sel = SchemaSelector(registry=registry, generador=GeneradorSchemas(llm_caller=_llm))

    # 1ª ingesta de un tipo fuera de catálogo → genera y persiste.
    r1 = sel.seleccionar("acta de inspección", "acta.pdf", tenant_id="t1")
    assert r1.fue_generado

    # 2ª vez, mismo tenant + tipo forzado → se resuelve del registry, NO regenera.
    schema_persistido = registry.resolver("t1", "acta_inspeccion")
    assert schema_persistido is not None
    assert schema_persistido.tipo_documento == "acta_inspeccion"
    assert len(schema_persistido.relaciones) > 0


def test_registry_aisla_por_tenant():
    registry = SchemaRegistry(store=InMemorySchemaStore())
    sel = SchemaSelector(registry=registry, generador=GeneradorSchemas(llm_caller=_llm))
    sel.seleccionar("acta", "a.pdf", tenant_id="t1")
    # Otro tenant no ve el schema generado de t1.
    assert registry.resolver("t2", "acta_inspeccion") is None


def test_schema_generado_se_propone_candidato_tras_uso():
    registry = SchemaRegistry(store=InMemorySchemaStore())
    sel = SchemaSelector(registry=registry, generador=GeneradorSchemas(llm_caller=_llm))
    sel.seleccionar("acta", "a.pdf", tenant_id="t1")

    # Marca uso repetido (ingesta exitosa) hasta superar el umbral.
    for _ in range(UMBRAL_CANDIDATO_CATALOGO):
        registry.marcar_uso("t1", "acta_inspeccion")

    candidatos = registry.candidatos_a_catalogo("t1")
    assert any(c.tipo_documento == "acta_inspeccion" for c in candidatos)


def test_catalogo_no_se_marca_candidato():
    """Un schema del catálogo (no generado) nunca se propone como 'candidato'."""
    registry = SchemaRegistry(store=InMemorySchemaStore())
    from app.schemas_documentales.catalogo import CATALOGO
    registry.registrar("t1", CATALOGO["manual_tecnico"], es_generado_dinamicamente=False)
    for _ in range(UMBRAL_CANDIDATO_CATALOGO + 2):
        registry.marcar_uso("t1", "manual_tecnico")
    assert registry.candidatos_a_catalogo("t1") == []
