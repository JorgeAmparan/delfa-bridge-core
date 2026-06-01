"""
Pipeline de ingesta del worker (B2 §4.1 / §5).

DOCYAN LDE™ by XCID — worker `docyan-lde-ingest`.

Orquestación (Adenda §5):

  Docling (conversión universal + OCR + tablas complejas)
    → GraphRAG-SDK 1.1.1 (extracción al grafo, multi-tenant por graph_name)
    → BGE-M3 self-hosted (embeddings, vía embedder_adapter de B1)
    → deduplicate_entities(fuzzy=True)  [await correcto — bug PoC #1]
    → finalize()
  El provenance (MENTIONED_IN / PART_OF / NEXT_CHUNK + spans de caracteres) es
  nativo del SDK.

Reglas:
  - Multi-tenancy ABSOLUTA: la conexión se crea con graph_name = graph_name_for(
    tenant_id) — el MISMO grafo que el backend lee (app/graph/dkg_ontology).
  - El worker NO cotiza ni reingiere sin confirmación: confía en que el job trae
    una cotización aprobada (el gate es del backend). Verifica esa invariante.
  - BGE-M3, NO OpenAI/Gemini para embeddings (decisión #1).

El stack pesado (graphrag_sdk, docling, litellm, torch) se importa de forma
perezosa: este módulo se puede importar para introspección/tests sin el stack.
"""
from __future__ import annotations

import logging
import os

from app.graph.schemas.dkg_ontology import graph_name_for
from app.jobs.job_models import IngestJob
from worker import llm_config

logger = logging.getLogger("docyan.worker.pipeline")

FALKOR_HOST = os.getenv("FALKOR_HOST") or os.getenv("FALKORDB_HOST", "localhost")
FALKOR_PORT = int(os.getenv("FALKOR_PORT") or os.getenv("FALKORDB_PORT", "6379"))


# ── Conversión Docling ────────────────────────────────────────────────────────


def convertir_a_markdown(path: str) -> str:
    """
    Convierte un documento (PDF/docx/xlsx/pptx/imagen/...) a Markdown con Docling,
    preservando tablas complejas (TableFormer) y aplicando OCR cuando hace falta.
    GraphRAG-SDK ingiere Markdown nativamente.

    Pipeline OFFLINE (HF_HUB_OFFLINE en la imagen del worker): usa los modelos
    layout + TableFormer precargados en build y OCR vía el binario `tesseract`
    (apt, sin modelo HF) — así convert() no requiere red. Para formatos no-PDF,
    Docling usa su pipeline por defecto.
    """
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import (
        PdfPipelineOptions,
        TesseractCliOcrOptions,
    )
    from docling.document_converter import DocumentConverter, PdfFormatOption

    pdf_opts = PdfPipelineOptions()
    pdf_opts.do_table_structure = True  # TableFormer (tablas complejas, núcleo PoC)
    pdf_opts.ocr_options = TesseractCliOcrOptions()  # OCR con el tesseract de apt
    # artifacts_path: directorio donde `docling-tools models download` dejó los
    # modelos en build (layout + tableformer). Sin esto, convert() intenta
    # snapshot_download desde HF y con HF_HUB_OFFLINE=1 falla con
    # LocalEntryNotFoundError (verificado offline en B2.2). Apuntarlo a la ruta del
    # prefetch hace que convert() corra 100% sin red.
    artifacts = os.getenv("DOCLING_ARTIFACTS_PATH")
    if artifacts and os.path.isdir(artifacts):
        pdf_opts.artifacts_path = artifacts
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_opts)}
    )
    result = converter.convert(path)
    return result.document.export_to_markdown()


# ── Construcción del GraphRAG por tenant ──────────────────────────────────────


def _build_graphrag(tenant_id: str, document_schema):
    """
    Construye un GraphRAG apuntando al grafo aislado del tenant.

    Wiring validado en el PoC (poc_v111_gemini_flash.py): el `llm` base del
    GraphRAG es el de QA (gpt-4o-mini); el de EXTRACCIÓN (Gemini 2.5 Flash) NO va
    aquí sino en el `extractor` de `ingest()` (ver procesar()). El embedder es
    BGE-M3 (decisión #1; el PoC usó OpenAI 1536 "por simplicidad", no invalida).
    """
    from graphrag_sdk import ConnectionConfig, FalkorDBConnection, GraphRAG

    from app.graph.embedder_adapter import BGE_M3_DIMENSION, make_bge_m3_adapter

    embedder = make_bge_m3_adapter()
    connection = FalkorDBConnection(
        config=ConnectionConfig(
            host=FALKOR_HOST,
            port=FALKOR_PORT,
            graph_name=graph_name_for(tenant_id),  # multi-tenancy absoluta
        )
    )
    return GraphRAG(
        connection=connection,
        llm=llm_config.build_qa_llm(),  # base = QA (gpt-4o-mini), como el PoC
        embedder=embedder,
        schema=document_schema.to_sdk_schema() if document_schema else None,
        embedding_dimension=BGE_M3_DIMENSION,  # 1024 (BGE-M3), no 256/1536
    )


