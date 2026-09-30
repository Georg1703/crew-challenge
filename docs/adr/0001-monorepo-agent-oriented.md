# 0001. Monorepo organized for coding agents

**Status:** Accepted
**Date:** 2026-09-30

## Context

Most code will be written by coding agents working in short sessions, reviewed by one owner.
Agents do best when the repo tells them where things go, how to verify work, and which decisions
are already made.

## Decision

One repository holds `backend/`, `frontend/`, `infra/`, `contracts/`, `docs/`, and `tools/`.

- A root `AGENTS.md` (map, rules, commands, definition of done) plus short nested `AGENTS.md`
  files per area. `CLAUDE.md` files contain only `@AGENTS.md`.
- A single `Makefile` is the only entry point for commands; `make check` is the definition of done.
- Step-by-step recipes in `docs/recipes/`, mirrored as slash commands in `.claude/commands/`.
- Work split into packages with acceptance criteria in `docs/milestones/`.
- `tools/check_repo.py` keeps the docs honest: links resolve, ADRs are indexed, packages have a status.

## Consequences

- Agents can start cold and find the right place and the right command without asking.
- Docs are part of the code: a broken link or missing ADR fails CI.
- Keeping docs current is real work; every package that changes a convention updates the docs in
  the same pull request.
