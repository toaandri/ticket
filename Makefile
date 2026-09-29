# =============================================================================
# Ticket — Makefile
# =============================================================================
.PHONY: help setup up down restart logs migrate seed test lint format schema \
        concurrency-test web-test mobile-test backend-shell clean

COMPOSE        = docker compose
COMPOSE_TEST   = docker compose -f docker-compose.test.yml
BACKEND        = $(COMPOSE) exec backend
BACKEND_RUN    = $(COMPOSE) run --rm backend

# Default target
help:
	@echo ""
	@echo "  Ticket — available targets"
	@echo ""
	@echo "  setup            Copy .env.example → .env (once)"
	@echo "  up               Start all services (build if needed)"
	@echo "  down             Stop and remove containers"
	@echo "  restart          Restart all services"
	@echo "  logs             Follow logs for all services"
	@echo "  migrate          Run Django migrations"
	@echo "  seed             Load deterministic demo data (dev only)"
	@echo "  test             Run backend tests against PostgreSQL"
	@echo "  lint             Ruff lint + format check"
	@echo "  format           Auto-format Python code (ruff format)"
	@echo "  schema           Regenerate OpenAPI schema"
	@echo "  concurrency-test Run concurrency/race condition tests"
	@echo "  web-test         Run web frontend tests"
	@echo "  mobile-test      Run mobile tests"
	@echo "  backend-shell    Open Django shell in backend container"
	@echo "  clean            Remove volumes (WARNING: deletes all data)"
	@echo ""

setup:
	@if [ ! -f .env ]; then cp .env.example .env && echo ".env created — edit it before starting"; else echo ".env already exists"; fi

up:
	$(COMPOSE) up --build -d
	@echo ""
	@echo "  Services started:"
	@echo "  Web:      http://localhost:5173"
	@echo "  API:      http://localhost:8000/api/v1/"
	@echo "  Swagger:  http://localhost:8000/api/schema/swagger-ui/"
	@echo "  Admin:    http://localhost:8000/admin/"
	@echo "  Mailpit:  http://localhost:8025"
	@echo ""

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart

logs:
	$(COMPOSE) logs -f

migrate:
	$(BACKEND_RUN) python manage.py migrate --noinput

seed:
	$(BACKEND_RUN) python manage.py seed_demo

test:
	$(COMPOSE_TEST) run --rm backend_test

lint:
	$(BACKEND_RUN) ruff check .
	$(BACKEND_RUN) ruff format --check .

format:
	$(BACKEND_RUN) ruff format .
	$(BACKEND_RUN) ruff check --fix .

schema:
	$(BACKEND_RUN) python manage.py spectacular --color --file /app/../packages/api-client/generated/schema.yml
	@echo "Schema written to packages/api-client/generated/schema.yml"

concurrency-test:
	$(COMPOSE_TEST) run --rm -e PYTEST_ARGS="-m concurrency -v" backend_test

web-test:
	cd web && npm test

mobile-test:
	cd mobile && npx jest

backend-shell:
	$(BACKEND) python manage.py shell

clean:
	@echo "WARNING: This will delete all Docker volumes (database, media, etc.)"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	$(COMPOSE) down -v
