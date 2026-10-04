# Security review and privacy

This is a synthetic portfolio demo. No production payment/compliance claim is made. Keep DEBUG and the dev server off public production infrastructure. Django requires strong signing keys outside development. Keep JWT/password-reset signing and ticket signing keys separate, secret and backed up. Configure HTTPS, exact ALLOWED_HOSTS and origins, a trusted reverse proxy and restricted DB/Redis access before any public deployment.

## Threat model

| Threat | Implemented defense | Evidence / limit |
| --- | --- | --- |
| Tenant ID guessing / platform privilege leakage | Scope lookups before disclosure; explicit service role checks | Cross-org, finance/scanner and superuser isolation tests |
| Overselling / double checkout | Ordered row locks, unique claims, capacity checks, fingerprints | Separate PostgreSQL connection races and replay tests |
| Forged, replayed or late payment | HMAC timestamp/signature, TEST-only linkage, immutable amount, inbox digest | Signed fixtures, mismatch rollback, repeated issuance and compensation tests |
| QR guessing or foreign-event use | 256-bit purpose-separated HMAC, stored hash only, assigned-scanner checks | Token tests, owner-only downloads, invalid/foreign/duplicate gate tests |
| Multiple admission / refund replay | Ticket row locks, one accepted scan constraint, refund idempotency | Two-scanner race and exact partial allocation tests |
| Secret leakage in browser/storage/logs | In-memory web tokens, native SecureStore refresh, redacted outbox/audit | Client tests; device SecureStore acceptance remains manual |
| Spreadsheet execution | Escape leading whitespace/formula characters and controls | CSV tests |
| Email duplication or missed tasks | Transactional outbox, leases, retries, stable Message-ID | Rollback/retry/dedup tests; SMTP still at least once |
| CSRF / CORS / abusive auth | JWT clients, Django session CSRF protection, explicit origin allowlist, scoped throttles | Configuration and API security tests; proxy rate limits required for public exposure |
| Upload / offline gate abuse | No upload or offline admission endpoint | These features are disabled |

Organization finance reports omit holder QR tokens; wallet endpoints require the holder. Rejected foreign-event scans omit the foreign ticket ID. Do not log authorization headers, webhook bodies, QR URLs or reset/invitation links. SMTP necessarily receives the recipient email and link; production email needs an appropriate retention/access policy. No universal admin credentials are seeded.

## Upstream mobile advisories, reviewed 2026-10-04

`npm audit --omit=dev` reports four underlying advisories, propagated through 57 package findings in the Expo dependency tree. Current registry latest releases still contain these dependencies; downgrade suggestions from npm are not SDK-compatible fixes.

- GHSA-vfj7-8cjw-p6xm: braces nested-pattern stack exhaustion. Mostly Metro/Jest/CLI file-pattern tooling; do not build attacker-supplied projects or expose Metro publicly.
- GHSA-86w9-cpqp-85rv: node-forge RSA signature verification. Expo development code-signing tooling; Ticket does not use node-forge for payment or admission verification. Keep development tooling on a trusted network.
- GHSA-vcc3-ghjq-m6fr: malformed percent-encoding decode denial of service through Expo Router/query-string. This can affect app navigation; treat untrusted deep links as a residual availability risk. Do not publish a production native release before an upstream fix and link-fuzzing validation.
- GHSA-w5hq-g745-h8pq: uuid buffer bounds. Transitive build/config utilities use older UUID packages; Ticket request keys use browser crypto or expo-crypto. Review callers again before a build tool update.

Exact exceptions and review expiry are in `mobile-advisories.json`. CI prints every advisory, rejects new advisory IDs and fails after the review deadline. Exceptions are not proof that affected packages are safe. Web production dependency audit reports no findings at the recorded revision. Python audit results are recorded in testing/progress when verified.

## Privacy and retention

Synthetic data only in demo fixtures. Orders, money, audit and scan history are retained for traceability; no automatic financial purge exists. A production retention policy must specify legal periods, privacy access/export handling, account anonymization and encrypted backup lifecycle. Operational logs should contain request IDs and aggregate IDs rather than PII. Protect backups, SMTP inboxes and screenshots; documentation screenshots mask live QR areas. No personal production user data was used to validate the project.
