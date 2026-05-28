FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ARIA_CLOUD=true \
    PORT=8080 \
    ARIA_DATA_DIR=/data \
    DB_PATH=/data/aria.db \
    CHROMA_PATH=/data/chroma_db \
    GOOGLE_CREDENTIALS_DIR=/data/google_credentials

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "run.py"]
