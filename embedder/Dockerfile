# docyan-lde-embedder — BGE-M3 self-hosted (B1 §4).
# El modelo BAAI/bge-m3 se descarga EN BUILD para que el arranque no dependa
# de la red ni de Hugging Face en runtime (imagen autocontenida, reproducible).
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Precarga del modelo en la capa de imagen (sin volumen persistente — decisión B1).
ENV HF_HOME=/app/.hf_cache
ENV BGE_MODEL_NAME=BAAI/bge-m3
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3')"

COPY main.py .

ENV PORT=8000
EXPOSE 8000

# Bind 0.0.0.0: el backend alcanza este servicio por `docyan-lde-embedder.flycast`
# (fly-proxy mediado), que puentea IPv4↔IPv6 y dispara auto-start. Con `::`
# (IPv6-only) el health check TCP de Fly (IPv4) fallaba y reiniciaba la máquina a
# media carga del modelo. flycast es el patrón recomendado para servicio↔servicio
# privado en Fly. B1 §13.
# Un solo worker: el modelo ocupa RAM; replicar workers multiplicaría memoria.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
