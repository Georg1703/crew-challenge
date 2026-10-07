# API conventions

The contract between the React app and Django. The machine-readable version is
`contracts/openapi.yaml`, generated from the code by `make schema`.

## Transport

- One origin. Locally Vite proxies `/api` and `/admin` to Django; in production Caddy does.
  There is no CORS configuration for the API.
- Base path: `/api/v1/`. A breaking change goes to `/api/v2/` for that resource.
- JSON only. `Content-Type: application/json`.

## Authentication

1. `GET /api/v1/auth/csrf` sets the `crew_csrftoken` cookie (and returns the token).
2. `POST /api/v1/auth/login` with `{username, password}` and header `X-CSRFToken` sets
   `crew_session` and answers `204`. Then `GET /api/v1/me` loads the user.
3. Every unsafe request (`POST`, `PUT`, `PATCH`, `DELETE`) sends `X-CSRFToken`, logged in or not.
   Without it the answer is `403 csrf_failed`. Django rotates the token on login, so re-read the
   `crew_csrftoken` cookie after logging in.
4. A `401` means the session is gone: the client clears its cache and goes to `/login`.

Cookies: `crew_session` is `HttpOnly`, `Secure` in production, `SameSite=Lax`, one-year age.
Both cookies have names of their own, not Django's defaults: cookies are shared by every port of
a host, so another Django app on localhost would otherwise overwrite them and log people out.
Usernames are case-insensitive (stored in lowercase).

Rate limits per client IP: login 5/minute, joining a crew 10/minute, looking up an invite
30/minute (`429 throttled`). Local settings use looser limits so `make e2e` can log in many times.

**Active crew.** A user can belong to several crews. Crew endpoints act in the session's active
crew (set when joining), falling back to the user's oldest membership.

## Data shapes

| Kind | Format | Example |
|---|---|---|
| Keys | `snake_case` on both sides | `display_name` |
| Ids | UUID strings | `"3f1c..."` |
| Instants | ISO 8601 UTC | `"2026-11-03T21:04:11Z"` |
| Crew-local dates | `YYYY-MM-DD` | `"2026-11-03"` |
| Money / counts | integers | `"vote_count": 3` |
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
| 400 | Input failed validation | `validation_failed`, `username_taken`, `display_name_taken`, `invalid_emoji`, `period_too_far` (with `fields`); `invalid_credentials` |
| 401 | Not logged in | `not_authenticated` |
| 403 | Not allowed | `csrf_failed`, `not_crew_member`, `not_crew_admin`, `not_a_participant`, `not_taking_part`, `not_your_proposal`, `permission_denied` |
| 404 | Not found or not in your crew | `not_found`, `challenge_not_found`, `crew_not_found`, `member_not_found`, `invite_not_found`, `proof_not_found`, `target_not_found`, `upload_not_found` |
| 409 | Valid request that conflicts with state | `invite_expired`, `invite_used`, `already_member`, `already_signed_in`, `pool_full`, `not_a_proposal`, `not_chosen_yet`, `challenge_started`, `challenge_finished`, `period_over`, `too_few_days`, `day_closed`, `not_due_today`, `nothing_to_undo`, `not_checked_in`, `too_many_proofs`, `upload_closed`, `upload_incomplete`, `upload_size_mismatch` |
| 429 | Rate limited | `throttled` |
| 500 | Unexpected error on the server (details are only in the logs) | `server_error` |

