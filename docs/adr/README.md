# Architecture decisions

## ADR-001 — Authentication and tenant scope

Accepted. JWT access stays in memory. Web refresh also stays in memory, so a browser reload requires login. Native refresh uses OS SecureStore and rotates on refresh. Tokens never enter browser storage or URLs. Password changes revoke access through password-hash checks and blacklist refresh tokens. Tenant lookups precede object disclosure; platform administration is an explicit separate capability. Admin status alone grants no organization role.

## ADR-002 — Money and promotions

Accepted. EUR, USD and MGA are represented with two integer decimal places throughout this application's pricing contract. Amounts are immutable snapshots, with zero fees in this release. Percentage discounts round down once and allocate by cumulative integer proportions; per-admission allocations preserve exactly the order total. Stripe adapter behavior for a new currency must be reviewed rather than inferred from a browser formatter. A single event uses one currency. Cross-currency totals are not summed.

## ADR-003 — Concurrency

Accepted. Serialize inventory mutations on Event, with a documented global row-lock order and DB uniqueness/check constraints as independent protection. This is simpler to verify for a portfolio project and limits throughput for exceptionally busy events. No blind automatic retry of unknown money transactions. A transport failure retries the same idempotency key; lock/deadlock failures roll back and can be retried through that same key after investigation. Replay fingerprints reject changed payloads.

## ADR-004 — Payment adapters

Accepted. Default deterministic mock; optional hosted Stripe checkout with TEST keys only. Hosted checkout uses Stripe's PaymentIntent for refunds; the project never receives card data. Provider calls are outside DB transactions and use the persisted payment UUID for provider idempotency. Inbox events and reconciliation are authoritative. The original reservation deadline remains effective. Late successes issue no tickets and trigger compensation. A test browser return only refetches state.

## ADR-005 — Expo and frontend

Accepted. Expo SDK 57 pins compatible native versions; dedicated attendee/wallet/scanner screens use the same API as web. Online gate admission is required. Camera fallback uses manual QR entry. TypeScript 6 checks app code; API generation uses TypeScript 5.9 to match openapi-typescript's declared peer range. React web uses semantic controls and custom CSS with keyboard focus, responsive layouts and reduced motion. Tailwind is not required by the implementation.

## ADR-006 — QR tokens

Accepted. Derive a 256-bit HMAC token from a purpose-separated persistent TICKET_SIGNING_KEY, ticket UUID and token version. Store only SHA-256 lookup hash, derive the token for holder-authorized QR/PDF output. Random UUID alone is not admission authority. Keep the signing key backed up independently when rotating Django's JWT/reset key. Changing the ticket key invalidates existing hashes; rotation requires an explicit versioned migration/reissue workflow. No transfer endpoint is enabled.

## ADR-007 — Outbox, auditing and reconciliation

Accepted. Durable outbox stores aggregate IDs and redacted data, not raw QR/reset/invitation secrets. SMTP is at least once; in-app delivery is deduplicated. Post-commit WebSockets are advisory and anonymous only for publicly available inventory. PostgreSQL triggers protect append-only audit/history, immutable order snapshots and financial deletion. Seed resets retain historical records. Reconciliation is a locked diagnostic; administrators must investigate mismatches, never silently overwrite counters.

## ADR-008 — Release validation limits

Accepted. CI runs real PostgreSQL races and real API browser journeys, plus native component tests and Android compilation. Compilation is not a device camera/SecureStore test. External Stripe TEST credentials and physical-device checks remain explicit integration acceptance steps. Upstream advisory exceptions are documented, time-limited and limited to exact advisory IDs; a new advisory fails CI. This is a runnable portfolio demo, not a certified production payment system.
