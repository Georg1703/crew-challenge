# API conventions

The contract between the React app and Django. The machine-readable version is
`contracts/openapi.yaml`, generated from the code by `make schema`.

## Transport

- One origin. Locally Vite proxies `/api` and `/admin` to Django; in production Caddy does.
  There is no CORS configuration for the API.
- Base path: `/api/v1/`. A breaking change goes to `/api/v2/` for that resource.
- JSON only. `Content-Type: application/json`.

## Authentication

1. `GET /api/v1/auth/csrf` sets the `csrftoken` cookie.
2. `POST /api/v1/auth/login` with `{username, password}` and header `X-CSRFToken` sets `sessionid`.
3. Every unsafe request (`POST`, `PUT`, `PATCH`, `DELETE`) sends `X-CSRFToken`.
4. A `401` means the session is gone: the client clears its cache and goes to `/login`.

Cookies: `sessionid` is `HttpOnly`, `Secure` in production, `SameSite=Lax`, one-year age.

## Data shapes

| Kind | Format | Example |
|---|---|---|
| Keys | `snake_case` on both sides | `display_name` |
| Ids | UUID strings | `"3f1c..."` |
| Instants | ISO 8601 UTC | `"2026-11-03T21:04:11Z"` |
| Crew-local dates | `YYYY-MM-DD` | `"2026-11-03"` |
| Money / counts | integers | `"goal_target": 2` |
| Enums | lowercase strings | `"status": "uploading"` |

## Lists

Cursor pagination:

```json
{ "results": [ ... ], "next": "cD0yMDI2LTExLTAz..." }
```

Pass `?cursor=<next>` to get the next page. `next` is `null` on the last page.

## Errors

Every error, from any layer, has this shape:

```json
{
  "error": {
    "code": "invite_expired",
    "message": "This invite link has expired. Ask for a new one.",
    "fields": { "password": ["Too short."] }
  }
}
```

| HTTP | When | Typical `code` |
|---|---|---|
| 400 | Input failed validation | `validation_failed` (with `fields`) |
| 401 | Not logged in | `not_authenticated` |
| 403 | Logged in but not allowed | `permission_denied`, `not_proposer` |
| 404 | Not found or not in your crew | `not_found` |
| 409 | Valid request that conflicts with state | `invite_expired`, `already_checked_in` |
| 429 | Rate limited | `throttled` |

`code` values are stable and documented in the endpoint's schema. The frontend translates
`errors.<code>` from i18n and falls back to `message`.

## Endpoint rules

- Every view declares `@extend_schema(request=..., responses=...)` so the contract is exact.
- Resource names are plural nouns (`/invites`); actions on a resource are sub-paths
  (`/invites/{code}/accept`).
- A member only ever sees data from their own crews. Out-of-crew ids return `404`, not `403`.
- Write endpoints return the created or updated resource.

## Milestone 1 endpoints

```
GET    /api/health                       liveness: database and Redis (not versioned, not in the contract)
GET    /api/v1/auth/csrf
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
GET    /api/v1/me                        user + member + crew
PATCH  /api/v1/me                        display_name, preferred_language
GET    /api/v1/crew                      crew + members ordered by rotation
PATCH  /api/v1/crew/rotation             admin: reorder members
POST   /api/v1/crew/invites              admin: create invite -> code + link
GET    /api/v1/invites/{code}            public: crew name, validity
POST   /api/v1/invites/{code}/accept     public: create user + member, log in
```

## Changing the contract

1. Change serializers or views.
2. Run `make schema` - writes `contracts/openapi.yaml` and `frontend/src/api/schema.gen.ts`.
3. Fix TypeScript errors in the frontend.
4. Commit all three together. CI fails if the generated files are out of date.
