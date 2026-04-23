FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN sed -i '/pyobjc/d' requirements.txt && \
    sed -i '/ocrmac/d' requirements.txt && \
    sed -i '/^torch==/d' requirements.txt && \
    sed -i '/^torchvision==/d' requirements.txt && \
    sed -i '/^pyodbc==/d' requirements.txt && \
    sed -i '/^cryptography==/d' requirements.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt
    
COPY app/ ./app/

ENV PYTHONPATH=/app
ENV DATA_DIR=/app/data

RUN mkdir -p /app/data

EXPOSE 8000

CMD python3 -m uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT:-8000}