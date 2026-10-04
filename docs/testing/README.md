# Verification

## Recorded local results (2026-10-04)

- Python 3.12.14 / Django 5.2.17 / PostgreSQL 16.15 / Redis 7.0.15: 58 backend tests passed. Overall statement/branch coverage baseline 84%; combined checkout, hold, payment, ticket and gate service coverage 90%. Coverage reports distinguish untested provider/network paths; the target is not a claim that every service branch is covered.
- Ruff lint and format pass. Mypy checks the eleven domain model/provider contract files; TypeScript checks both clients.
- Web: three Vitest account/discovery tests passed and Vite production build succeeded.
- Mobile: three component/session tests passed, Expo web export and Android Hermes bundle export succeeded. Expo web discovery and authenticated wallet/QR also passed against the real API. These do not replace physical camera/SecureStore testing.
- npm production dependency audit: web zero findings; mobile four underlying upstream advisories, documented with expiring exceptions in the security review. Python requirements audit reported no known vulnerabilities.

All three real API Playwright journeys passed against the freshly migrated/seeded Compose stack (10.6s). Four race tests passed in each of three repetitions (25.37s, 25.37s, 29.17s). Restore into a separate PostgreSQL database preserved 3 orders/9 tickets/18 audit rows and reconciled with zero mismatches. Screenshots come from running synthetic apps and mask admission QR areas.

The same three browser journeys passed again (12.5s) against an independent GitHub clone with fresh Compose volumes and generated signing keys. All runtime services started, migrations exited successfully and the API health endpoint returned 200. Eight synthetic messages reached Mailpit through the worker. This managed shell uses umask 077; tracked public source permissions were normalized to the usual 644/755 clone modes for non-root bind mounts, while `.env` remained 600.

## Test matrix

| Area | Checks |
| --- | --- |
| Accounts | Password/email validation, case-insensitive DB uniqueness, refresh rotation, logout ownership, reset invalidation, disabled user, readonly privilege flags |
| Tenants | Owner creation, role checks, verified email-bound invitation replay, cross-org lookup, owner escalation protection, explicit superuser moderation |
| Layout / holds | Publication freeze, invalid configuration, mixed seating, immutable prices, wrong seat, expiry/release once, capacity/claim constraints |
| Orders / money | Payload fingerprint mismatch, duplicate concurrent checkout, integer promotion allocation/limits, immutable DB snapshots |
| Payments / refunds | Duplicate concurrent payment, ten-event replay, amount/currency rollback, decline, late compensation, partial refund allocation, provider outage/recovery, signed TEST webhook fixtures |
| Gate / wallet | Private PDF/PNG access; hashed admission credentials; invalid, revoked, closed and foreign scans; assigned role and two-scanner acceptance race |
| Operations | Reconciliation flags without repair, cancellation retries, SMTP outage/dedup, outbox rollback, post-commit hints, CSV formula escaping, timezone grouping, admin isolation, guarded/idempotent seed |
| Clients | Memory-token web login/retry, native SecureStore adapter/rotated restoration, staff endpoint scope; real browser hold, payment, wallet, report, selected refund and invalid gate journey |

## Concurrency reproduction

```sh
make concurrency-test
# Repeat against PostgreSQL, using separate DB connections:
cd backend
for attempt in 1 2 3; do
  pytest tests/test_inventory.py tests/test_checkout.py -k 'race or concurrent or scanners' --tb=short -x
done
```

The seat race synchronizes competing buyers; the GA test runs 100 buyer attempts against capacity 20 in simultaneous batches. Tests assert one exclusive claim, at most twenty held/sold admissions and no negative counts. Two scanners race a valid ticket and assert one ACCEPTED. Checkout/payment replay also uses simultaneous separate connections. Django transaction-wrapped TestCase alone is not treated as concurrency evidence. Use a disposable database; pytest's transactional fixtures clear their test state.

## Browser E2E

`web/e2e/journeys.spec.ts` drives the running API with Playwright Chromium. Create a fresh synthetic seed with the documented E2E password, start API/Vite, then run `npx playwright test` from `web`. It covers responsive 390px discovery with no horizontal overflow, an accessible numbered seat hold/release, GA mock checkout and authorized wallet QR, reports/selected partial refund, and assigned scanner INVALID result. CI archives traces/screenshots on failure. Do not suppress failed assertions with retries or generic sleeps.

## Manual native device checklist (not yet hardware-verified)

1. Start Expo with the LAN API URL; confirm web/phone see the same event IDs.
2. Login as attendee, kill/reopen the app and confirm SecureStore rotates refresh rather than storing access/password. Logout and confirm wallet/cache clear.
3. Buy GA and an exact accessible seat in MOCK success mode; confirm the same order/ticket appears on web. Check decline, pending and expiration display after background/resume.
4. Display private QR and share PDF through OS UI; ensure temporary downloaded files are removed. Confirm a foreign account cannot load the same URLs.
5. Login as assigned scanner, grant camera permission and scan one synthetic ticket within the check-in window; two devices must produce ACCEPTED then DUPLICATE.
6. Deny camera permission and use manual token entry. Disconnect the network and verify no offline admission is granted; reconnect and rescan.
7. Exercise test hosted checkout return/cancel and verify server-confirmed status, never trust deep-link query parameters. Fuzz malformed links before a production native release.

Record device/OS/Expo version, commands, timestamps and outcomes. Android bundle compilation and Expo web screenshots are expressly not evidence of these hardware checks. External Stripe TEST integration requires optional credentials and has not been represented as a live verified connection.
