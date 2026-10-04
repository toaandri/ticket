# syntax=docker/dockerfile:1
FROM python:3.12-slim AS builder
WORKDIR /build
COPY backend/requirements.lock backend/pyproject.toml ./
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    pip install --no-cache-dir --prefix=/install -r requirements.lock
COPY backend/ ./
RUN PYTHONPATH=/install/lib/python3.12/site-packages pip install --no-cache-dir --no-deps --no-build-isolation --prefix=/install .
FROM python:3.12-slim AS runtime
RUN groupadd --gid 1001 appgroup && useradd --uid 1001 --gid appgroup --no-create-home appuser
COPY --from=builder /install /usr/local
WORKDIR /app
COPY --chown=appuser:appgroup backend/ ./
COPY --chmod=755 infra/docker/backend-entrypoint.sh /entrypoint.sh
RUN mkdir -p /app/mediafiles /app/staticfiles && chown -R appuser:appgroup /app
USER appuser
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8000"]
