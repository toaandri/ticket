# Current progress

## Latest continuation — 2026-10-08, advanced interface and delivery

The user's requested first push was completed as `6c61493` on `main`, preserving the existing functional implementation and adding the session race fixes. Its GitHub run passed all functional/schema/secret jobs but failed dependency review on the newly reported sprintf-js advisory. The new delivery removes that chain rather than widening the advisory baseline.

Implemented the editorial responsive interface, original poster/ticket artwork, light/dark tokens, optional decorative motion and OS reduced-motion support, browser shortlist, URL filters/order, grid/list layouts, native dialog quick search and guided seat/hold/checkout flow. Added actual daily-sales charts, organization-switch cleanup, mobile posters/pull-to-refresh/press feedback, account/event-isolated native checkout state and account-isolated scanner state. Pending order polling stops after a terminal outcome. Unexpected API exceptions now mark atomic request writes for rollback. Environment setup works directly in PowerShell and preserves existing signing keys.

Verification for this continuation: 59 real PostgreSQL backend tests; four repeated separate-connection race tests; 18 web tests; six mobile tests plus an actual YAML-loader compatibility check; backend Ruff/format/migration/mypy and matching OpenAPI fingerprints; web production build and Android/Web exports. All six real API browser journeys passed (44.3s), including pending/declined payment outcomes, refunds, assigned gate access, shortlist/keyboard navigation and responsive/reduced-motion checks. Web/Python production audits are clean; mobile reports only the four existing upstream advisory IDs, with unchanged exceptions/deadline. README and real synthetic screenshots have been refreshed. Detailed commands/results are in `testing/README.md`.

Delivery targets `main` with normal fast-forward pushes, no release tag or public deployment. Physical-device and optional external Stripe TEST validation, upstream mobile fixes and production HTTPS/security review remain release gates, not completed checks. The earlier continuation notes below retain their historical local-only status; the first push above supersedes that status. Final commit and CI result are reported with delivery, not assumed here.

The repository now contains a functional synthetic ticketing application, replacing the original empty domain scaffold. Current backend/client tests and known integration limits are in `testing/README.md`. All previous scaffold-only notes in `repository-audit.md` are historical findings.

Implemented: accounts/tenants, venues/events, GA/assigned/mixed holds, integer order/promotions, mock and optional Stripe TEST, compensation/refunds, private QR/PDF, assigned gate, notifications/outbox/realtime, metrics/CSV/audit/moderation, web and Expo interfaces, guarded seed and documentation. No live payment or public hosting was used.

Verified locally: 58 backend tests on PostgreSQL, 84% overall branch-enabled coverage and 90% combined critical service coverage; Ruff; eleven-file mypy domain check; three web tests and production build; three native component tests, Expo web export and Android Hermes bundle export; web and Python dependency audits clean, native advisory review printed four upstream advisories.

Final local validation passed: fresh Compose build, automatic migration, synthetic seed and healthy API/PostgreSQL/Redis/Mailpit; all three Playwright journeys passed against the Docker stack. Four separate-connection race tests passed in three repeated runs (25.37s, 25.37s, 29.17s). Fresh npm ci passed for web, mobile and API generator; schema/type regeneration matched. A PostgreSQL dump restored into a separate database preserved 3 orders, 9 tickets and 18 audit records with zero inventory mismatches. An independent GitHub clone also built, migrated and seeded with fresh volumes/signing keys; its API and database services were healthy and all three browser journeys passed (12.5s). The worker delivered eight synthetic emails into Mailpit with no failed or pending outbox entries on the first stack. GitHub Actions passed the backend, web, mobile, schema, dependency-review and browser jobs. CI keeps the history secret scan blocking; its single prose-only historical finding has an exact documented fingerprint exception. Temporary dependency-provisioning workflows have been removed. Delivery targets the main branch.

Outstanding production-release gates: physical device camera/SecureStore/PDF-sharing checklist and optional external Stripe TEST integration, fixes for upstream mobile advisories, public HTTPS deployment/security review. The runnable app can be delivered without pretending those checks happened. Do not tag v1.0.0 as a fully accepted production release while they remain open.

## Continuation — 2026-10-05, Windows workspace

Read the progress/delivery/security logs on `origin/codex/repair-scaffold`, which points to the same commit as `origin/main` (`8fd74ba`). Fast-forwarded the clean local `main` from `b7907a2` through the fifteen existing commits before continuing. The scaffold notes in the original master specification are historical; implementation is already present on the remote branches.

Reproduced two client session failures with regression tests before changing implementation: a late refresh reinstalled credentials after logout, and an old refresh rejection cleared a newly signed-in account. Added shared session generation and serialized refresh-storage handling used by both clients. Old responses cannot install tokens or return earlier-account data; logout clears local profile/cache immediately, shares any pending rotation for remote revocation and does not persist its returned credentials. Transient refresh transport errors remain retryable. Native Jest/Metro now resolve Babel helpers used by the shared package through the mobile dependency tree.

Verification actually run in this workspace:

- `npm ci --no-audit --no-fund` in web/mobile: both passed against the existing lockfiles. Node was 24.13.0; npm warned that some web test dependencies declare a minimum of 24.15.0. Use a supported Node version on fresh setups.
- Web `npm test -- --run`: 13 passed, including five shared credential/storage tests and five session regression tests.
- Mobile `npm test -- --watch=false`: 6 passed, including three new session regression tests.
- Web/mobile `npm run lint` and `npm run typecheck`: passed.
- Web `npm run build`: passed.
- Mobile `node node_modules/expo/bin/cli export --platform android --output-dir dist/android`: passed; 1,338 modules bundled into an Android Hermes artifact. This is compilation evidence, not a device acceptance test.
- `python infra/scripts/audit_mobile.py`: passed with network access, reporting all four existing advisory IDs. Fixed Windows `npm.cmd` discovery, forced online audit and rejected incomplete reports. Exceptions were not widened and vulnerable dependencies were not represented as fixed.

Backend, PostgreSQL races, Docker/browser journeys and device tests were not rerun for this client-only continuation. Their earlier results remain historical evidence. Changes from this continuation are local; no push, release tag or deployment was performed. Next work: review upstream advisory fixes and fuzz native links; then perform the documented device checklist with hardware and optional Stripe TEST checks with credentials.
