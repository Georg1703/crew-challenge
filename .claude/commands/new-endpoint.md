---
description: Add an API endpoint from service to typed frontend hook
argument-hint: <METHOD /api/v1/path — what it does>
---

Add this endpoint: $ARGUMENTS

Follow `docs/recipes/new-endpoint.md` step by step, respecting `docs/architecture/api-conventions.md`
and the layer rules in `backend/AGENTS.md`. Write service tests and API tests, run `make schema`,
add the frontend hook, and finish with `make check` passing.
