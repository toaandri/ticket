# Ticket — Implementation Plan

## Phased delivery (spec §18)

Each phase has a clear gate. A phase is **complete** only when its gate tests pass
on a fresh checkout with `docker compose up --build` + `make migrate`.

---

## Phase 0 — Discovery & Scaffold ✅
**Gate**: fresh compose starts, health endpoints respond, lint baseline passes.

### Deliverables
- [x] Monorepo structure (`backend/`, `web/`, `mobile/`, `packages/`, `docs/`, `infra/`, `.github/`)
- [x] `backend/pyproject.toml` — pinned Python 3.12 + Django 5.0 + DRF + Celery + Channels + pytest + Ruff
- [x] `backend/config/settings.py` — all settings via env vars, custom User model declared, AUTH_USER_MODEL set
- [x] `backend/config/asgi.py` — Channels ASGI with HTTP + WebSocket router
- [x] `backend/config/celery.py` — Celery app, autodiscover
- [x] `backend/config/urls.py` — health check + OpenAPI + admin + api/v1/
- [x] `backend/config/exceptions.py` — uniform `{code, message, details, request_id}` error schema
- [x] `backend/manage.py`
- [x] `docker-compose.yml` — postgres, redis, backend, celery_worker, celery_beat, web, mailpit
- [x] `docker-compose.test.yml` — isolated test services (tmpfs postgres)
- [x] `infra/docker/backend.Dockerfile` — multi-stage, non-root
- [x] `infra/docker/web.Dockerfile`
- [x] `.env.example` — all required vars documented
- [x] `Makefile` — setup, up, down, migrate, seed, test, lint, format, schema, concurrency-test
- [x] `.github/workflows/ci.yml` — backend-lint, backend-test, schema-check, web, mobile, secret-scan
- [x] `web/package.json` — React 18 + Vite 5 + TanStack Query + Zod + Tailwind + Vitest
- [x] `web/vite.config.ts`, `tsconfig.json`, `tailwind.config.js`, `postcss.config.js`
- [x] `web/src/App.tsx`, `main.tsx`, `index.css` — skeleton
- [x] `mobile/package.json` — Expo 51 + Expo Router + expo-camera + expo-secure-store
- [x] `mobile/app.json`, `tsconfig.json`
- [x] `mobile/app/_layout.tsx`, `app/index.tsx` — skeleton
- [x] `packages/api-client/package.json`
- [x] `backend/tests/conftest.py` — pytest fixtures (api_client, auth_client)

### ADRs to write in Phase 0
- [ ] ADR-001: Authentication strategy (session+CSRF vs JWT+refresh dual)
- [ ] ADR-002: Money representation (integer minor units + ISO 4217)
- [ ] ADR-003: Concurrency strategy (select_for_update, SeatClaim, InventoryBucket)
- [ ] ADR-004: Payment provider abstraction (MockPaymentProvider + StripeTestPaymentProvider)
- [ ] ADR-005: Expo SDK and secure token storage

---

## Phase 1 — Accounts & Tenants
**Gate**: auth and cross-org tests pass; migration clean.

### Deliverables
- [ ] `apps/accounts/models.py` — custom `User` (UUID PK, email CITEXT-equiv, email_verified_at)
- [ ] `apps/accounts/migrations/0001_initial.py`
- [ ] `apps/accounts/services.py` — register, verify_email, change_password, request_password_reset
- [ ] `apps/accounts/serializers.py` — register, login, profile
- [ ] `apps/accounts/views.py` — POST register, login, logout, refresh, password-reset, email-verify; GET/PATCH me
- [ ] `apps/accounts/urls.py`
- [ ] `apps/organizations/models.py` — Organization, Membership, Invitation, EventStaffAssignment
- [ ] `apps/organizations/migrations/`
- [ ] `apps/organizations/services.py` — create_org, invite_member, accept_invitation, update_role
- [ ] `apps/organizations/serializers.py`
- [ ] `apps/organizations/views.py`
- [ ] `apps/organizations/urls.py`
- [ ] `apps/audit/models.py` — AuditLog (append-only)
- [ ] Role permission matrix in `docs/security/role-matrix.md`
- [ ] Tests: registration, login, JWT refresh, cross-org denial, scanner cannot access finance, invitation flow

---

## Phase 2 — Venues & Events
**Gate**: organizer can publish valid GA/assigned/mixed event; invalid configurations rejected.

### Deliverables
- [ ] `apps/venues/models.py` — Venue, VenueSection, Seat (with layout freeze logic)
- [ ] `apps/events/models.py` — Event, EventSection, EventSeat, EventTicketType
- [ ] Migrations for both
- [ ] Services: create_venue, add_section, add_seats (bulk), freeze_layout, create_event, publish_event, cancel_event
- [ ] Tests: venue layout freeze after tickets issued, invalid event config rejected

---

## Phase 3 — Inventory & Holds
**Gate**: seat and GA race tests pass repeatedly on PostgreSQL.

### Deliverables
- [ ] `apps/inventory/models.py` — InventoryBucket, SeatClaim, SeatClaimHistory
- [ ] `apps/reservations/models.py` — Reservation, ReservationItem
- [ ] Reservation service: create_hold (GA + assigned), expire_holds Celery task
- [ ] Concurrency tests: 2 buyers for same seat → exactly 1 hold; 100 buyers for GA-20 → ≤20 held+sold

---

