# Contributing

Use Python 3.12, Node 24 and PostgreSQL 16. Follow the README quick start. Keep money in integer minor units and preserve lock ordering, immutable snapshots, tenant scoping and replay fingerprints. Do not introduce card fields, live keys or offline admission.

Submit a focused PR with the concrete behavior change, migration implications and actual test commands/results. Run backend tests on PostgreSQL, Ruff, relevant app type/tests and schema regeneration. Race changes require repeated separate-connection concurrency tests. CI failures block merging. Keep generated OpenAPI/types together and use committed lockfiles with `npm ci`.

Do not commit `.env`, tokens, databases, generated build/cache directories or personal data. Add screenshots only from synthetic fixtures and mask admission QR codes. New dependency advisories require review rather than broad audit suppression. Test credentials are synthetic development fixtures and must never become deployed defaults.
