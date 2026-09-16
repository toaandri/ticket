# Ticket 🎟️

**An open-source event management and ticketing platform.**

Ticket is a portfolio project for discovering events, reserving tickets, managing organizers and venues, and validating entry with QR codes. It is designed as a single monorepo with a Django API, a React web application, and a dedicated React Native mobile application.

> **Project status: Planned / work in progress.** This README describes the intended scope, not features that are already implemented. Update the status and screenshots as development progresses.
>
> **Demo-first:** All event data is synthetic. Mock checkout is the default; optional Stripe integration uses **test mode only**. Ticket is not a live ticket marketplace or production payment processor.

## What Ticket aims to offer

| Audience | Planned capabilities |
| --- | --- |
| Attendees | Discover and filter events; select general-admission tickets or numbered seats; reserve temporarily; check out; view orders and QR tickets. |
| Organizers | Create organizations, venues and events; configure ticket types and seating; manage staff, sales, promotions, refunds and analytics. |
| Gate staff | Scan QR tickets, validate admission and detect duplicate or invalid scans. |
| Administrators | Manage platform access, moderation, audit logs and operational issues. |

Additional planned capabilities include live availability updates, email notifications, downloadable tickets, accessible interfaces, and a mobile ticket wallet.

## Engineering highlights

- **Concurrency-safe reservations:** PostgreSQL transactions, row-level locking and database constraints protect numbered seats and general-admission inventory against overselling.
- **Timed holds:** Reservations expire without holding database locks for the duration of checkout.
- **Idempotent operations:** Repeated checkout, payment callbacks and ticket scans must not create duplicate orders, tickets or accepted admissions.
- **Optional payment integration:** A built-in mock provider works without external credentials; Stripe is supported in test mode only, with verified webhooks.
- **Role-based access:** Organization-scoped permissions separate attendee, organizer, gate staff and administrator workflows.
- **Testable architecture:** Automated API, integration, concurrency, web and mobile tests, with CI using real PostgreSQL for critical race conditions.

These are design goals until the corresponding code and tests are complete.

## Tech stack

| Layer | Technologies |
| --- | --- |
| Backend | Python, Django, Django REST Framework |
| Database | PostgreSQL |
| Background jobs | Celery, Redis |
| Real-time updates | Django Channels / WebSockets |
| Web | React, TypeScript, Vite, Tailwind CSS |
| Mobile | React Native, Expo, TypeScript |
| API contract | OpenAPI, shared generated TypeScript client |
| Payments | Mock provider; optional Stripe Test Mode |
| Tooling | Docker Compose, pytest, Vitest, Playwright, GitHub Actions |

Dependency versions and the final implementation choices will be recorded in the repository lockfiles and architecture decisions.

## Architecture

```text
                 React web app          React Native app
                       \                  /
                        \                /
                         Django REST API
                         /      |       \
                Domain services |    WebSockets
                       |        |         |
                   PostgreSQL  Redis  Django Channels
                       ^        |
                       |    Celery workers / beat
                       +--------+

            Mock payments (default)
            Stripe Test Mode (optional, server-side)
```

PostgreSQL is the source of truth for inventory, orders, payments and ticket validity. WebSocket messages are notifications; clients must refresh authoritative availability before checkout.

## Monorepo layout

```text
ticket/
├── backend/                 # Django API and domain modules
├── web/                     # React attendee and organizer web app
├── mobile/                  # Expo / React Native app
├── packages/
│   └── api-client/          # Shared generated API types and client
├── docs/                    # Product, architecture, database, API and testing docs
├── infra/                   # Docker and development scripts
├── .github/workflows/       # CI workflows
├── docker-compose.yml
├── .env.example
└── README.md
```

The backend, web and mobile clients live in **one GitHub repository** and share a single API and database. There are no duplicate backend implementations or separate repositories.

## Getting started

> The commands below describe the **target developer workflow**. They become executable once the corresponding Docker configuration, migrations and seed commands are implemented. Check the repository's current implementation status before running them.

Prerequisites: Git, Docker and Docker Compose. For native mobile development, install Node.js and the Android/iOS tooling required by the selected Expo SDK.

```bash
git clone https://github.com/YOUR_USERNAME/ticket.git
cd ticket
cp .env.example .env
# Fill in the documented development-only environment values.
docker compose up --build
```

Once implemented, follow `docs/` or the Makefile for database migrations and deterministic demo seeding. Use the local development URLs and demo accounts printed by the setup commands; do not assume fixed ports or credentials until they are documented in code.

### Mobile development

The React Native app lives in `mobile/`. After dependencies and Expo configuration are implemented:

```bash
cd mobile
npm install
npx expo start
```

Configure the API URL for your emulator or physical device. `localhost` inside a phone or Android emulator does not necessarily refer to your development computer. Camera-based QR scanning requires device permissions; emulator capabilities may vary.

### Payment modes

- **Mock (default):** No Stripe account, card details or external payment credentials required.
- **Stripe Test Mode (optional):** Configure test-only server-side keys and a webhook signing secret in your untracked `.env`. Never use live keys, store card data or expose secrets to web/mobile clients. Confirm orders from verified backend payment state, not from a browser or app redirect alone.

## Quality and tests

The planned CI pipeline will check Python linting, Django migrations, backend tests, PostgreSQL concurrency tests, frontend type checking and tests, mobile type checking and tests, and API contract consistency.

Critical acceptance scenarios include:

- Two simultaneous requests for one numbered seat cannot both succeed.
- General-admission held plus sold inventory never exceeds capacity.
- Expired holds cannot be purchased through stale requests or late callbacks.
- Replayed payment events cannot issue duplicate tickets.
- Two concurrent scans cannot both accept the same ticket.
- Users cannot access another organization's protected data.

Actual test commands and results will be documented when implemented. No test coverage or CI success is claimed at this stage.

## Development roadmap

- [ ] Foundation: repository, Django, React, Expo, PostgreSQL and Docker.
- [ ] Authentication, organizations and permissions.
- [ ] Events, venues, seating maps and ticket categories.
- [ ] Transaction-safe reservations and timed holds.
- [ ] Orders, mock payments and optional Stripe Test Mode.
- [ ] QR tickets, PDF downloads and atomic check-in.
- [ ] Promotions, refunds, notifications and analytics.
- [ ] Web/mobile polish, accessibility, security review and CI.
- [ ] Demo data, screenshots, deployment notes and final documentation.

The detailed implementation phases and acceptance criteria are maintained in the project specification and `docs/implementation-plan.md` once created.

## Demo and screenshots

Screenshots, a demo video and development-only test accounts will be added **after the relevant features work**. Seeded events, customers and financial figures will be clearly marked as fictional. Do not use real attendees' personal data in public demos.

## Security and limitations

Ticket is an educational portfolio application. It does not currently claim production readiness, regulatory compliance, real-money settlement, offline gate synchronization or guaranteed availability. Before any real-world deployment, complete a security and privacy review, establish operational monitoring and backups, verify payment/legal obligations, and obtain authorization for any real event inventory.

Never commit `.env` files, Stripe keys, tokens, real card information or private customer data. Report security concerns using the repository's `SECURITY.md` once published.

## Contributing and license

Contribution guidelines will be documented in `CONTRIBUTING.md`. **A license has not yet been selected**: choose and add a `LICENSE` file before describing the repository as legally open-source or inviting unrestricted reuse.

---

Built as a full-stack software engineering portfolio project.
