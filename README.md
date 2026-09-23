# Ticket

A portfolio-grade, open-source event management and ticketing platform built as a single GitHub monorepo.

## Project Status

**Current Phase: Phase 0 — Discovery and Scaffold** (Infrastructure only)

- [x] Monorepo structure created
- [x] Docker Compose configuration
- [x] CI/CD pipeline (GitHub Actions)
- [x] Documentation structure
- [ ] Backend implementation (Django + DRF)
- [ ] Web frontend (React + TypeScript + Vite)
- [ ] Mobile app (React Native + Expo)
- [ ] Database migrations & models
- [ ] Authentication & authorization
- [ ] Event & venue management
- [ ] Inventory & reservation engine
- [ ] Orders, payments & checkout
- [ ] QR tickets & check-in
- [ ] Notifications & analytics
- [ ] Demo data & deterministic seeding
- [ ] Automated tests (unit, integration, concurrency)
- [ ] Portfolio release v1.0.0

> **Note**: This is a portfolio/demo project. No real payments, settlement, tax compliance, or PCI card handling. Uses mock payments by default; Stripe Test Mode is optional.

## Architecture

```
ticket/
├── backend/          # Django + DRF + PostgreSQL + Redis + Celery
├── web/              # React + TypeScript + Vite + TanStack Query + Tailwind
├── mobile/           # React Native + Expo + TypeScript
├── packages/api-client/  # Shared OpenAPI-generated TypeScript client
├── docs/             # Product, architecture, ADRs, database, API, security, runbooks, testing
├── infra/            # Dockerfiles, scripts
└── .github/workflows/# CI/CD
```

**Tech Stack**
- **Backend**: Python, Django, Django REST Framework, PostgreSQL, Redis, Celery, Django Channels, pytest, Ruff
- **Web**: React, TypeScript, Vite, React Router, TanStack Query, React Hook Form + Zod, Tailwind CSS
- **Mobile**: React Native, Expo, TypeScript, Expo Router
- **Infrastructure**: Docker Compose, GitHub Actions

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for web/mobile development)
- Python 3.12+ (for backend development)
- Make

### Development Setup

```bash
# Clone and enter repo
git clone https://github.com/toaandri/ticket.git
cd ticket

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Start all services
make up

# Run migrations
make migrate

# Seed demo data (idempotent)
make seed

# Access applications
# Web:      http://localhost:5173
# API:      http://localhost:8000/api/v1/
# Admin:    http://localhost:8000/admin/
# Mailpit:  http://localhost:8025
```

### Demo Accounts (after seeding)

| Role | Email | Password |
|------|-------|----------|
| Platform Admin | admin@ticket.local | demo123 |
| Org Owner | owner@org1.local | demo123 |
| Org Manager | manager@org1.local | demo123 |
| Gate Scanner | scanner@org1.local | demo123 |
| Attendee | attendee@local | demo123 |

## Key Features

### Implemented (Scaffold)
- Complete monorepo structure
- Docker Compose with PostgreSQL, Redis, backend, web, Celery worker/beat, Mailpit
- GitHub Actions CI pipeline
- Documentation structure with ADRs
- Shared API client package

### Planned (Per Specification)
- **Multi-tenant organizations** with role-based access (Owner, Manager, Editor, Finance, Scanner)
- **Venue management** with sections, seats, accessibility info, frozen layout versions
- **Event management** (GA, assigned seating, mixed) with ticket types, pricing, quotas
- **Reservation engine** with timed holds (default 10 min), atomic seat claims, GA buckets
- **Orders & checkout** with immutable pricing snapshots, promotions, idempotency
- **Mock payment provider** (success, decline, pending, timeout, delayed success, refunds)
- **Optional Stripe Test Mode** (PaymentIntents, verified webhooks, no real transactions)
- **QR tickets** with cryptographically secure secrets, PDF generation, wallet endpoints
- **Atomic check-in** (online-only v1) with duplicate/revoked/invalid detection
- **Real-time availability** via Django Channels (best-effort hints, API authoritative)
- **Notifications** (email via Celery, in-app, templates for verification, tickets, reminders)
- **Analytics** (sales, occupancy, check-in rates, CSV exports with formula injection protection)
- **Audit trails** (append-only, privilege changes, refunds, scans, inventory adjustments)
- **Deterministic demo seed** (≥3 orgs, ≥8 events, ≥2 venues, 4 role accounts, race-test fixtures)

## Documentation

| Doc | Description |
|-----|-------------|
| [Implementation Plan](docs/implementation-plan.md) | Phased tasks with acceptance checklists |
| [Progress](docs/progress.md) | Completed work, blockers, next commands |
| [Architecture ADRs](docs/adr/) | Architecture Decision Records |
| [Database](docs/database/) | ERD, migrations, constraints, indexes |
| [API](docs/api/) | OpenAPI spec, examples, errors, idempotency |
| [Security](docs/security/) | Threat model, role matrix, privacy |
| [Runbooks](docs/runbooks/) | Expiration, reconciliation, webhook replay, restore |

## Testing

```bash
# Backend tests (requires PostgreSQL)
make test

# Frontend tests
make web-test

# Mobile tests
make mobile-test

# Concurrency/race tests
make concurrency-test
```

## Deployment (Example)

See [deployment runbook](docs/runbooks/deployment.md) for:
- HTTPS, managed DB, Redis restrictions
- Migrations, static/media handling
- Worker scaling, observability
- Stripe test webhook configuration
- Backup/restore, health checks, rollback

> **Warning**: Production deployment requires legal/security review. This is a portfolio demo, not a production payment processor.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE) — see LICENSE file for details.