---
description: Implement one work package from docs/milestones, end to end
argument-hint: <package id, e.g. M1.2>
---

Implement work package $ARGUMENTS.

1. Read `AGENTS.md`, then find package $ARGUMENTS in `docs/milestones/` and read every document it
   lists under "Read:" plus the nested `AGENTS.md` of each area it touches.
2. Follow `docs/recipes/work-package.md` exactly: set the status to in progress, list the files you
   will touch, stay inside the scope, and write out-of-scope findings under "Follow-ups".
3. Use the matching recipes in `docs/recipes/` for each kind of change.
4. Finish only when `make check` passes and every acceptance criterion is met. Then set the status
   to done with a one-line "Done:" note, and summarize what changed and how it was verified.

If a decision is missing, set the status to blocked, write the question, and stop.
