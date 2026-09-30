# Recipe: work a package

1. Read the root `AGENTS.md` and the nested `AGENTS.md` for every area the package touches.
2. Open the milestone file (for example `docs/milestones/m1.md`) and find the package.
   Change its status line to `**Status:** in progress`.
3. Read the ADRs and architecture pages the package links to.
4. List the files you expect to create or change before writing code. If the list reaches outside
   the package scope, stop and write a "Follow-ups" entry instead.
5. Implement using the matching recipes. Write tests alongside the code, not after.
6. Run `make check`. Fix everything it reports. Do not disable a check to make it pass.
7. Check each acceptance criterion of the package and note how it was verified.
8. Set `**Status:** done` and add one line under the package: `Done: <what, how verified>`.
9. Commit with a scope prefix (`backend: …`, `frontend: …`, `docs: …`) and open a pull request
   using the template.

If you are blocked (missing decision, missing credentials, unclear rule), set
`**Status:** blocked`, write the question under the package, and stop.
