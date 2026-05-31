"""
Selector de schema documental (B2 §6.5).

DOCYAN LDE™ by XCID.

Decide qué schema usar para un documento entrante. Estrategia:

  1. Clasificación heurística primero (nombre de archivo + primeras N páginas +
     palabras clave de cada schema del catálogo). Barata, sin costo de API.
  2. Si la heurística no calza con el catálogo del tenant con confianza
     suficiente → invoca el generador dinámico (Gemini) para derivar un schema.

Decisión técnica del sprint (§6.5): la heurística por palabras clave alcanza
precisión ≥90% en los tipos del mercado alfa (ver test_schema_selector). Por eso
NO se usa Gemini como clasificador previo obligatorio — solo como fallback de
GENERACIÓN cuando no hay match de catálogo, lo que ahorra una llamada LLM por
documento. Si en pilotos la precisión cae <90% para algún tipo, se activa el
clasificador Gemini previo (gancho `clasificar_con_llm`).
"""
from __future__ import annotations

from dataclasses import dataclass

from app.schemas_documentales.base import DocumentSchema
from app.schemas_documentales.catalogo import CATALOGO
from app.schemas_documentales.generador import GeneradorSchemas
from app.schemas_documentales.registry import SchemaRegistry

# Confianza mínima (score normalizado) para aceptar una clasificación heurística.
UMBRAL_CONFIANZA = 0.15


@dataclass
class ResultadoSeleccion:
    schema: DocumentSchema
    tipo_documento: str
    origen: str  # "catalogo" | "registry" | "generado"
    confianza: float
    fue_generado: bool


def _score(texto: str, nombre_archivo: str, schema: DocumentSchema) -> float:
    """Score heurístico: fracción de palabras clave del schema presentes."""
    blob = f"{nombre_archivo}\n{texto}".lower()
    if not schema.palabras_clave:
        return 0.0
    hits = sum(1 for kw in schema.palabras_clave if kw.lower() in blob)
    return hits / len(schema.palabras_clave)


class SchemaSelector:
    """Selecciona el schema de extracción para un documento."""

    def __init__(
        self,
        registry: SchemaRegistry | None = None,
        generador: GeneradorSchemas | None = None,
    ):
        # registry sin store explícito requiere Supabase; en tests se inyecta.
        self.registry = registry
        self.generador = generador or GeneradorSchemas()

    def clasificar_heuristica(
        self, texto_muestra: str, nombre_archivo: str = ""
    ) -> tuple[str | None, float]:
        """Devuelve (tipo_documento, confianza) del mejor match de catálogo."""
        mejor_tipo, mejor_score = None, 0.0
        for tipo, schema in CATALOGO.items():
            s = _score(texto_muestra, nombre_archivo, schema)
            if s > mejor_score:
                mejor_tipo, mejor_score = tipo, s
        return mejor_tipo, mejor_score

    def seleccionar(
        self,
        texto_muestra: str,
        nombre_archivo: str = "",
        tenant_id: str | None = None,
        contexto: dict | None = None,
        tipo_forzado: str | None = None,
    ) -> ResultadoSeleccion:
        """
        Selecciona el schema. Si `tipo_forzado` se da (el usuario declaró el tipo
        en onboarding/UI), se respeta. Si no, clasifica heurísticamente; si no hay
        match confiable, genera un schema dinámico.
        """
        # 1. Tipo declarado por el usuario.
        if tipo_forzado:
            schema = self._resolver_tipo(tipo_forzado, tenant_id)
            if schema is not None:
                return ResultadoSeleccion(schema, tipo_forzado, self._origen(tipo_forzado, tenant_id), 1.0, False)

        # 2. Clasificación heurística contra el catálogo.
        tipo, confianza = self.clasificar_heuristica(texto_muestra, nombre_archivo)
        if tipo is not None and confianza >= UMBRAL_CONFIANZA:
            schema = self._resolver_tipo(tipo, tenant_id)
            if schema is not None:
                return ResultadoSeleccion(schema, tipo, self._origen(tipo, tenant_id), confianza, False)

        # 3. Fuera de catálogo → generador dinámico (evita el caso LGPGIR/0 relaciones).
        schema = self.generador.generar(texto_muestra, contexto)
        if tenant_id is not None and self.registry is not None:
            self.registry.registrar(tenant_id, schema, es_generado_dinamicamente=True)
        return ResultadoSeleccion(schema, schema.tipo_documento, "generado", confianza, True)

    # ── helpers ──────────────────────────────────────────────────────────────
    def _resolver_tipo(self, tipo: str, tenant_id: str | None) -> DocumentSchema | None:
        if tenant_id is not None and self.registry is not None:
            via_registry = self.registry.resolver(tenant_id, tipo)
            if via_registry is not None:
                return via_registry
        return CATALOGO.get(tipo)

    def _origen(self, tipo: str, tenant_id: str | None) -> str:
        if (
            tenant_id is not None
            and self.registry is not None
            and self.registry.store.get(tenant_id, tipo) is not None
        ):
            return "registry"
        return "catalogo"
