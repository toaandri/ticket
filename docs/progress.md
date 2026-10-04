# Ticket — Progress Log

## Phase 0 — Scaffold (completed)

**Date**: 2024-07

### Files created / written

| File | Description |
|------|-------------|
| `backend/pyproject.toml` | Python deps (Django 5.0.6, DRF 3.15.2, Celery 5.4, Channels 4.1, pytest, Ruff) |
| `backend/manage.py` | Django management entry point |
| `backend/config/settings.py` | Full settings via env vars; AUTH_USER_MODEL=accounts.User set before migrations |
| `backend/config/urls.py` | Health check + admin + OpenAPI + api/v1/ |
| `backend/config/api_urls.py` | API v1 URL router (empty, filled per phase) |
| `backend/config/asgi.py` | Channels ASGI (HTTP + WebSocket) |
| `backend/config/wsgi.py` | WSGI fallback |
| `backend/config/celery.py` | Celery app with DJANGO_SETTINGS_MODULE |
| `backend/config/__init__.py` | Imports celery_app for Django startup |
| `backend/config/exceptions.py` | Uniform `{code, message, details, request_id}` error envelope |
| `backend/config/health.py` | `GET /api/health/` liveness probe |
| `backend/tests/conftest.py` | pytest fixtures: api_client, auth_client |
| `backend/tests/factories.py` | Factory Boy stubs (populated per phase) |
| `docker-compose.yml` | postgres, redis, backend (ASGI/uvicorn), celery_worker, celery_beat, web, mailpit |
| `docker-compose.test.yml` | Isolated test env (tmpfs postgres, redis) |
| `infra/docker/backend.Dockerfile` | Multi-stage, non-root, Python 3.12 |
| `infra/docker/web.Dockerfile` | Node 20 Vite dev server |
| `infra/docker/backend-entrypoint.sh` | Container entrypoint |
| `.env.example` | All env vars documented; no secrets committed |
| `Makefile` | setup, up, down, migrate, seed, test, lint, format, schema, concurrency-test |
| `.github/workflows/ci.yml` | backend-lint, backend-test (PostgreSQL service), schema-check, web, mobile, secret-scan |
| `web/package.json` | React 18 + Vite 5 + TanStack Query + Zod + Tailwind + Vitest |
| `web/vite.config.ts` | Vite config with proxy to backend |
| `web/tsconfig.json`, `tsconfig.node.json` | TypeScript strict config |
| `web/tailwind.config.js`, `postcss.config.js` | Tailwind CSS |
| `web/src/App.tsx`, `main.tsx`, `index.css` | React skeleton |
| `web/src/test/setup.ts` | Vitest + Testing Library setup |
| `mobile/package.json` | Expo 51 + Expo Router 3 + expo-camera + expo-secure-store |
| `mobile/app.json` | Expo config (Android + iOS) |
| `mobile/tsconfig.json` | TypeScript strict |
| `mobile/app/_layout.tsx`, `app/index.tsx` | Expo Router skeleton |
| `packages/api-client/package.json` | openapi-typescript stub |
| `docs/implementation-plan.md` | Phased plan with acceptance checklists |
| `docs/progress.md` | This file |

### Architecture decisions made
- **Auth**: JWT (simplejwt) access token (15 min) + refresh (7 days, blacklisted on rotation) for mobile; session+CSRF supported for browser. ADR-001 to be written.
- **Money**: integer minor units + ISO 4217 currency code. ADR-002 to be written.
- **Custom User**: `AUTH_USER_MODEL = "accounts.User"` set in settings BEFORE first migration (critical).
- **ASGI**: Django Channels 4.1 with channels-redis; HTTP via uvicorn.
- **Celery**: django-celery-beat for scheduler; tasks autodiscovered.
- **Error schema**: uniform `{code, message, details, request_id}` via custom DRF exception handler.

### Outstanding blockers
None — Phase 0 is infrastructure only. All app code starts in Phase 1.

### Next commands
```bash
# 1. Start Phase 1 — implement apps/accounts/models.py (custom User)
# 2. Create first migration
# 3. Implement auth endpoints
# 4. Write cross-org isolation tests
```

### Phase 1 acceptance gates to pass
- [ ] `python manage.py migrate` runs cleanly with custom User
- [ ] POST `/api/v1/auth/register/` creates user, returns JWT pair
- [ ] POST `/api/v1/auth/login/` returns tokens
- [ ] GET `/api/v1/me/` returns authenticated user profile
- [ ] Cross-org tests: org A member cannot read org B resources
- [ ] Scanner role cannot access finance endpoints

## 2026-10-04 — scaffold audit and initial repairs

See [repository-audit.md](repository-audit.md) for the observed baseline, exact corrections, checks and continuation gates. The earlier Phase 0 completion claim is not runtime-verified. Build metadata, backend Docker installation, web entry point, Vite typings and client lint configuration were repaired. Static checks passed; application tests are blocked by executor networking and missing dependencies. No functional phase is marked complete.

## 2026-10-04 — account and organization foundation

Implemented custom UUID User and migrations; account register/login/refresh/logout/profile; verification/password reset; organization ownership and tenant-scoped reads; verified invitations and role management; application audit records. Web and Expo account workspaces use actual backend endpoints. Added web/mobile lockfiles, React interaction tests and native component tests. OpenAPI generation now validates without warnings and has a committed snapshot; CI checks model/migration drift explicitly.

Verified on GitHub Actions run 37221763027 before the final schema/native-test update: 22 PostgreSQL tests passed, 94% Python statement coverage; 3 web interaction tests passed and Vite build succeeded; Python lint/format and mobile lint/typecheck succeeded. Native component tests and strict schema snapshot checks are being run on the final commit. No emulator/device or fresh Docker Compose smoke test has been claimed.

The executor proxy remains unavailable. Development dependencies were recovered as GitHub Actions artifacts and installed locally. Django `check`, `makemigrations --check --dry-run` (with unavailable local DB warning), Ruff checks and strict schema generation pass locally. PostgreSQL integration tests run on real PostgreSQL in CI.

Outstanding: all event/venue/inventory/payment/ticket/gate functionality and the later specification phases; durable notification/outbox handling; seeded demo data; fresh Docker and mobile device checks. No final release tag or completed-product claim.
