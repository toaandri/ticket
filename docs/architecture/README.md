# Architecture

The API is authoritative. Web and Expo share schema-derived types, not inventory state. PostgreSQL stores all inventory and financial truth; Redis transports advisory hints and Celery tasks. Django ASGI serves HTTP and public availability WebSockets. SMTP and payment network calls run outside database transactions.

## Lock order and races

Mutating services lock an attendee's User row when serializing user-wide idempotency or purchase limits, then Event, Reservation, Order, Payment, inventory buckets ordered by ticket type, and seat claims/tickets. Venue configuration locks Event before Venue. Organization role operations lock Organization. All event inventory writers own the Event lock, so one event's transitions serialize without deadlock-prone per-seat lock combinations. This favors correctness over throughput for large stadium-scale events. A production scale change requires benchmarking and a new lock-order review.

```mermaid
sequenceDiagram
  participant A as Buyer A
  participant B as Buyer B
  participant S as Hold service
  participant DB as PostgreSQL
  A->>S: Hold seat A12 / key A
  S->>DB: Lock User A then Event
  S->>DB: Validate quota; create exclusive SeatClaim
  B->>S: Hold seat A12 / key B
  S->>DB: Buyer B waits for Event lock
  DB-->>A: Commit ACTIVE hold
  DB-->>S: Grant Event lock to B
  S->>DB: Existing seat claim
  S-->>B: 409 conflict
```

GA uses the same event boundary and an InventoryBucket row. Before adding quantity Q, check `capacity - held - sold >= Q`; database checks enforce nonnegative counters and `held + sold <= capacity`. Sold seats retain one unique claim. Expiry releases ACTIVE items exactly once, appends history and deletes only temporary claims. Reconciliation takes the event lock for a consistent read and never repairs counters automatically.

## Checkout and payment

```mermaid
sequenceDiagram
  participant C as Client
  participant API as API
  participant DB as PostgreSQL
  participant P as Mock / Stripe TEST
  C->>API: Create order from hold / idempotency key
  API->>DB: Lock; snapshot prices and promotion; commit
  C->>API: Initiate payment / key
  API->>DB: Record CREATED attempt; commit
  API->>P: Create hosted checkout using attempt UUID
  P-->>API: Provider ID / outcome
  API->>DB: Save attempt; process inbox event atomically
  alt Live hold and successful payment
    API->>DB: Held to sold; consume hold; issue admissions; enqueue email
  else Expired/cancelled hold and successful payment
    API->>DB: No tickets; record compensating refund
  end
  DB-->>C: Authoritative order status
```

An interrupted provider creation resumes with the same attempt UUID and persisted mock scenario. A CREATED attempt older than 30 seconds is retried by reconciliation. Pending Stripe status is checked against the order amount/currency and attempt linkage; a browser return is never evidence of payment. Webhooks require a fresh HMAC signature, test mode and immutable financial linkage. Inbox `(provider,event_id)` deduplicates exact payload digests; a different payload under the same event ID is a conflict. Final paid transitions ignore later failure messages. Refunds reserve selected tickets and amount in a transaction, revoke admission, call the provider outside the transaction and finalize inventory once. Provider outages leave a resumable pending refund.

```mermaid
sequenceDiagram
  participant Scan as Scanner
  participant API as Gate service
  participant DB as PostgreSQL
  Scan->>API: Event, QR token, device ID, key
  API->>DB: Lock User, Event, Ticket
  API->>DB: Check tenant role + scanner assignment + window + token hash
  alt Valid unused admission
    API->>DB: Ticket VALID to USED; one ACCEPTED CheckIn
    API-->>Scan: 201 ACCEPTED
  else Duplicate / foreign / revoked / closed / invalid
    API->>DB: Record rejected scan without foreign ticket ID
    API-->>Scan: 409 typed gate result
  end
```

## Notifications and realtime

Outbox rows and money/state transitions commit together. A worker leases a bounded batch, commits its lease, then sends email outside the transaction. Retries use increasing delay, eight-attempt dead letters and a stable Message-ID. In-app notifications have a unique outbox association. SMTP delivery is at least once: a crash after SMTP acceptance and before `published_at` may resend the email. Stable Message-ID is a deduplication hint, not a guarantee.

Availability callbacks register with `transaction.on_commit`; rollback produces no hint. WebSocket messages contain only event/version/refetch, with allowed-origin checks. Public published events in active organizations are eligible; no ticket/user/token data is broadcast. Redis failure suppresses the advisory operation; HTTP polling and refetch on reconnect restore authoritative state. Beat handles expiration, payment reconciliation, cancellation refunds, outbox delivery and reminders. Run one beat instance.
