# 0002. Django apps with service and selector layers

**Status:** Accepted
**Date:** 2026-09-30

## Context

Django lets business logic spread across models, serializers, views, and signals. That makes it
hard for agents (and people) to know where a rule lives, and hard to reuse it from Celery tasks.

## Decision

Every app has the same layout: `models.py`, `services.py` (all writes and rules), `selectors.py`
(non-trivial reads), `api/` (thin DRF views and serializers), `tasks.py` (thin Celery wrappers),
and `tests/`. External SDKs are wrapped in `integrations/` behind abstract base classes with a
factory function. Layer boundaries are enforced with import-linter. No Django signals for business
logic.

## Consequences

- One obvious place for each kind of code; views and tasks share the same services.
- Services are easy to unit test; adapters swap to in-memory versions in tests.
- Slightly more files than a "fat model" style.
