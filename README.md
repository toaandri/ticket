# Ticket

An event ticketing demo with general admission, numbered seats, a team workspace and a dedicated Expo attendee/scanner app. Orders, tickets and admission all use the same PostgreSQL backend. Transactions are simulated; Stripe TEST is optional.

![Discovery on the running web application](docs/screenshots/discovery-desktop.png)

## Run locally

Requirements: Docker with Compose v2, Python 3 for environment setup, Node.js 24 for mobile development. No payment, email or cloud account is needed.

```sh
git clone https://github.com/toaandri/ticket.git
cd ticket
make setup       # creates .env with independent random signing keys
make up          # builds, migrates, then starts API, web, workers and Mailpit
make seed        # prints a generated password for synthetic demo accounts
```

| Service | URL |
| --- | --- |
| Web | http://localhost:5173 |
| API | http://localhost:8000/api/v1/ |
| OpenAPI / Swagger | http://localhost:8000/api/schema/swagger-ui/ |
| Local email inbox | http://localhost:8025 |
| PostgreSQL / Redis on the host | localhost:5433 / localhost:6380 |

Sign in as `demo-owner@ticket.example`, `demo-manager@ticket.example`, `demo-editor@ticket.example`, `demo-finance@ticket.example`, `demo-scanner@ticket.example` or `demo-attendee@ticket.example`, using the password printed by `make seed`. These are verified synthetic accounts; none is a platform administrator. Repeating the seed preserves accounts, passwords and transactions. A development-only reset creates another dataset while retaining financial and audit history:

```sh
docker compose run --rm backend python manage.py seed_demo --reset-demo --confirm-reset
```

Choose Garden Sessions, select general admission tickets, hold them, continue to checkout and pay in test mode. The wallet contains authorized QR and PDF downloads. On a numbered event, choose an exact seat. The hold lasts up to ten minutes and is never extended by checkout. Mock decline, pending, delayed and timeout scenarios are available only in development. Pending mock outcomes can be completed using the demo control; they are deliberately not auto-approved by a timer.

The organizer workspace creates venues, numbered layouts, drafts and ticket types, publishes events, manages invitations and roles, assigns scanners, manages promotions, shows reports, exports protected CSV, refunds selected unused admissions and cancels events. Finance can read reports; Scanner sees assigned events without finance access. A platform administrator uses explicit moderation endpoints and has no implicit organization access.

## Mobile

```sh
cd mobile
npm ci
# Android emulator: http://10.0.2.2:8000/api/v1
# iOS simulator: http://localhost:8000/api/v1
# Phone: replace localhost with the computer's LAN address
EXPO_PUBLIC_API_BASE_URL=http://192.168.1.10:8000/api/v1 npm start
```

Use an Expo Go version compatible with SDK 57, or a local development build. On a phone, set the LAN hostname in root `.env` `ALLOWED_HOSTS` and the matching web origins in `CORS_ALLOWED_ORIGINS`, then restart the backend. Phone and computer must reach the same LAN. Open the Expo QR in Expo Go; the app has Discover, My tickets, Account and Scanner tabs. Native refresh credentials use SecureStore; access tokens remain in memory. Camera permissions are requested when scanning. Admission is online only. PDF downloads are authenticated, shared through the OS and removed from app cache afterward.

Mobile TypeScript, component tests and Android bundle compilation are automated. The device checklist in [testing](docs/testing/README.md) records hardware-only checks separately; bundle compilation does not prove camera or Keychain behavior on a physical device.

## Implemented behavior

- UUID accounts, normalized unique emails, password reset, email verification and rotating JWT logout/revocation.
- Organization permissions, email-bound expiring invitations, scanner event assignments and immutable audit records.
- GENERAL, ASSIGNED and MIXED events; numbered and accessible seats; venue layouts frozen on publication.
- Atomic holds, exclusive seat claims, database capacity checks, expiry, request fingerprints and idempotent retries.
- Immutable integer money snapshots, exact promotion allocation, payment inbox replay protection, one ticket per paid admission and late-payment compensation.
- Holder-scoped QR/PDF wallet, online atomic check-in, duplicate/foreign/revoked/closed rejection.
- Full and partial unused-ticket test refunds, cancellation processing, inventory reconciliation, currency-aware metrics and safe CSV.
- Durable email outbox, retry leases, dead letters, in-app notifications, reminders and post-commit availability hints.
- Responsive English web interface, Expo app, OpenAPI-derived shared types and PostgreSQL integration tests.

Transfer, offline admission, real-money payments, image uploads and reserved-seat ticket reconfiguration after publication are intentionally disabled. The local Compose web service is a development server. There is no deployed public URL or production certification. See the [security review](docs/security/README.md), including the current upstream mobile dependency advisories, before exposing a deployment.

## Architecture and stack

```mermaid
flowchart LR
  Web[React web] --> API[Django ASGI / DRF]
  Mobile[Expo app] --> API
  Web <-. availability hints .-> Channels[Channels / Redis]
  API --> PG[(PostgreSQL 16)]
  API --> Outbox[Transactional outbox]
  Outbox --> Worker[Celery worker / beat]
  Worker --> PG
  Worker --> Mail[SMTP / Mailpit]
  Worker --> Providers[Mock / optional Stripe TEST]
  API --> Providers
```

Python 3.12, Django 5.2 LTS, DRF, psycopg 3, Channels, Celery; React 19, TypeScript, Vite, TanStack Query; Expo SDK 57 with its compatible React Native modules. Python requirements and npm lockfiles pin dependencies. [ADRs](docs/adr/README.md) explain coarse event locks, minor units, token storage, QR derivation and outbox delivery semantics.

## Validation

```sh
make test
make concurrency-test
make lint
make schema
cd web && npm ci && npm run typecheck && npm test -- --run && npm run build
cd ../mobile && npm ci && npm run typecheck && npm run lint && npm test
npx expo export --platform android
```

Browser journeys use a fresh synthetic database and a known development-only password:

```sh
docker compose run --rm backend python manage.py seed_demo --password 'synthetic-demo-password-94!'
cd web
npx playwright install chromium
DEMO_PASSWORD='synthetic-demo-password-94!' npx playwright test
```

This seed password option applies only on first creation of that dataset. Repeated E2E purchases accumulate persistent orders; use a disposable database for repeated runs. CI creates fresh PostgreSQL and Redis services, verifies migration/schema drift, runs race tests repeatedly, compiles both clients, runs real API browser journeys, scans secrets and reports dependency advisories. [Recorded checks](docs/testing/README.md) distinguish actual results from manual checks still needed.

![Running organizer report](docs/screenshots/organizer-reports.png)

![Expo app rendered on its web target](docs/screenshots/expo-web-discovery.png)

The Expo screenshot is from the web target using the real API; it is not a physical-device capture.

Screenshots show synthetic development data. Wallet screenshots mask admission QR codes. All event artwork is self-created CSS; no scraped artwork is used.

See [API examples](docs/api/README.md), [ERD](docs/database/README.md), [operations](docs/runbooks/README.md), [contribution guide](CONTRIBUTING.md) and [MIT license](LICENSE).
