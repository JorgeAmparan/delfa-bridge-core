"""B1 §6 — Ontología base del DKG: validación, etiquetas, aristas, introspección."""
import pytest

from app.graph.schemas import dkg_ontology as onto


def test_graph_name_for():
    assert onto.graph_name_for("acme") == "docyan_tenant_acme"
    with pytest.raises(ValueError):
        onto.graph_name_for("")


def test_validate_node_rejects_unknown_label():
    with pytest.raises(ValueError):
        onto.validate_node("NodoInventado", {"x": 1})


def test_validate_tenant_props():
    out = onto.validate_node("Tenant", {"tenant_id": "t1", "nombre": "N", "tipo": "agencia_traduccion"})
    assert out["tipo"] == "agencia_traduccion"


def test_validate_entidad_requires_token_qr():
    with pytest.raises(Exception):
        onto.validate_node("EntidadOperativa", {"tipo": "x"})  # falta token_qr


def test_documento_source_default_fuente_ingesta():
    out = onto.validate_node("DocumentoSource", {"tipo_documento": "NOM", "idioma_origen": "es"})
    assert out["fuente_ingesta"] == "manual"


def test_evento_operativo_supports_consulta_realizada():
    """B1 §6.2 — preparación Playbooks de Consulta (Nivel A futuro)."""
    out = onto.validate_node(
        "EventoOperativo",
        {
            "tipo": "consulta_realizada",
            "usuario_id": "u1",
            "consulta_texto": "¿vigencia del compresor?",
            "tipo_intencion_resuelto": "tipo_6",
        },
    )
    assert out["tipo"] == "consulta_realizada"
    assert out["consulta_texto"]


def test_core_edges_present():
    edges = {(a, t, b) for a, t, b in onto.CORE_EDGES}
    assert ("Tenant", "CONTIENE", "EntidadOperativa") in edges
    assert ("DocumentoSource", "TIENE_TRADUCCION", "DocumentoTraducido") in edges
    assert ("EntidadOperativa", "VERSION_HISTORICA", "EntidadOperativa") in edges


def test_ontology_summary_introspection():
    s = onto.ontology_summary()
    assert s["graph_name_prefix"] == "docyan_tenant_"
    assert "Tenant" in s["node_labels"]
    assert "VERSION_HISTORICA" in s["edge_types"]
    assert "DocumentoSource" in s["versioning_default_on"]
    assert "TerminoTecnico" in s["versioning_default_off"]
