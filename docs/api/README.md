# API contract

Base path `/api/v1/`. OpenAPI is available at `/api/schema/`, with Swagger at `/api/schema/swagger-ui/`. The committed schema and generated TypeScript types live in `packages/api-client/generated/`. Regenerate both with `make schema`; CI checks drift. Paginated resources return `{count,next,previous,results}`. Dates use ISO 8601 UTC plus an IANA display timezone; amounts use integer minor units.

## Authentication

```sh
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo-attendee@ticket.example","password":"YOUR_GENERATED_DEMO_PASSWORD"}'
# Subsequent calls: Authorization: Bearer ACCESS_TOKEN
```

Register/login return access and refresh tokens; refresh rotates both. Logout revokes the current user's refresh token. Password reset uses email-bound signed tokens and invalidates existing sessions. `GET/PATCH /me/` exposes only editable profile fields and readonly role flags. Verify email before holding tickets or accepting team invitations. Authorization is enforced server-side, regardless of hidden client buttons.

## Hold, checkout and payment

```http
POST /api/v1/reservations/
Authorization: Bearer ACCESS_TOKEN
Idempotency-Key: YOUR_UUID
Content-Type: application/json

{"event_id":"EVENT_UUID","items":[{"ticket_type_id":"TYPE_UUID","quantity":2}]}
```

For numbered seating use quantity 1 and `event_seat_id`, selected from `/events/EVENT_UUID/availability/`. A mixed basket may combine both. The response includes the server's `expires_at`. `POST /reservations/HOLD_UUID/cancel/` releases an unpaid hold idempotently.

```http
POST /api/v1/orders/
Idempotency-Key: ANOTHER_UUID

{"reservation_id":"HOLD_UUID","promotion_code":"DEMO10"}

POST /api/v1/orders/ORDER_UUID/payments/
Idempotency-Key: PAYMENT_UUID

{"provider":"MOCK","scenario":"success"}
```

Retry an uncertain request with the same key and payload. A changed payload under that key returns 409. Never invent a fresh key just because the response was lost. Checkout does not extend a hold. Only PAID orders produce tickets; pending, failed, expired and late successful payments do not grant admission. Stripe's checkout URL is TEST-only and optional. Fetch `/orders/ORDER_UUID/` after returning from hosted checkout.

## Capability map

| Routes | Capability |
| --- | --- |
| `/events/`, `/events/:id/availability/` | Public published inventory; member-scoped drafts |
| `/events/:id/publish/`, `/ticket-types/`, venue/layout routes | Owner, Manager, Editor |
| `/organizations/:id/invitations/`, membership role changes, `/events/:id/staff/` | Owner/Manager, with owner escalation protection |
| `/orders/`, `/tickets/`, `/tickets/:id/qr/`, `/pdf/` | Own account only; private no-store binary downloads |
| `/organizations/:id/orders/`, `/tickets/`, event `/metrics/`, `/export/` | Owner/Manager/Finance; ticket report omits QR secrets |
| `/orders/:id/refunds/`, event `/cancel/` | Owner/Manager, scoped and policy checked |
| `/staff/events/`, `/check-ins/` | Owner/Manager, or Scanner assigned to that event |
| `/notifications/`, `/notifications/:id/read/` | Own account |
| `/admin/audit/`, `/admin/outbox/`, `/admin/.../moderate/` | Platform superuser, explicit separate actions |
| `/payments/stripe/webhook/` | Signed Stripe TEST events; no JWT |

```http
POST /api/v1/check-ins/
Idempotency-Key: SCAN_UUID

{"event_id":"EVENT_UUID","token":"OPAQUE_QR_TOKEN_OR_URL","device_id":"gate-1"}
```

201 ACCEPTED grants admission. A 409 gate response has the typed CheckIn body with INVALID, WRONG_EVENT, CLOSED, REVOKED or DUPLICATE. Other errors use `{code,message,details,request_id}`. The typed gate response is the documented exception to the uniform error envelope. A network timeout or offline state never grants admission. Check-in opens two hours before the event and closes at its end.

Refund requests include exact `ticket_ids` and a reason, plus an idempotency key. Only unused eligible tickets are selected, with server-computed allocated amounts; clients cannot specify the money value. Reports and exports never accept a foreign organization's UUID as authority.
