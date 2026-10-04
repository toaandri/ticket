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

COPY backend/ /build/
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install ".[dev]"

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
