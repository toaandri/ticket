# Changelog

## Unreleased — functional portfolio application

- Guarded web/mobile sessions against late refresh/login responses and old-account data after logout or account switching; serialized native refresh persistence and kept temporary outages retryable.
- Made the mobile dependency audit runnable on Windows and explicitly online, with incomplete reports rejected.
- Replaced the scaffold with account/tenant, venue/event, PostgreSQL inventory, order/promotion, mock/optional Stripe TEST payment, ticket and gate services.
- Added durable notifications, cancellation/refunds, metrics, audit protection and explicit moderation.
- Built responsive attendee/organizer web and dedicated Expo attendee/wallet/scanner interfaces sharing OpenAPI types.
- Added migrations, locked dependencies, repeat race tests, real API browser journeys, Docker startup and operational/security documentation.
- Current external Stripe TEST and physical-device acceptance checks are documented separately. No production certification or final v1.0.0 tag is claimed while those release gates remain open.
