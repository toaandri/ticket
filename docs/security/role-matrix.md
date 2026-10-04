# Account and organization authorization

Organization lookup is scoped to the authenticated user's memberships before UUID lookup. Platform superusers have no implicit membership access through organizer endpoints.

| Action | Owner | Manager | Editor / Finance / Scanner |
| --- | --- | --- | --- |
| Read own organization | Yes | Yes | Yes |
| Read an unrelated organization | No | No | No |
| Invite manager | Yes | No | No |
| Invite editor / finance / scanner | Yes | Yes | No |
| Change roles below manager | Yes | Yes | No |
| Promote a member to manager | Yes | No | No |
| Demote owner / grant owner | No | No | No |

Any authenticated user can create an organization and becomes its owner atomically. Accepting invitations requires a verified address matching the invitation. Acceptance is locked and idempotent; inviter permissions are rechecked. Raw invitation secrets are sent by email; only SHA-256 digests are stored. Account recovery invalidates reset tokens after use and revokes old access/refresh tokens.

Audit records enforce append-only semantics in application model/queryset operations. Database administrators can bypass application enforcement; database-level auditing is not claimed.

Event assignment and financial/gate authorization are future work. The present tests do not prove security for unimplemented finance or scanner endpoints.
