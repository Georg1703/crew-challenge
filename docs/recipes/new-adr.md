# Recipe: new ADR

1. Copy `docs/adr/template.md` to `docs/adr/NNNN-short-title.md`, using the next number.
2. Fill in Context, Decision, and Consequences in plain language. One decision per ADR.
3. Set `**Status:** Proposed` until the owner agrees, then `Accepted`.
4. If it replaces an earlier decision, set the old ADR's status to `Superseded` and add
   "Superseded by NNNN" under it.
5. Add a row to the table in `docs/adr/README.md`.
6. Update any docs or `AGENTS.md` rules the decision changes.
7. Run `make check-repo`.