# ── Pipeline ───────────────────────────────────────────────────────────────────


class IngestPipeline:
    """Procesa un IngestJob: convierte, extrae al grafo, dedup, finaliza."""

    def __init__(self, document_store=None, schema_registry=None):
        self.document_store = document_store
        self.schema_registry = schema_registry

    def _resolver_schema(self, job: IngestJob, muestra: str = ""):
        """
        Resuelve el schema del job: registry del tenant → catálogo → generador
        dinámico (Gemini). La generación ocurre AQUÍ (worker), no en el backend:
        el worker tiene litellm/Gemini; el backend se mantiene <1 GB y sin litellm.
        """
        from app.schemas_documentales.catalogo import CATALOGO

        tipo = job.tipo_forzado or job.tipo_documento
        if tipo:
            if self.schema_registry is not None:
                via_reg = self.schema_registry.resolver(job.tenant_id, tipo)
                if via_reg is not None:
                    return via_reg
            if tipo in CATALOGO:
                return CATALOGO[tipo]

        # Sin tipo de catálogo → generar schema dinámico (evita el caso LGPGIR).
        from app.schemas_documentales.generador import GeneradorSchemas

        schema = GeneradorSchemas().generar(muestra, job.contexto)
        if self.schema_registry is not None:
            try:
                self.schema_registry.registrar(job.tenant_id, schema, es_generado_dinamicamente=True)
            except Exception:  # noqa: BLE001
                logger.warning("no se pudo registrar el schema generado")
        return schema

    async def procesar(self, job: IngestJob, local_path: str) -> dict:
        """
        Ejecuta el pipeline completo para un job confirmado. Devuelve estadísticas.

        `local_path`: ruta local del documento (el worker ya lo descargó del
        document store). `job` debe traer una cotización aprobada (invariante del
        gate; el worker la verifica como defensa en profundidad).
        """
        if job.cotizacion is None or not job.cotizacion.aprobado:
            raise PermissionError(
                f"job {job.job_id}: sin cotización aprobada. El worker NO ingiere "
                "documentos que no pasaron el gate del cotizador (CLAUDE.md §14)."
            )

        markdown = convertir_a_markdown(local_path)
        schema = self._resolver_schema(job, muestra=markdown[:8000])

        graphrag = _build_graphrag(job.tenant_id, schema)
        try:
            # 1. Extracción al grafo del tenant (provenance nativo). Wiring del PoC:
            #    extractor = Gemini 2.5 Flash; resolver = LLMVerifiedResolution con
            #    Gemini + el embedder BGE-M3. Sin pasarlos, el SDK usaría defaults.
            extractor, resolver = llm_config.build_extractor_and_resolver(
                graphrag.embedder
            )
            ingest_result = await graphrag.ingest(
                text=markdown,
                document_id=job.job_id,
                extractor=extractor,
                resolver=resolver,
            )

            # 2. Deduplicación fuzzy — BUG PoC #1: el PoC NO la llamó (653 residuos).
            #    Es async y NO tiene variante _sync → con await.
            duplicados_resueltos = 0
            if llm_config.LLM_CONFIG["deduplicate_fuzzy"]:
                duplicados_resueltos = await graphrag.deduplicate_entities(fuzzy=True)

            # 3. Finalize (async; también existe finalize_sync para contextos sync).
            await graphrag.finalize()
        finally:
            graphrag.close()

        # Marca uso del schema (señal de utilidad para el registry vivo).
        if self.schema_registry is not None and schema is not None:
            try:
                self.schema_registry.marcar_uso(job.tenant_id, schema.tipo_documento)
            except Exception:  # noqa: BLE001 — el conteo de uso no debe tumbar la ingesta
                logger.warning("no se pudo marcar uso del schema %s", schema.tipo_documento)

        # Campos del IngestionResult del SDK (como reporta el PoC).
        return {
            "tipo_documento": schema.tipo_documento if schema else None,
            "document_id": job.job_id,
            "nodos_creados": getattr(ingest_result, "nodes_created", None),
            "relaciones_creadas": getattr(ingest_result, "relationships_created", None),
            "chunks_indexados": getattr(ingest_result, "chunks_indexed", None),
            "duplicados_resueltos": duplicados_resueltos,
            "metadata": getattr(ingest_result, "metadata", {}),
        }
