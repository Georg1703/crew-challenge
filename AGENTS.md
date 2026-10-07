# AGENTS.md - Crew Challenges

A PWA for any small group (a **crew**: a family, friends, a team) that sets shared challenges
(monthly, weekly or daily) and checks in every day with proof (photo or video). The first crew is
the owner's family.

Read this file before changing anything. Then read the nested `AGENTS.md` of the area you touch.

## First version (v1) scope
v1 ships five things: inviting members, flexible challenge creation, the daily check-in (you and
your crew), proof upload (photo or video), and simple reactions on the crew's journal (one emoji
per person). Everything below marked **after v1** stays in the docs as the long-term direction but
must not be built yet: growing trees and the garden, streak flames as artwork, the Wheel of Doom,
confetti and Rive animations, custom reaction sets and reaction notifications, and Web Push.
If a task seems to need one of these, stop and ask.

- How the system is built, and why: `docs/architecture/`
- Words we use: `docs/glossary.md`
- How to make common changes: `docs/recipes/`
- How the UI is built and kept consistent: `docs/design-system.md`

## How to work in this repo
1. Read this file, then `backend/AGENTS.md`, `frontend/AGENTS.md` or `infra/AGENTS.md` as needed.
2. Do what the task asks and nothing more. Mention anything else you notice in your final summary
   instead of doing it.
3. Follow the matching recipe in `docs/recipes/` (backend app, endpoint, screen, migration, Celery task).
4. Follow `docs/architecture/`. If a task seems to need a different approach, stop and ask first.
   When an approach changes, update the docs in the same change.
5. Use names from `docs/glossary.md` in code, API fields, and UI keys.
6. When planning, look for what can be generic (a model, an endpoint, a component, a hook) so the
   next feature reuses it, and for what can be simpler. Do it where it pays off now or clearly
   soon, say why in the plan, and do not build for imagined needs.
7. Done means: `make check` passes and the task's acceptance criteria are met.

## Repository map
| Path | What lives there |
|---|---|
| `backend/` | Django project: `config/` settings, `apps/<name>/` domain apps, `integrations/` adapters to AWS/push, `tests/` |
| `frontend/` | React PWA: `src/app/`, `src/api/` (generated client), `src/features/<name>/`, `src/shared/`, `src/pwa/`, `src/i18n/`, `src/styles/` |
| `contracts/openapi.yaml` | Generated API contract. Never edit by hand. |
| `infra/` | `aws/` JSON documents for the hand-made AWS setup, `caddy/`, `scripts/` (deploy, backup, host bootstrap) |
| `docs/` | `architecture/`, `recipes/`, `design-system.md`, `glossary.md` |
| `tools/` | Repo helpers: docs checker, seed data, upload smoke test |
| `.claude/` | Agent permissions and slash commands |

## Commands
Always use `make`. Run `make help` to see every target. Never invent commands.

| Command | Purpose |
|---|---|
| `make setup` | First-time setup |
| `make install` | Install backend and frontend dependencies and the git hooks |
| `make dev` / `make stop` / `make ps` | Run everything locally / stop it / show container health |
| `make check` | Everything CI runs. Must pass before a task is done. |
| `make test` / `make test-fast` | All tests / tests for changed apps only |
| `make e2e` | Playwright end-to-end tests against the real backend (needs Postgres and Redis) |
| `make upload-smoke` | Upload test files to the dev S3 bucket like the browser, check, delete (needs `AWS_PROFILE`) |
| `make fmt` | Format all code |
| `make schema` | Regenerate OpenAPI + TypeScript client. Run after any serializer or view change. |
| `make migrate` / `make makemigrations` | Database migrations |
| `make seed` | Demo crew with known users and a challenge running this month |
| `make superuser` | Create a Django admin user (interactive) |
| `make shell` / `make logs` | Django shell / service logs |
| `make tunnel` / `make preview` | HTTPS URL for a phone: dev server / production build (to install) |

## Never
- Create or change AWS resources, SSH into servers, run deploy scripts, or touch production.
  Write the JSON document or the console steps; the owner applies them.
- Read, print, or commit `.env` files or secrets. Use `.env.example` for variable names.
- Edit generated files (`contracts/openapi.yaml`, `frontend/src/api/schema.gen.ts`) by hand.
- Call `boto3` or `pywebpush` outside `backend/integrations/`, or `fetch` outside `frontend/src/api/`.
- Use `timezone.now()` or `date.today()` for business dates; use `apps/core/clock.py`.
- Add a dependency without a one-line reason in the PR description.

## Frontend <-> backend
- One origin: Vite (local) and Caddy (server) serve the SPA and proxy `/api` and `/admin` to Django.
  No CORS for the API.
- Base path `/api/v1/`. snake_case JSON on both sides. UUID ids. ISO 8601 UTC datetimes.
  Crew-local dates as `YYYY-MM-DD`.
