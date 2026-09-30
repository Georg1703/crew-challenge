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
`-- tests/               # conftest.py, factories/, cross-app tests
```

Apps: `core`, `accounts`, `crews` (M1) · `challenges`, `checkins`, `media` (M2) · `doom` (M3) ·
`notifications` (M4).

## Layer rules (enforced by import-linter in `make check`)
- `api` → `services`, `selectors`, serializers. Views never write through the ORM.
- `services` and `selectors` never import from `api`.
- Another app is used only through its `services` / `selectors`.
- `integrations/*` is the only place that imports `boto3` or `pywebpush`. Services get adapters from
  factory functions such as `get_object_storage()`; tests get the in-memory implementation.

## Conventions
- Models inherit `TimeStampedModel` (UUID pk, `created_at`, `updated_at`); crew data inherits
  `CrewScopedModel` (adds `crew` FK and `.for_crew(crew)`).
- Service functions are keyword-only and typed: `def accept_invite(*, code: str, username: str, password: str) -> Member:`.
  Wrap multi-step writes in `transaction.atomic()`.
- Services raise `DomainError` subclasses with a stable `code`; never raise DRF exceptions from services.
- Business dates come from `apps.core.clock` (`now()`, `crew_today(crew)`), never `timezone.now()`.
- Every endpoint has `@extend_schema` with request and response serializers, so the contract is exact.
- Permissions: `IsCrewMember`, `IsCrewAdmin`. The current member is `request.member`.
- Celery tasks are idempotent, take ids (not objects), and call one service.

## Tests
- pytest-django on Postgres. factory-boy factories in `backend/tests/factories/`.
- Service tests cover rules and edge cases; API tests cover auth, permissions, and the response shape.
- Freeze time with `time_machine` for anything date-related, including a DST transition case.
- S3 and MediaConvert: moto or the in-memory adapter. Never call real AWS from tests.

## Recipes
- New app: `docs/recipes/new-backend-app.md`
- New endpoint: `docs/recipes/new-endpoint.md`
- Migration: `docs/recipes/new-migration.md`
- Celery task: `docs/recipes/new-celery-task.md`
