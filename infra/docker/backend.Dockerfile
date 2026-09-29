# =============================================================================
# Backend Dockerfile — multi-stage, non-root runtime
# =============================================================================

# ---- Build stage ----
FROM python:3.12-slim AS builder

WORKDIR /build

# System deps for psycopg binary and Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml /build/
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install ".[dev]" -e . 2>/dev/null || \
       pip install --no-cache-dir --prefix=/install \
           Django==5.0.6 \
           djangorestframework==3.15.2 \
           django-filter==24.2 \
           drf-spectacular==0.27.2 \
           "psycopg[binary]==3.1.19" \
           django-redis==5.4.0 \
           redis==5.0.7 \
           celery==5.4.0 \
           django-celery-beat==2.6.0 \
           channels==4.1.0 \
           channels-redis==4.2.0 \
           djangorestframework-simplejwt==5.3.1 \
           django-cors-headers==4.4.0 \
           Pillow==10.4.0 \
           python-decouple==3.8 \
           "qrcode[pil]==7.4.2" \
           reportlab==4.2.2 \
           Faker==25.9.2 \
           dj-database-url==2.2.0 \
           whitenoise==6.7.0 \
           structlog==24.2.0 \
           django-extensions==3.2.3 \
           uvicorn[standard]==0.30.1 \
           pytest==8.2.2 \
           pytest-django==4.8.0 \
           pytest-asyncio==0.23.7 \
           pytest-xdist==3.5.0 \
           factory-boy==3.3.0 \
           coverage==7.5.4 \
           ruff==0.5.2

# ---- Runtime stage ----
FROM python:3.12-slim AS runtime

# Non-root user
RUN groupadd --gid 1001 appgroup \
    && useradd --uid 1001 --gid appgroup --no-create-home appuser

# System runtime deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy source
COPY backend/ /app/

# Entrypoint script
COPY infra/docker/backend-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--reload"]
