# Crew Challenges

A fun, animated PWA for a small group of people (a *crew*) who set one shared challenge per month,
check in every day with proof, grow a tree in the crew garden, keep a streak flame alive, and spin
the Wheel of Doom when they miss a day.

The first crew is our family. The app is built so any group can use it.

## Quick start (local)

Requirements: Docker with Compose, GNU Make, Python 3.11+ (for repo tools), an AWS CLI profile
named `cc-dev` with access to the dev media bucket.

```sh
make help     # list every command
make setup    # first-time setup
make dev      # run the app at http://localhost:5173
make check    # everything CI runs
```

## How the repo is organized

| Path | Contents |
|---|---|
| `backend/` | Django + DRF API, Celery tasks |
| `frontend/` | React PWA |
| `contracts/` | Generated OpenAPI contract shared by both |
| `infra/` | AWS JSON documents, Caddy config, deploy and backup scripts |
| `docs/` | Architecture, recipes, glossary |
| `tools/` | Repo helper scripts |

## Working with coding agents

- [`AGENTS.md`](AGENTS.md) is the entry point: repo map, commands, rules, and the definition of done.
  Each area (`backend/`, `frontend/`, `infra/`) has its own shorter `AGENTS.md`.
  `CLAUDE.md` files only point to `AGENTS.md`, so every agent reads the same instructions.
- [`docs/recipes/`](docs/recipes/) has step-by-step guides for common changes. The same guides are
  available as Claude Code slash commands in [`.claude/commands/`](.claude/commands/).
- `make check` is the single gate: a task is done when it passes.

## Documentation

- [Architecture overview and key decisions](docs/architecture/overview.md)
- [Recipes](docs/recipes/README.md)
- [Glossary](docs/glossary.md)
