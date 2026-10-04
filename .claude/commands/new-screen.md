---
description: Add a PWA screen following the feature-folder conventions
argument-hint: <feature/screen name - what it shows>
---

Add this screen: $ARGUMENTS

Read `docs/design-system.md` first, then follow `docs/recipes/new-screen.md` and
`frontend/AGENTS.md`. Build only from `shared/ui` components and tokens. Include loading, empty,
and error states, translations in both languages, and a component test. Finish with `make check`
passing.
