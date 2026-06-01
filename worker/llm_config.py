"""
Configuración de modelos del pipeline de ingesta (B2 §5.3).

DOCYAN LDE™ by XCID — worker `docyan-lde-ingest`.

Config validada con el PoC sobre NOM-052 (Adenda §3), DISTINTA del Model Router
de traducción (Pista A). Reglas inviolables:

  - Extracción + Resolution: Gemini 2.5 Flash con prefijo `gemini/` OBLIGATORIO
    (sin el prefijo, LiteLLM defaultea a Vertex AI y falla pidiendo credenciales GCP).
  - QA / consulta: gpt-4o-mini.
  - deduplicate_entities(fuzzy=True) — con await correcto (bug PoC #1).
  - Forzar respuesta en español en el prompt de extracción.
  - Retry con tenacity ante rate limiting de Gemini (PoC: 1,506 retries en multi-doc).

Variables: GEMINI_API_KEY (NO GOOGLE_API_KEY), OPENAI_API_KEY.
"""
from __future__ import annotations

import os

LLM_CONFIG = {
    "extraction_model": "gemini/gemini-2.5-flash",  # prefijo gemini/ OBLIGATORIO
    "qa_model": "gpt-4o-mini",
    "resolution_model": "gemini/gemini-2.5-flash",  # LLMVerifiedResolution
    "deduplicate_fuzzy": True,
    "force_spanish_in_extraction_prompt": True,
    "retry_with_tenacity": True,
}


def _require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(
            f"{name} es requerida por el worker de ingesta. "
            "Configúrala como Fly secret en docyan-lde-ingest."
        )
    return val


def build_extraction_llm():
    """LiteLLM para extracción (Gemini 2.5 Flash). Import perezoso del SDK."""
    from graphrag_sdk import LiteLLM

    _require_env("GEMINI_API_KEY")
    return LiteLLM(model=LLM_CONFIG["extraction_model"], temperature=0.0)


def build_qa_llm():
    """LiteLLM para QA/consulta (gpt-4o-mini)."""
    from graphrag_sdk import LiteLLM

    _require_env("OPENAI_API_KEY")
    return LiteLLM(model=LLM_CONFIG["qa_model"], temperature=0.0)


def build_resolution(embedder=None):
    """
    Estrategia de resolución de entidades (LLMVerifiedResolution con Gemini 2.5
    Flash). Si se pasa el embedder BGE-M3, lo usa para el matching vectorial.
    """
    from graphrag_sdk import LiteLLM, LLMVerifiedResolution

    _require_env("GEMINI_API_KEY")
    llm = LiteLLM(model=LLM_CONFIG["resolution_model"], temperature=0.0)
    return LLMVerifiedResolution(llm=llm, embedder=embedder)


def build_extractor_and_resolver(embedder=None):
    """
    Construye (extractor, resolver) para `GraphRAG.ingest()`, con el wiring exacto
    validado en el PoC (poc_v111_gemini_flash.py):
      extractor = GraphExtraction(llm = Gemini 2.5 Flash)
      resolver  = LLMVerifiedResolution(llm = Gemini 2.5 Flash, embedder = BGE-M3)
    Pasarlos explícitamente a ingest() evita que el SDK use estrategias por defecto
    (que no garantizan extracción con Gemini ni resolución verificada por LLM).
    """
    from graphrag_sdk import GraphExtraction, LiteLLM, LLMVerifiedResolution

    _require_env("GEMINI_API_KEY")
    llm_extraction = LiteLLM(model=LLM_CONFIG["extraction_model"], temperature=0.0)
    extractor = GraphExtraction(llm=llm_extraction)
    resolver = LLMVerifiedResolution(llm=llm_extraction, embedder=embedder)
    return extractor, resolver