- Errors always `{"error": {"code": "...", "message": "...", "fields": {...}}}`.
  The frontend maps `code` to i18n text.
- Session cookie + CSRF: `GET /api/v1/auth/csrf` first, send `X-CSRFToken` on unsafe requests,
  401 -> redirect to `/login`.
- Details: `docs/architecture/api-conventions.md`.

## Environments
- **Local:** `compose.yaml`, Django `runserver` + Vite dev server, Postgres and Redis containers,
  a real S3 dev bucket through the `cc-dev` AWS profile. Tests never call AWS.
- **Production:** one Amazon Lightsail instance running `compose.prod.yaml`: Caddy, gunicorn,
  Celery worker + beat, Redis, Postgres (nightly `pg_dump` to S3). Images from GitHub Container
  Registry; deploys over SSH from GitHub Actions. Media in S3 + CloudFront, transcoding by
  AWS Elemental MediaConvert. The server uses a least-privilege IAM user key stored in its
  root-only `.env`.
- Details: `docs/architecture/environments.md`.

## Stack
- **Backend:** Python 3.13, Django 5.2 LTS, DRF, drf-spectacular, PostgreSQL 17, Redis, Celery +
  django-celery-beat, boto3, pywebpush. Tooling: uv, ruff, mypy + django-stubs, pytest-django,
  factory-boy, time-machine, import-linter.
- **Frontend:** React 19, TypeScript strict, Vite (pnpm), React Router, vite-plugin-pwa (Workbox),
  TanStack Query, openapi-fetch, Zustand, Motion, i18next, hls.js, Uppy core + @uppy/aws-s3 (v5)
  (after v1: @rive-app/react-canvas, canvas-confetti). CSS Modules + tokens in `src/styles/tokens.css`.
- **Media:** private S3 bucket, CloudFront with signed cookies, MediaConvert -> HLS.
- **Emoji:** Emoji Mart (`emoji-mart` + `@emoji-mart/data`, core only, loaded on demand).
- **Auth:** Django session cookie + CSRF. No JWT.

## Architecture rules
- Every Django app has the same layout: `models.py`, `services.py` (writes), `selectors.py` (reads),
  `api/{serializers,views,urls}.py`, `admin.py`, `tasks.py`, `tests/`. Layers are enforced by
  import-linter. See `docs/architecture/backend.md`.
- Business rules live in `services.py`, never in views, serializers or tasks. Views and Celery
  tasks call services. Non-trivial reads go through `selectors.py`.
- Every domain row carries `crew_id`. A user can belong to several crews (through `Member`).
- Rows people delete but we keep (challenges, proofs) inherit `SoftDeleteModel` or
  `CrewScopedSoftDeleteModel`: `objects` hides deleted rows, `delete()` is soft. See
  `docs/recipes/soft-delete.md`.
- Store datetimes in UTC. A "challenge day" is a local date in `Crew.timezone`
  (default `Europe/Chisinau`). Test around midnight and DST switches.
- Scheduled jobs are idempotent (safe to run twice).
- Tree stage and flame tier (after v1) are derived in the API, not stored.

## Game rules that code must respect
- Any member adds proposals to the crew's pool (at most `Crew.max_proposals`, default 50). The crew
  votes (one vote per member per proposal, for as many as they like). A proposal says how long it
  runs (months, weeks or days); a crew admin picks when it starts. Several challenges can run at
  the same time. Votes guide the admin; they do not decide.
- A challenge shows who proposed it and when. Its creator chooses who takes part (the
  participants: one `Participant` row each, the whole crew by default, the creator always) and can
  change the list until it is scheduled. Only participants and crew admins see a challenge; only
  participants vote and take part. People who join the crew later are not added. A proposal can be
  edited by its creator while it is in the pool (editing the challenge resets its votes; removing
  someone deletes only their vote); once scheduled, nothing can be edited. Before the start an
  admin can move it or put it back in the pool (the participants stay as they are). Opting out
  before the start deletes the row; leaving during it sets `left_on` (today still counts). Either
  way the member stops seeing it and cannot come back; the board keeps a leaver's days.
- Plan and details: `docs/plans/monthly-challenges.md`.
- A participant checks in for today only (crew time zone; midnight closes the day). Numbers add up
  during the day. A challenge is judged in windows (a day, a Monday-Sunday week or the whole
  period, `apps/challenges/windows.py`): a window that ended below its need has failed, and a
  failed day window is a missed day. Verdicts are derived on read, not stored. Streaks are per
  challenge.
- Proof (stage 3) attaches to the day's check-in. A proof upload that starts before midnight
  counts if it completes within 24 h after that day's deadline.