Unknown `/api/` URLs return `404 not_found` and crashes return `500 server_error` in the same
shape (Django's own HTML pages are used only outside `/api/`).

`code` values are stable and documented in the endpoint's schema. The frontend translates
`errors.<code>` from i18n and falls back to `message`.

## Endpoint rules

- Every view declares `@extend_schema(request=..., responses=...)` so the contract is exact.
- Resource names are plural nouns (`/invites`); actions on a resource are sub-paths
  (`/invites/{code}/accept`).
- A member only ever sees data from their own crews. Out-of-crew ids return `404`, not `403`.
  The same holds for a challenge the member is not invited to (admins see every challenge).
- Write endpoints return the created or updated resource.

## Endpoints

`contracts/openapi.yaml` is the full reference. Current endpoints:

```
GET    /api/health                      liveness: database and Redis (not versioned, not in the contract)

GET    /api/v1/auth/csrf                sets the crew_csrftoken cookie
POST   /api/v1/auth/login               {username, password} -> 204, session cookie
POST   /api/v1/auth/logout              -> 204

GET    /api/v1/me                       {user, member, crew}; member and crew are null outside a crew
PATCH  /api/v1/me                       {display_name?, preferred_language?} -> me

GET    /api/v1/crew                     the active crew + members in the order they joined
POST   /api/v1/crew/invites             admin: -> 201 {code, url, expires_at} (single use, 7 days)

GET    /api/v1/invites/{code}           public: {crew_name, status: valid|expired|used, expires_at}
POST   /api/v1/invites/{code}/accept    public: {username, password, display_name}
                                        -> 201 me, logged in, a member of the crew

GET    /api/v1/proposals                the pool: proposals (newest first) with votes, size, limit
GET    /api/v1/challenges?phase=...     scheduled challenges: upcoming, active, finished
POST   /api/v1/challenges               propose into the pool, {participant_ids?} -> 201 (409 pool_full)
GET    /api/v1/challenges/{id}          one challenge with participants
PUT    /api/v1/challenges/{id}          creator: replace a proposal (resets its votes)
DELETE /api/v1/challenges/{id}          creator or admin: withdraw a proposal (soft delete)
PUT    /api/v1/challenges/{id}/participants   creator: {participant_ids} (while proposed)
PUT    /api/v1/challenges/{id}/vote     participants: vote for a proposal; DELETE takes it back
PUT    /api/v1/challenges/{id}/schedule   admin: {period_start} (the 1st, a Monday or a day,
                                        by the proposal's period kind): schedule or move before
                                        the start; DELETE puts it back in the pool
DELETE /api/v1/challenges/{id}/participation   opt out (before the start) or leave -> 204;
                                        either way the challenge is gone for the member

GET    /api/v1/today                    my challenges today (state, total, streak, week), the crew
POST   /api/v1/challenges/{id}/check-ins   {day, amount?}: check in for today -> today's card
DELETE /api/v1/challenges/{id}/check-ins/{day}/last   undo today's last entry -> today's card
                                        (the last one takes the day's proofs with it)
GET    /api/v1/challenges/{id}/board?month=YYYY-MM   every participant x every day of the month
GET    /api/v1/challenges/{id}/windows?start=&until=   its weeks, months or whole period: need,
                                        full need, and for a participant done and verdict;
                                        `start` previews a start, `until` previews leaving that day
GET    /api/v1/challenges/{id}/days/{day}   the day sheet: everyone's state, total and shown proofs
GET    /api/v1/feed?cursor=...          the crew's check-ins with proofs, latest activity first
                                        (30 per page, challenges you can see)

POST   /api/v1/challenges/{id}/check-ins/{day}/proofs   {kind, content_type, size, fingerprint?,
                                        thumb_size?}: add proof to today's check-in -> 201
                                        proof + how to upload (one PUT, or multipart parts)
GET    /api/v1/proofs/resume?fingerprint=...   my open video upload for this file, or 404
POST   /api/v1/proofs/{id}/parts        {numbers} -> fresh part URLs
PUT    /api/v1/proofs/{id}/parts/{number}   {etag}: report a finished part -> 204
POST   /api/v1/proofs/{id}/complete     check the file -> the proof (ready); safe to repeat
DELETE /api/v1/proofs/{id}              mine, only on its own day -> 204

POST   /api/v1/media/session            sets the CloudFront cookies for the crew's media
                                        -> {expires_at}; a no-op locally (expires_at null)
```

## Changing the contract

1. Change serializers or views.
2. Run `make schema` - writes `contracts/openapi.yaml` and `frontend/src/api/schema.gen.ts`.
3. Fix TypeScript errors in the frontend.
4. Commit all three together. CI fails if the generated files are out of date.
