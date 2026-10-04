# Operations

Compose is a local demo stack. Run one beat scheduler and scale workers independently from ASGI processes. Readiness of API/database/workers is separate from `/api/health/`, which is a liveness endpoint only.

## Expiry, reconciliation and outbox

Beat runs hold expiry and payment reconciliation every ten seconds, outbox delivery every five seconds and reminder selection hourly. Expiry processes a bounded batch under event locks; concurrent workers skip busy events. If a worker is down, existing hold deadlines remain authoritative in checkout/payment checks; restart workers to release stale counters promptly.

```sh
docker compose logs --tail=100 backend celery_worker celery_beat
docker compose run --rm backend python manage.py reconcile_inventory
```

The diagnostic returns mismatches without modifying anything. Capture affected event/bucket/claim IDs, investigate reservation items and retained tickets under a stable snapshot, identify the failed transition and prepare an audited correction. Do not subtract counters blindly or delete orders. If PostgreSQL detects a deadlock, the transaction rolls back: retry through the original idempotency key after checking the incident, not a new payment identifier.

Outbox attempts acquire a two-minute lease. SMTP failures back off and become dead letters after eight attempts. A superuser may inspect/replay dead letters through the explicit admin API/UI. Fix SMTP reachability first; replay retains its deduplication identity. A crash after SMTP acceptance may produce a duplicate email, while the in-app notification stays unique. Logs identify aggregate IDs, not link secrets or payloads.

## Payment incidents

Provider outages leave CREATED attempts or pending refunds durable. Creation reconciliation resumes attempts older than thirty seconds with the same provider UUID. A pending mock payment deliberately requires the development completion control; it cannot be marked successful by elapsed time alone. Stripe reconciliation checks session identity, TEST mode, amount and currency before applying an outcome.

For a repeated webhook, exact same provider/event ID and payload produces the same transition; a changed digest returns conflict and rolls back. Do not delete inbox rows to force a replay. For amount mismatch, capture only provider/attempt/event IDs, verify the immutable order snapshot and test provider record, then investigate configuration. No money/tickets should change on the mismatched event.

A successful payment after hold expiry/cancellation issues no tickets and queues compensation. Monitor pending refunds and provider errors until completion. Cancellation closes sales immediately, releases active holds and queues cancellation notifications; background processing refunds unused admissions in bounded order batches. Used admissions and historical completed events are preserved. A failed provider refund keeps tickets revoked until the pending request is resolved.

## Optional Stripe TEST integration

Enable STRIPE_ENABLED with an `sk_test_` key and a test webhook secret in the local `.env`; live keys/responses/events are rejected. Restart API and workers. Use Stripe CLI TEST forwarding:

```sh
stripe listen --forward-to localhost:8000/api/v1/payments/stripe/webhook/
```

Set the printed CLI webhook secret locally. Buy through hosted TEST checkout using Stripe's documented test card numbers. Verify the resulting session/PaymentIntent, API PAID order and wallet, replay the signed event and request a test refund. Use the hosted session's real linkage; a generic CLI event with unrelated IDs should not issue tickets. No external Stripe account was used for the recorded local tests; signature/provider fixtures cover the contract. Mock remains fully available without these variables.

## Backup and restore drill

Protect the PostgreSQL dump and both signing keys. Ticket tokens cannot be regenerated from a database-only backup after losing TICKET_SIGNING_KEY. Include media/static configuration, migration revision and encrypted secret references in deployment recovery records.

```sh
mkdir -p private-backups
docker compose exec -T postgres pg_dump -U ticket -Fc ticket > private-backups/ticket.dump
# Restore into a disposable database, never overwrite the running one:
docker compose exec postgres createdb -U ticket ticket_restore_check
docker compose exec -T postgres pg_restore -U ticket -d ticket_restore_check < private-backups/ticket.dump
```

Check order/ticket/audit counts, migrations and reconciliation against the restored database using isolated environment variables. Test login and authorized QR derivation with the restored key, then record duration and outcomes. Validate encrypted backup retention and restore regularly. Do not commit dumps. No destructive restore target or unattended production cleanup is supplied.

## Deployment example and rollback

Build locked backend dependencies and a production static web bundle. Serve web assets through an HTTPS reverse proxy/CDN, proxy `/api` and `/ws` to ASGI, set correct forwarding headers only from that trusted proxy, and use a restricted managed PostgreSQL/Redis network. Set DEBUG=False, long independent signing keys, exact hosts/origins, SMTP credentials, HTTPS APP_BASE_URL and environment-appropriate throttles. Keep Stripe TEST-only in this release. Run `manage.py check --deploy`, explicit migrations and `collectstatic`; restrict Django admin, use separately provisioned staff accounts and take a backup before schema changes.

Scale ASGI/workers based on measured latency, event-lock wait time, DB connection budgets and outbox lag. Alert on provider failures, compensation backlog, dead letters, reconciliation mismatch and rejected-scan spikes. Configure production reverse-proxy timeouts/connection limits, structured request IDs, log redaction, process resource limits and backup access. There is no included production hosting deployment.

Rollback application code only when the previous code supports the current schema. Prefer forward fixes for additive migrations. If restore is required, close sales/admission, stop workers, reconcile provider test state and restore into a new database before switching traffic; do not duplicate payment attempts under new IDs. Test this procedure before public use. A public deployment still requires review of the documented mobile advisories and physical-device integration checks.
