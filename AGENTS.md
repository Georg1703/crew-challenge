# AGENTS.md - Crew Challenges

A PWA for any small group (a **crew**: a family, friends, a team) that sets one shared challenge
per month: daily check-ins with proof (often video), a growing tree per member, streak flames,
and a Wheel of Doom for missed days. The first crew is the owner's family.

Read this file before changing anything. Then read the nested `AGENTS.md` of the area you touch.

- Product rules: `docs/product-plan.md`
- Current work: `docs/milestones/` (one work package per session)
- Why things are the way they are: `docs/adr/`
- Words we use: `docs/glossary.md`

## How to work in this repo
1. Read this file, then `backend/AGENTS.md`, `frontend/AGENTS.md` or `infra/AGENTS.md` as needed.
2. Take exactly one work package from `docs/milestones/mN.md`. Stay inside its scope. If you find
   work outside the scope, write it under "Follow-ups" in the milestone file instead of doing it.
3. Follow the matching recipe in `docs/recipes/` (backend app, endpoint, screen, migration, Celery task).
4. Read the relevant ADRs before changing architecture. If you change a decision, add a new ADR
   that supersedes the old one (`docs/recipes/new-adr.md`).
5. Use names from `docs/glossary.md` in code, API fields, and UI keys.
6. Done means: `make check` passes, the package's acceptance criteria are met, and the package is
   ticked in its milestone file with a one-line note of what was done.

## Repository map
| Path | What lives there |
|---|---|
| `backend/` | Django project: `config/` settings, `apps/<name>/` domain apps, `integrations/` adapters to AWS/push, `tests/` |
| `frontend/` | React PWA: `src/app/`, `src/api/` (generated client), `src/features/<name>/`, `src/shared/`, `src/pwa/`, `src/i18n/`, `src/styles/` |
| `contracts/openapi.yaml` | Generated API contract. Never edit by hand. |
| `infra/` | `aws/` JSON documents for the hand-made AWS setup, `caddy/`, `scripts/` (deploy, backup, host bootstrap) |
| `docs/` | `architecture/`, `adr/`, `recipes/`, `runbooks/`, `milestones/`, `glossary.md`, `product-plan.md` |
| `tools/` | Repo helpers: docs checker, seed data, upload smoke test |
| `.claude/` | Agent permissions and slash commands |

## Commands
Always use `make`. Run `make help` to see every target. Never invent commands.

| Command | Purpose |
|---|---|
| `make setup` | First-time setup |
| `make dev` | Run everything locally |
| `make check` | Everything CI runs. Must pass before a package is done. |
| `make test` / `make test-fast` | All tests / tests for changed apps only |
| `make fmt` | Format all code |
| `make schema` | Regenerate OpenAPI + TypeScript client. Run after any serializer or view change. |
| `make migrate` / `make makemigrations` | Database migrations |
| `make seed` | Demo crew with known users |
| `make shell` / `make logs` / `make tunnel` | Django shell / service logs / HTTPS tunnel for phone testing |

## Never
- Create or change AWS resources, SSH into servers, run deploy scripts, or touch production.
  Write the runbook step or JSON document; the owner applies it.
- Read, print, or commit `.env` files or secrets. Use `.env.example` for variable names.
- Edit generated files (`contracts/openapi.yaml`, `frontend/src/api/schema.gen.ts`) by hand.
- Call `boto3` or `pywebpush` outside `backend/integrations/`, or `fetch` outside `frontend/src/api/`.
- Use `timezone.now()` or `date.today()` for business dates; use `apps/core/clock.py`.
- Add a dependency without a one-line reason in the PR description.

## Frontend ↔ backend
- One origin: Vite (local) and Caddy (server) serve the SPA and proxy `/api` and `/admin` to Django.
  No CORS for the API.
- Base path `/api/v1/`. snake_case JSON on both sides. UUID ids. ISO 8601 UTC datetimes.
  Crew-local dates as `YYYY-MM-DD`.
- Errors always `{"error": {"code": "...", "message": "...", "fields": {...}}}`.
  The frontend maps `code` to i18n text.
- Session cookie + CSRF: `GET /api/v1/auth/csrf` first, send `X-CSRFToken` on unsafe requests,
  401 → redirect to `/login`.
- Details: `docs/architecture/api-conventions.md`.

## Environments
- **Local:** `compose.yaml`, Django `runserver` + Vite dev server, Postgres and Redis containers,
  a real S3 dev bucket through the `cc-dev` AWS profile. Tests use moto, never real AWS.
- **Production:** one Amazon Lightsail instance running `compose.prod.yaml`: Caddy, gunicorn,
  Celery worker + beat, Redis, Postgres (nightly `pg_dump` to S3). Images from GitHub Container
  Registry; deploys over SSH from GitHub Actions. Media in S3 + CloudFront, transcoding by
  AWS Elemental MediaConvert. The server uses a least-privilege IAM user key stored in its
  root-only `.env`.
- Details: `docs/architecture/environments.md`.

## Stack
- **Backend:** Python 3.13, Django 5.2 LTS, DRF, drf-spectacular, PostgreSQL 17, Redis, Celery +
  django-celery-beat, boto3, pywebpush. Tooling: uv, ruff, mypy + django-stubs, pytest-django,
  factory-boy, time-machine, moto, import-linter.