## Phase 4 — Orders & Pricing
**Gate**: no duplicate orders; exact minor-unit arithmetic; expired checkout rejection.

### Deliverables
- [ ] `apps/orders/models.py` — Order, OrderItem
- [ ] Checkout service: create_order_from_reservation, apply_promotion, pricing snapshots
- [ ] `apps/promotions/models.py` — Promotion, PromotionRedemption
- [ ] Tests: duplicate order prevention, promotion limits, expiry rejection

---

## Phase 5 — Mock Payments
**Gate**: full demo checkout including failure/late success/replay.

### Deliverables
- [ ] `apps/payments/models.py` — PaymentAttempt, PaymentEventInbox, Refund
- [ ] `apps/payments/providers/base.py` — PaymentProvider protocol
- [ ] `apps/payments/providers/mock.py` — MockPaymentProvider (success/decline/pending/timeout/delayed/refund)
- [ ] Ticket issuance on PAID, idempotent, one ticket per admission
- [ ] Tests: delayed success after expiry → no ticket; webhook replay → one issuance; refund replay → one refund

---

## Phase 6 — Stripe TEST Mode (optional)
**Gate**: signed test webhook; replay and out-of-order tests; mock still works without keys.

### Deliverables
- [ ] `apps/payments/providers/stripe_test.py` — StripeTestPaymentProvider
- [ ] Webhook inbox with signature verification
- [ ] Stripe CLI local setup instructions in docs

---

## Phase 7 — Tickets & Gate
**Gate**: one accepted scan under race; revoked/invalid/foreign-event blocked.

### Deliverables
- [ ] `apps/tickets/models.py` — Ticket, TicketTransfer
- [ ] `apps/checkins/models.py` — CheckIn
- [ ] QR generation (HTTPS URL, >=128-bit entropy, hash stored)
- [ ] PDF ticket generation (ReportLab)
- [ ] Atomic check-in service: lock Ticket → verify → write ACCEPTED; duplicate → 409
- [ ] Concurrent check-in race test → exactly 1 ACCEPTED

---

## Phase 8 — Public Web
**Gate**: Playwright attendee journey on mock provider; accessible responsive screens.

### Deliverables
- [ ] Event discovery, detail, seat selection, checkout, wallet
- [ ] Timed hold countdown (server expires_at)
- [ ] Protected account/order routes
- [ ] Playwright E2E tests (full attendee journey)

---

## Phase 9 — Organizer Web
**Gate**: organizer end-to-end; cross-org denial.

### Deliverables
- [ ] Venue/event editor, inventory dashboard, orders/refunds, promotions, team management
- [ ] Gate scanner UI
- [ ] Analytics page

---

## Phase 10 — Mobile App
**Gate**: documented emulator/device smoke test; token security; API parity.

### Deliverables
- [ ] Attendee: event discovery, seat selection, checkout, wallet, QR display
- [ ] Scanner: camera QR scan, online-only, accepted/duplicate/invalid feedback
- [ ] Secure token storage (expo-secure-store)
- [ ] Manual QA checklist + screenshots

---

## Phase 11 — Realtime & Notifications
**Gate**: post-commit event correctness; retry/idempotence; reconnect refetch.

### Deliverables
- [ ] Django Channels: `/ws/events/{id}/availability/` — availability broadcast post-commit
- [ ] Celery: expiry, reconciliation, email templates (verification, ticket, reminder, cancellation, refund)
- [ ] Outbox pattern for must-deliver side effects

---

## Phase 12 — Analytics & Admin
**Gate**: metrics reconcile to fixture orders/refunds; access checks pass.

### Deliverables
- [ ] `apps/analytics/models.py` — EventMetricSnapshot
- [ ] Metrics: tickets_sold, net_revenue, refunds, GA occupancy, assigned occupancy, check-in rate
- [ ] CSV exports (formula injection protection)
- [ ] Admin moderation + audit endpoints

---

## Phase 13 — Hardening
**Gate**: all critical invariants and security tests pass.

### Deliverables
- [ ] Threat model tests (cross-org, BOLA, webhook signature, QR guessing, rate limits, CSRF, CORS)
- [ ] Performance indexes audit
- [ ] a11y audit (WCAG 2.2 AA target)
- [ ] Dependency security scan in CI

---

## Phase 14 — Portfolio Release
**Gate**: independent reviewer can clone, run, test and demonstrate without external credentials.

### Deliverables
- [ ] Deterministic seed: ≥3 orgs, ≥8 events, ≥2 venues, race-test event, 4 role accounts
- [ ] Real screenshots in README
- [ ] All tests passing in CI
- [ ] Tagged release v1.0.0
- [ ] Final gap audit vs spec §19 checklist

---

## Dependency Versions (pinned, Phase 0)

| Component | Version |
|-----------|---------|
| Python | 3.12 |
| Django | 5.0.6 |
| DRF | 3.15.2 |
| drf-spectacular | 0.27.2 |
| psycopg | 3.1.19 |
| Celery | 5.4.0 |
| channels | 4.1.0 |
| simplejwt | 5.3.1 |
| React | 18.3.1 |
| Vite | 5.3.1 |
| TanStack Query | 5.40.0 |
| Tailwind | 3.4.4 |
| Expo | 51.0.14 |
| React Native | 0.74.2 |
| PostgreSQL | 16 |
| Redis | 7 |
| Node.js | 20 |
