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
COPY worker/requirements.txt /srv/worker/requirements.txt
RUN pip install --no-cache-dir -r /srv/worker/requirements.txt

# 3) Precarga de modelos de layout/tabla de Docling EN BUILD (arranque sin red).
RUN python -c "from docling.document_converter import DocumentConverter; DocumentConverter()" || true

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
