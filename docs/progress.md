# Current progress

The repository now contains a functional synthetic ticketing application, replacing the original empty domain scaffold. Current backend/client tests and known integration limits are in `testing/README.md`. All previous scaffold-only notes in `repository-audit.md` are historical findings.

Implemented: accounts/tenants, venues/events, GA/assigned/mixed holds, integer order/promotions, mock and optional Stripe TEST, compensation/refunds, private QR/PDF, assigned gate, notifications/outbox/realtime, metrics/CSV/audit/moderation, web and Expo interfaces, guarded seed and documentation. No live payment or public hosting was used.

Verified locally: 58 backend tests on PostgreSQL, 84% overall branch-enabled coverage and 90% combined critical service coverage; Ruff; eleven-file mypy domain check; three web tests and production build; three native component tests, Expo web export and Android Hermes bundle export; web and Python dependency audits clean, native advisory review printed four upstream advisories.

Final local validation passed: fresh Compose build, automatic migration, synthetic seed and healthy API/PostgreSQL/Redis/Mailpit; all three Playwright journeys passed against the Docker stack. Four separate-connection race tests passed in three repeated runs (25.37s, 25.37s, 29.17s). Fresh npm ci passed for web, mobile and API generator; schema/type regeneration matched. A PostgreSQL dump restored into a separate database preserved 3 orders, 9 tickets and 18 audit records with zero inventory mismatches. GitHub CI/main integration is the remaining delivery step.

Outstanding production-release gates: physical device camera/SecureStore/PDF-sharing checklist and optional external Stripe TEST integration, fixes for upstream mobile advisories, public HTTPS deployment/security review. The runnable app can be delivered without pretending those checks happened. Do not tag v1.0.0 as a fully accepted production release while they remain open.
