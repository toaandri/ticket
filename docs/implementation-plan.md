# Delivery plan and acceptance status

The original scaffold and master specification are preserved. Implementation follows the specification's invariants; acceptance claims require actual results.

| Phase | Delivered | Acceptance evidence / remaining gate |
| --- | --- | --- |
| 0–1: runtime, accounts, tenants | Locked stack, custom user, JWT, roles, invitations, audit | Migration/auth/tenant tests; fresh Compose recorded in progress |
| 2–3: events, seats, holds | GA/assigned/mixed, frozen numbered layout, atomic holds/expiry | PostgreSQL claim/capacity races and replay tests |
| 4–5: checkout/mock | Immutable prices, promotions, payment, compensation/refunds | Money/replay/race/outage and late-success tests |
| 6: optional Stripe TEST | Hosted checkout, HMAC inbox, reconciliation, refunds | Signed/provider fixtures pass; external TEST account integration remains optional/unverified |
| 7: wallet/gate | HMAC QR, authorized PDF/PNG, atomic assigned scanning | Private access and two-scanner tests |
| 8–9: web | Editorial light/dark UI, optional motion, shortlist, keyboard search, URL filters, guided checkout, wallet and sales charts | 18 unit tests and six real-API browser journeys; 320–1440px and reduced-motion checks |
| 10: mobile | Expo discover/account/checkout/wallet/camera/manual scanner, native posters, motion and pull-to-refresh | Type/component/Android/Web checks and scoped YAML override regression; physical-device checklist remains open |
| 11–12: operations | Outbox, reminders, hints, metrics, audit/admin | Retry/rollback/CSV/metrics/moderation tests |
| 13: hardening | DB guards, role isolation, locked diagnostic, dependency review | Coverage/race/security checks; upstream native dependency fixes still open |
| 14: portfolio delivery | Documentation, real synthetic screenshots, CI and main integration | Final head/CI recorded in progress; no final v1.0.0 tag while hardware/security release gates remain open |

Decisions: coarse Event serialization; purpose-separated persistent QR key; in-memory browser JWT; SecureStore native refresh; integer exact pricing; no offline admission/transfer/uploads; Stripe TEST only; at-least-once SMTP. See ADRs and security/runbooks for implications.

Next production-release gates: physical device camera/storage/share checks, upstream mobile advisory fixes and link-fuzzing validation, optional real Stripe TEST flow, HTTPS deployment/backup drill and independent security review. These are distinct from completing the runnable synthetic application and pushing its code.
