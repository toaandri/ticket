# Role matrix

A user may own tickets while holding any team role. Holder access and organization access are separate. Lookups scope private objects by the actual membership before UUID disclosure.

| Organization operation | Owner | Manager | Editor | Finance | Scanner |
| --- | --- | --- | --- | --- | --- |
| Read own organization/events | Yes | Yes | Yes | Yes | Yes |
| Create/edit venue/layout/draft/ticket type, publish | Yes | Yes | Yes | No | No |
| Create/change promotion | Yes | Yes | Yes | No | No |
| Invite/edit roles below Manager | Yes | Yes | No | No | No |
| Invite/promote Manager | Yes | No | No | No | No |
| Demote Owner / grant Owner | No | No | No | No | No |
| Assign gate scanners | Yes | Yes | No | No | No |
| Orders, ticket reports, metrics, CSV | Yes | Yes | No | Yes | No |
| Refund unused tickets / cancel event | Yes | Yes | No | No | No |
| Organization audit | Yes | Yes | No | No | No |
| Gate admission | Yes | Yes | No | No | Assigned events only |

Any authenticated account can create an organization and receives its owner membership atomically. Accepting an invitation requires verified matching email, an unexpired token and still-valid inviter authority. Only hashes are persisted; raw invitation links go through email. Profile edits cannot promote accounts.

Wallet/orders/QR/PDF endpoints grant only the actual attendee's records. Finance ticket reports contain allocation/status/seat details but no admission secret. Scanner cannot read finance, other tenants or unassigned gate inventory. Rejected foreign-event gate responses omit foreign ticket IDs.

Platform superusers use explicit admin moderation/outbox/audit endpoints. They gain no automatic tenant membership or wallet access. Financial/audit invariants are protected by model/queryset guards and PostgreSQL triggers; database superusers remain capable of deliberate administrative override. Production DB permissions must separate runtime access from migration/maintenance access.
