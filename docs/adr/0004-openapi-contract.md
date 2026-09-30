# 0004. OpenAPI contract with a generated TypeScript client

**Status:** Accepted
**Date:** 2026-09-30

## Context

Frontend and backend change often, usually in the same package. Hand-written API types drift.

## Decision

drf-spectacular generates `contracts/openapi.yaml` from the code. openapi-typescript generates
`frontend/src/api/schema.gen.ts`, used by openapi-fetch. `make schema` regenerates both; CI fails
when the committed files are out of date. Every view declares its request and response schemas.

## Consequences

- A wrong path, field, or type in the frontend is a compile error.
- The contract is reviewable in pull requests.
- Views must carry accurate `@extend_schema` annotations.
