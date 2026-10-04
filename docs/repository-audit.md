# Repository audit — 2026-10-04

## Scope and observed baseline

Completion follows `Ticket_Master_Specification.txt`, sections 00, 18 and 19. The repository is a scaffold, not an implemented ticketing application. The current main commit is b7907a2e302e2c9d56b86917076f95a76d04a730. All domain model, serializer, service, view and application test files are empty. No application migrations or dependency lockfiles exist. The web and Expo screens are placeholders. Phase 0's previously recorded completion is not supported by a working startup verification.

GitHub Actions run 36637427472 failed backend dependency installation and both Node setup steps; schema validation was skipped. This audit does not claim those failures are the only failures.

## Corrections in this change

- Use the existing setuptools PEP 517 build backend instead of the nonexistent `setuptools.backends.legacy` module.
- Declare Uvicorn alongside backend dependencies, matching the Compose ASGI command.
- Build the backend package from actual source and remove the Docker fallback that masked install errors and duplicated the dependency list.
- Provide the web HTML root and React entry script.
- Declare Vite environment types and load the Vite config helper from Vitest so the existing test configuration is typed.
- Add ESLint configuration for both TypeScript clients.

These are scaffold corrections only. They do not implement registration, events, reservations, checkout, QR tickets or mobile journeys.

## Verification actually performed

Python TOML parsing and build-backend import passed. Python source AST parsing passed. Static checks confirmed the declared Uvicorn dependency, the HTML root and entry, and removal of the Docker installation fallback. `node --check web/.eslintrc.cjs` and `node --check mobile/.eslintrc.cjs` passed.

Runtime tests, Django migrations, TypeScript checks, Docker builds and PostgreSQL race tests have NOT run. The managed executor cannot reach its configured HTTP proxy: Git reports `Failed to connect to proxy port 8080`. Django, DRF, Celery, pytest and psycopg are absent. A pip download of Django 5.0.6 from PyPI failed. Repository files were obtained through the GitHub connector; package installation is still blocked. No proxy bypass was attempted.

## Remaining gates and continuation

1. Restore the managed execution environment's package-download networking. Use its supported runtime configuration and retain inherited proxy and TLS settings.
2. Install backend dependencies in a virtual environment. Install web/mobile dependencies and commit reproducible lockfiles before retaining `npm ci` in CI and Docker. Do not switch to unchecked installs merely to make CI green.
3. Complete Phase 1: UUID email-based user and first migration, authentication, organizations/memberships/invitations, role isolation and audit trail. `AUTH_USER_MODEL=accounts.User` currently references an absent model, so Django startup remains blocked.
4. Correct baseline configuration issues revealed by actual startup: the structlog processor is configured as a string rather than an instance; Compose's Vite proxy points at the web container's localhost; Expo references empty/missing image assets and a placeholder EAS project ID. Verify, rather than assume, compatibility of frontend test and mobile dependency versions.
5. Follow the existing implementation plan through backend transaction invariants, payment replay/refunds, QR check-in, web and Expo clients, notifications, analytics, seed and release documentation.
6. Keep each phase gated by its actual tests. Do not mark the project finished until the specification's fresh-clone, PostgreSQL concurrency, web and mobile acceptance checks pass.

No credentials, real payment keys or live payment transactions are required for the specified mock demo. Optional Stripe remains test-only.