- **Frontend:** React 19, TypeScript strict, Vite (pnpm), React Router, vite-plugin-pwa (Workbox),
  TanStack Query, openapi-fetch, Zustand, Motion, i18next, @rive-app/react-canvas, canvas-confetti,
  hls.js, Uppy core + @uppy/aws-s3. CSS Modules + tokens in `src/styles/tokens.css`.
- **Media:** private S3 bucket, CloudFront with signed cookies, MediaConvert → HLS.
- **Auth:** Django session cookie + CSRF. No JWT.

## Architecture rules
- Every Django app has the same layout: `models.py`, `services.py` (writes), `selectors.py` (reads),
  `api/{serializers,views,urls}.py`, `admin.py`, `tasks.py`, `tests/`. Layers are enforced by
  import-linter. See `docs/architecture/backend.md`.
- Business rules live in `services.py`, never in views, serializers or tasks. Views and Celery
  tasks call services. Non-trivial reads go through `selectors.py`.
- Every domain row carries `crew_id`. A user can belong to several crews (through `Member`).
- Store datetimes in UTC. A "challenge day" is a local date in `Crew.timezone`
  (default `Europe/Chisinau`). Test around midnight and DST switches.
- Scheduled jobs are idempotent (safe to run twice).
- Tree stage and flame tier are derived in the API, not stored.

## Game rules that code must respect
- One proposer per month, taken from a fixed rotation (`Member.rotation_position`). Only the
  proposer can create or edit the next challenge. Challenges go draft → sealed → active → finished.
- A check-in is created the moment proof upload *starts* (status `uploading`). It counts for the
  day if the upload completes within 24 h after that day's midnight deadline.
- Missed day → streak reset, tree wilted, one pending Wheel of Doom spin per missed day.
- The Wheel of Doom result is chosen on the server before the client animation starts.

## Large uploads (up to 20 GB) - non-negotiable
- Files never go through Django. Browser → S3 multipart upload with presigned part URLs.
- Part size 16 MiB (< 1 GiB files) or 64 MiB (larger). S3 limits: 5 MiB min part (except last),
  5 GiB max part, 10,000 parts max. Validate size ≤ 20 GB server-side.
- 4 parallel parts, 6 retries with exponential backoff, auto re-sign expired URLs,
  pause on `offline`, resume on `online`.
- Report each completed part (number + ETag) to the API. Also keep `upload_id`, file fingerprint
  (name + size + lastModified) and completed parts in IndexedDB. Resume = user re-picks the same
  file, fingerprint matches, only missing parts are uploaded.
- The upload manager is a global store outside routes: the user is never blocked from using the
  app while an upload runs. Progress shows in the tab bar.
- Request a Screen Wake Lock during uploads (tolerate rejection). Warn before > 2 GB on phones.
- On complete: CompleteMultipartUpload, HeadObject to verify size, enqueue MediaConvert job.
- S3 CORS allows PUT from the app origin and exposes `ETag`. Lifecycle aborts incomplete
  multipart uploads after 7 days.

## PWA constraints (iOS + Android)
- Android: capture `beforeinstallprompt`, show our own install button.
- iOS: no install prompt. Provide an animated "Share → Add to Home Screen" guide.
- iOS push works only when installed to the Home Screen (16.4+) and after a user gesture.
  Ask for push permission after the first check-in, never on first load.
- No background upload, background sync or background fetch on iOS. Uploads pause when the app is
  backgrounded or the screen locks. All timed logic runs on the server and reaches users by Web Push.
- Browser storage may be evicted on iOS: it is a cache; the server is the source of truth.
- Video capture: `<input type="file" accept="video/*" capture>`. Audio: MediaRecorder. Handle both
  MP4/AAC (Safari) and WebM/Opus (Chrome); normalize on the server.
- Service worker: precache app shell + Rive assets; network-only for `/api` and `/admin`; never
  cache presigned URLs or media uploads.
- Use `100dvh`, respect `env(safe-area-inset-*)`, touch targets ≥ 44 px.

## UI and motion
- The product goal is fun: every important action has a satisfying animation
  (check-in → tree grows + confetti + flame spark; spin; reveal flip).
- Every tap responds within 100 ms (optimistic updates with TanStack Query, rollback on error).
- Animate only `transform` and `opacity`; target 60 fps on a mid-range Android phone.
- Lazy-load the Rive runtime and hls.js; code-split routes; first load < 2 s on 4G.
- Honor `prefers-reduced-motion`. Sounds only after user interaction and off by default.
- Romanian (default) and English from the start; no hard-coded UI strings.

## Testing
- Backend: pytest + pytest-django against Postgres (never SQLite); time-machine for date logic;
  moto for S3 and MediaConvert.
- Frontend: Vitest + Testing Library; Playwright for check-in and upload flows.
- Before calling an upload change done: test a multi-GB upload with a network interruption and a resume.

## Commits and pull requests
- Small commits, imperative subject line, scope prefix: `backend: add invite service`.
- One work package per pull request. Fill in `.github/pull_request_template.md`.
