# Crew Challenges

A PWA for a small group of people (a *crew*) who set shared challenges (monthly, weekly or daily)
and check in every day with proof: a photo or a video. Trees, streak flames and the Wheel of Doom
are planned for after the first version (see `AGENTS.md`).

The first crew is our family. The app is built so any group can use it.

## Quick start (local)

Requirements: Docker with Compose, GNU Make, Python 3.11+ (for repo tools), an AWS CLI profile
named `cc-dev` with access to the dev media bucket (uploads only; the rest works without it).
For `make check` and `make e2e` on your machine also: uv and Node 22 with pnpm (`corepack enable`).

```sh
make help     # list every command
make setup    # first-time setup: .env, images, database, demo crew
make dev      # start in the background: http://localhost:5173 (log in as ana / garden-flame-2026)
make logs     # follow the output; make stop stops everything
make tunnel   # HTTPS URL to the dev server for your phone
make preview  # production build + HTTPS URL: install the app on your phone
make check    # everything CI runs
```

Details and troubleshooting: [docs/architecture/environments.md](docs/architecture/environments.md).

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
- [Design system](docs/design-system.md)
- [Glossary](docs/glossary.md)
