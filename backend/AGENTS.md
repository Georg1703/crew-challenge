# backend/AGENTS.md

Django 5.2 + DRF API and Celery tasks. Read the root `AGENTS.md` first.
Full detail: `docs/architecture/backend.md`. API rules: `docs/architecture/api-conventions.md`.

## Layout
```
backend/
|-- config/settings/{base,local,test,production}.py   # django-environ; no secrets in code
|-- config/{urls.py, celery.py, wsgi.py}
|-- apps/<app>/                                       # one folder per domain area
|   |-- models.py        # data + invariants only
|   |-- services.py      # every write and business rule
|   |-- selectors.py     # every non-trivial read
|   |-- api/{serializers.py, views.py, urls.py}
|   |-- admin.py
|   |-- tasks.py         # thin Celery wrappers around services
|   `-- tests/{test_services.py, test_selectors.py, test_api.py}
|-- integrations/<name>/ # boto3 / pywebpush live ONLY here (ABC + implementations + factory)
|-- tests/factories/     # factory-boy factories, one module per app
`-- conftest.py          # fixtures for all tests: api_client, user, auth_client, object_storage
```

Apps: `core`, `accounts`, `crews`, `challenges`, `checkins`, `media`, `doom`, `notifications`.
Create each one when it is first needed.

## Layer rules (enforced by import-linter in `make check`)
- `api` -> `services`, `selectors`, serializers. Views never write through the ORM.
- `services` and `selectors` never import from `api`.
- Another app is used only through its `services` / `selectors`.
- `integrations/*` is the only place that imports `boto3` or `pywebpush`. Services get adapters from
  factory functions such as `get_object_storage()`; tests get the in-memory implementation.

## Conventions
- Models inherit `TimeStampedModel` (UUID pk, `created_at`, `updated_at`); crew data inherits
  `apps.crews.models.CrewScopedModel` (adds `crew` FK and `.for_crew(crew)`).
- Service functions are keyword-only and typed: `def accept_invite(*, code: str, username: str, password: str) -> Member:`.
  Wrap multi-step writes in `transaction.atomic()`.
- Services raise `DomainError` subclasses with a stable `code`; never raise DRF exceptions from services.
- Time: instants are aware UTC datetimes; a challenge day is a `DateField` in the crew's time zone.
  Get time only from `apps.core.clock` (`now()`, `crew_today(crew)`, `day_bounds_utc(day, tz)`).
  ruff bans `timezone.now()`, `datetime.now()` and `date.today()` elsewhere. Never use "24 hours ago"
  as a day boundary: DST days are 23 or 25 hours.
- Every endpoint has `@extend_schema` with request and response serializers, so the contract is exact.
- Crew endpoints use `apps.crews.api.permissions.IsCrewMember`, which sets `request.member`.
  Admin-only rules are enforced in services (`NotCrewAdmin`), not in permission classes.
- Every unsafe request must carry a CSRF token, also for anonymous users (login, join).
- Celery tasks are idempotent, take ids (not objects), and call one service.

## Tests
- pytest-django on Postgres (`TEST_DATABASE_URL`, default localhost). Factories in `backend/tests/factories/`.
- `make check` enforces 90% line + branch coverage of `services.py`, `selectors.py`, `apps/core` and
  `integrations`. Test rules and edge cases there, not getters and settings.
- Saving a naive datetime fails the test run (Django's warning is turned into an error).
- Service tests cover rules and edge cases; API tests cover auth, permissions, and the response shape.
- Create test data with `XFactory.create(...)`, not `XFactory(...)`: only `.create()` is typed.
- For unsafe requests use the `browser` fixture (sends a real CSRF token) and `force_login`;
  a test that gets `403 csrf_failed` is usually using the wrong client.
- Freeze time with `time_machine` for anything date-related, including a DST transition case.
- Storage: services get `InMemoryObjectStorage` automatically (the `object_storage` fixture). The S3
  adapter is a thin boto3 wrapper without unit tests (excluded from coverage); it is checked against
  the real dev bucket by the upload smoke test. Never call AWS from tests.

## Recipes
- New app: `docs/recipes/new-backend-app.md`
- New endpoint: `docs/recipes/new-endpoint.md`
- Migration: `docs/recipes/new-migration.md`
- Celery task: `docs/recipes/new-celery-task.md`
