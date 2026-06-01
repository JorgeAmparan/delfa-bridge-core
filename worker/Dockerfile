# docyan-lde-ingest — worker de ingesta (B2 §4.1).
# Stack pesado AISLADO del backend: Docling + GraphRAG-SDK + LiteLLM + PyTorch CPU.
# Se construye desde la RAÍZ del repo (necesita app/ y worker/):
#   flyctl deploy --app docyan-lde-ingest --dockerfile worker/Dockerfile
FROM python:3.11-slim

WORKDIR /srv

# Dependencias de sistema:
#  - tesseract-ocr(+spa/eng): OCR SIN PyTorch (alternativa a EasyOCR para no
#    arrastrar modelos torch extra; §3). Docling usa el motor que se configure.
#  - libgl/ libglib: dependencias nativas de procesamiento de imágenes/Docling.
#  - curl: health checks.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng \
    libgl1 libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip

# 1) PyTorch CPU-only PRIMERO, desde el índice CPU de PyTorch. Así pip NO arrastra
#    la build CUDA (~3 GB de wheels nvidia). docling-ibm-models y gliner lo exigen
#    (§3). Versión dentro del rango que pide docling-ibm-models (torch<3,>=2.2.2).
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
    "torch==2.8.0" "torchvision==0.23.0"

# 2) Resto del stack del worker (torch ya satisfecho → no se re-resuelve a CUDA).
#    build-essential se instala SOLO para compilar paquetes sin wheel (hnswlib, dep
#    de graphrag-sdk, necesita g++ con C++11) y se PURGA en la MISMA capa, así no
#    infla la imagen final (importante por el margen al límite de unpack de Fly).
#    Verificado: sin compilador el build falla con "Unsupported compiler" (B2.2).
COPY worker/requirements.txt /srv/worker/requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && pip install --no-cache-dir -r /srv/worker/requirements.txt \
    && apt-get purge -y build-essential && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# 3) Precarga de modelos de Docling EN BUILD (arranque sin red, HF_HUB_OFFLINE).
#    SOLO layout + tableformer (núcleo para PDF con tablas del mercado alfa); NO los
#    VLM pesados (smoldocling/granite) ni easyocr — el OCR lo hace el binario
#    tesseract (apt), configurado en worker/ingest_pipeline.py. Verificado (B2.2):
#    `DocumentConverter()` NO descargaba nada (preload anterior era no-op); este
#    comando sí deja los modelos en la imagen para que convert() funcione offline.
RUN docling-tools models download layout tableformer
# Ruta donde quedaron los modelos; el pipeline la pasa como artifacts_path para que
# convert() los use offline (sin esto, convert() intenta snapshot_download desde HF
# y con HF_HUB_OFFLINE=1 falla — verificado en B2.2).
ENV DOCLING_ARTIFACTS_PATH=/root/.cache/docling/models

# Código: el worker importa el paquete `app` (embedder_adapter, dkg_ontology,
# schemas_documentales, jobs) y `worker`.
COPY app /srv/app
COPY worker /srv/worker

# Offline para HF en runtime (modelos ya en la imagen) — patrón del embedder B1.
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
ENV PORT=8000
EXPOSE 8000

# flycast (privado): el backend encola en Redis; el worker consume. El health se
# sirve por docyan-lde-ingest.flycast:8000. Un solo worker uvicorn: la ingesta es
# pesada (torch+Docling), replicar multiplicaría RAM; el escalado es por máquinas.
CMD ["sh", "-c", "uvicorn worker.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