- Missed day -> streak reset. After v1: tree wilted and one pending Wheel of Doom spin per missed day.
- After v1: the Wheel of Doom result is chosen on the server before the client animation starts.

## Large uploads (up to 20 GB) - non-negotiable
- Files never go through Django. Browser -> S3 multipart upload with presigned part URLs.
- Part size 16 MiB (< 1 GiB files) or 64 MiB (larger). S3 limits: 5 MiB min part (except last),
  5 GiB max part, 10,000 parts max. Validate size <= 20 GB server-side.
- 4 parallel parts, 6 retries with exponential backoff, auto re-sign expired URLs,
  pause on `offline`, resume on `online`.
- Report each completed part (number + ETag) to the API, which keeps them with the upload. Resume =
  user re-picks the same file, its fingerprint (name + size + lastModified) finds the open upload
  (`GET /api/v1/proofs/resume`), only missing parts are uploaded. No browser storage for this: it
  may be evicted on iOS, and the server already has it.
- The upload manager is a global store outside routes: the user is never blocked from using the
  app while an upload runs. Progress shows in the tab bar.
- Request a Screen Wake Lock during uploads (tolerate rejection). Warn before > 2 GB on phones.
- On complete: CompleteMultipartUpload, HeadObject to verify size, enqueue MediaConvert job.
- S3 CORS allows PUT from the app origin and exposes `ETag`. Lifecycle aborts incomplete
  multipart uploads after 7 days.

## PWA constraints (iOS + Android)
- Android: capture `beforeinstallprompt`, show our own install button.
- iOS: no install prompt. Provide an animated "Share -> Add to Home Screen" guide.
- After v1: iOS push works only when installed to the Home Screen (16.4+) and after a user gesture.
  Ask for push permission after the first check-in, never on first load.
- No background upload, background sync or background fetch on iOS. Uploads pause when the app is
  backgrounded or the screen locks. All timed logic runs on the server and reaches users by Web Push.
- Browser storage may be evicted on iOS: it is a cache; the server is the source of truth.
- Video capture: `<input type="file" accept="video/*" capture>`. Audio: MediaRecorder. Handle both
  MP4/AAC (Safari) and WebM/Opus (Chrome); normalize on the server.
- Service worker: precache app shell and fonts; network-only for `/api` and `/admin`; never
  cache presigned URLs or media uploads.
- Use `100dvh`, respect `env(safe-area-inset-*)`, touch targets >= 44 px.

## UI and motion
- Calm and clear first: every important action gets short feedback (a check mark, a toast,
  a progress change) through the `shared/motion` presets. Big celebrations (tree growth, confetti,
  flame spark, spin, reveal flip) come after v1.
- Every tap responds within 100 ms (optimistic updates with TanStack Query, rollback on error).
- Animate only `transform` and `opacity`; target 60 fps on a mid-range Android phone.
- Lazy-load hls.js (and the Rive runtime after v1); code-split routes; first load < 2 s on 4G.
- Honor `prefers-reduced-motion`. UI sounds only after user interaction and off by default
  (a proof video opened with a tap plays with sound).
- Romanian (default) and English from the start; no hard-coded UI strings.
- The look is defined by the design system in `docs/design-system.md`: tokens, `shared/ui`
  components and motion presets only. Read it before any UI work; `make check` enforces it.

## Testing
- Backend: pytest + pytest-django against Postgres (never SQLite); time-machine for date logic;
  in-memory fakes instead of AWS (the S3 adapter is checked against the real dev bucket by the
  upload smoke test, not in unit tests). `make check` enforces 90% coverage of services,
  selectors, core and integrations.
- Frontend: Vitest + Testing Library in `make check`; Playwright (`make e2e`) for main flows.
- Before calling an upload change done: test a multi-GB upload with a network interruption and a resume.

## Writing style
- Docs, the Makefile, scripts, and code comments use plain ASCII: `-` not em or en dashes,
  `->` not arrows, `|--` and `` `-- `` for directory trees. `make check` enforces this.
  Romanian diacritics are fine in UI translation files (`frontend/src/i18n/`).

## Commits, branches and pull requests
- Branches: `<type>/<short-description>`, e.g. `feat/invite-links`. Never commit to `main`.
- Commits follow Conventional Commits: `<type>(<scope>): <subject>`, e.g.
  `feat(backend): add invite service`. Types: feat, fix, refactor, perf, test, docs, build, ci,
  chore, revert. Scopes (optional): backend, frontend, infra, repo, deps. Lowercase subject, no
  period, at most 72 characters.
- A commit message is that one line only: no body, no trailers (no `Co-Authored-By`, no AI or
  session attribution). Commits are authored by the repo owner's git identity.
- Both are checked by the git hooks (`make install`) and by CI (`tools/git_rules.py`).
- One task per pull request. Fill in `.github/pull_request_template.md`.
