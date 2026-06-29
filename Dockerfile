# ── Stage 1: сборка React ─────────────────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /app/front
COPY front/package.json front/package-lock.json* ./
RUN npm ci
COPY front/ ./
RUN npm run build

# ── Stage 2: FastAPI + статика ────────────────────────────────────
FROM python:3.11-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STATIC_DIR=static \
    APP_DEBUG=false

COPY backend/requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY backend/ .
COPY --from=frontend /app/front/dist ./static

EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
