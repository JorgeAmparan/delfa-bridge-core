"""
Generador dinámico de schemas (B2 §6.3).

DOCYAN LDE™ by XCID.

Cuando un documento no calza con el catálogo del mercado alfa, en vez de fallar
con 0 relaciones (incidente PoC: schema NOM-052 sobre LGPGIR), el generador
analiza una muestra del documento + el contexto del usuario con Gemini 2.5 Flash
y deriva un schema operable (entidades + relaciones + prompt + mapeo de
visualización tentativo) para esa sesión de ingesta.

Caso documentado: cliente de Pista B sube un tipo no contemplado (ej. acta de
inspección regulatoria de un país nuevo); el generador produce schema en runtime.

Diseño testeable: el LLM se inyecta como `llm_caller(prompt) -> str(JSON)`. En
producción el default usa LiteLLM con `gemini/gemini-2.5-flash` (import perezoso:
litellm vive en el worker). Los tests inyectan un caller que reproduce el caso
LGPGIR sin llamar a la API.
"""
from __future__ import annotations

import json
from typing import Callable

from app.schemas_documentales.base import DocumentSchema

# Prefijo OBLIGATORIO (Adenda §3): sin `gemini/`, LiteLLM defaultea a Vertex AI.
GENERATOR_MODEL = "gemini/gemini-2.5-flash"

# Tamaño de muestra del documento que se envía al generador (chars). Suficiente
# para inferir estructura sin facturar el documento completo.
MUESTRA_CHARS = 8000

LlmCaller = Callable[[str], str]


def _default_llm_caller(prompt: str) -> str:
    """Caller real: Gemini 2.5 Flash vía LiteLLM (import perezoso, worker B2)."""
    from litellm import completion

    resp = completion(
        model=GENERATOR_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    return resp["choices"][0]["message"]["content"]


def _build_prompt(muestra: str, contexto: dict) -> str:
    return (
        "Eres un arquitecto de ontologías de extracción. Analiza la MUESTRA de "
        "documento y el CONTEXTO del usuario, y deriva un schema de extracción de "
        "grafo de conocimiento. Debes producir AL MENOS una entidad y AL MENOS una "
        "relación entre entidades declaradas (nunca devuelvas relaciones vacías).\n\n"
        "Devuelve EXCLUSIVAMENTE un objeto JSON con esta forma:\n"
        "{\n"
        '  "tipo_documento": "<slug_en_snake_case>",\n'
        '  "descripcion": "<una frase>",\n'
        '  "entidades": [{"label": "PascalCase", "descripcion": "...", '
        '"propiedades": ["prop1","prop2"]}],\n'
        '  "relaciones": [{"label": "MAYUSCULAS", "origen": "LabelA", '
        '"destino": "LabelB", "descripcion": "..."}],\n'
        '  "prompt_extraccion": "<instrucción de extracción en español>",\n'
        '  "tipos_intencion_visualizacion": [<enteros 1-11>]\n'
        "}\n"
        "Cada 'origen' y 'destino' de relación DEBE existir en 'entidades'.\n\n"
        f"CONTEXTO: {json.dumps(contexto, ensure_ascii=False)}\n\n"
        f"MUESTRA:\n{muestra[:MUESTRA_CHARS]}\n"
    )


def _parse_schema(raw: str) -> DocumentSchema:
    """Parsea la respuesta JSON del LLM a un DocumentSchema validado."""
    # Tolera fences ```json ... ``` que algunos modelos añaden.
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"): text.rfind("}") + 1]
    data = json.loads(text)
    data["es_generado_dinamicamente"] = True
    schema = DocumentSchema.from_dict(data)
    # Garantía dura del contrato: el generador NO puede devolver 0 relaciones útiles.
    if not schema.entidades:
        raise ValueError("El generador devolvió 0 entidades.")
    if not schema.relaciones:
        raise ValueError("El generador devolvió 0 relaciones (caso LGPGIR a evitar).")
    schema.validar()  # relaciones referencian entidades declaradas
    return schema


class GeneradorSchemas:
    """Deriva schemas de extracción en runtime con Gemini 2.5 Flash."""

    def __init__(self, llm_caller: LlmCaller | None = None):
        self.llm_caller = llm_caller or _default_llm_caller

    def generar(self, muestra_documento: str, contexto: dict | None = None) -> DocumentSchema:
        """
        Genera un schema para un documento fuera de catálogo.

        contexto: industria, operación, par_linguistico, tier, idioma, etc.
        """
        contexto = contexto or {}
        prompt = _build_prompt(muestra_documento, contexto)
        raw = self.llm_caller(prompt)
        return _parse_schema(raw)
