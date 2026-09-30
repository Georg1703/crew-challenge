# 0010. "Crew" as the name for a group

**Status:** Accepted
**Date:** 2026-09-30

## Context

The first users are a family, but the app should work for any group of friends or a team.
"Family" in code and UI would lock that in. "Group" collides with Django's `auth.Group`.

## Decision

The group entity is called **Crew** everywhere: model `Crew`, field `crew_id`, app `crews`,
UI "Crew" (Romanian: "Echipa"). A user joins a crew through `Member`, so one person can be in
several crews.

## Consequences

- Neutral wording for any kind of group; no clash with Django names.
- The glossary is the reference for this and every other domain word.
