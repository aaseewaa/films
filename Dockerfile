# ── Stage 1: сборка React ─────────────────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /app/front
ENV NODE_OPTIONS=--max-old-space-size=4096
COPY front/package.json front/package-lock.json* ./
RUN npm ci
COPY front/ ./
RUN npm run build

# ── Stage 2: FastAPI + статика ────────────────────────────────────
FROM python:3.11-slim-bookworm
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STATIC_DIR=static \
    APP_DEBUG=false \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      gcc libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements-prod.txt .
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --prefer-binary -r requirements-prod.txt

ENV HF_HOME=/app/.cache/huggingface
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-small')"

COPY backend/ .
COPY --from=frontend /app/front/dist ./static

EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
