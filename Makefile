# Crew Challenges - the single entry point for every command.
# Agents and humans: run `make help`. Never call tools directly when a target exists.
#
# Targets for parts that do not exist yet say what is missing.
# `make check` always runs the repo-level checks and skips areas that are not scaffolded yet.

SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help
MAKEFLAGS += --no-print-directory

COMPOSE      := docker compose
BACKEND_DIR  := backend
FRONTEND_DIR := frontend
UV           := uv --directory $(BACKEND_DIR) run
PNPM         := pnpm --dir $(FRONTEND_DIR)
PYTHON       := python3

HAS_BACKEND  := $(wildcard $(BACKEND_DIR)/pyproject.toml)
HAS_FRONTEND := $(wildcard $(FRONTEND_DIR)/package.json)
HAS_COMPOSE  := $(wildcard compose.yaml)

# $(call require,<path>,<what>) - stop with a helpful message if <path> is missing.
define require
	@test -e $(1) || { echo "ERROR: $(2) is not set up yet ($(1) is missing)."; exit 1; }
endef

# $(call skip,<what>)
define skip
	@echo "SKIP: $(1): not set up yet"
endef

##@ Getting started

.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"} \
		/^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } \
		/^[a-zA-Z0-9_-]+:.*##/ { printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo

.PHONY: setup
setup: ## First-time setup: .env, images, migrations, seed data
	$(call require,compose.yaml,Local environment)
	@test -f .env || { cp .env.example .env; echo "created .env from .env.example"; }
	$(COMPOSE) build
	$(COMPOSE) run --rm migrate
	$(COMPOSE) run --rm backend sh -c "python manage.py seed_demo && python manage.py seed_demo_challenge"
	@echo "OK: setup done - run: make dev, then open http://localhost:5173"

##@ Running locally

.PHONY: dev
dev: ## Start everything in the background, wait until healthy (app at http://localhost:5173)
	$(call require,compose.yaml,Local environment)
	@$(COMPOSE) up --build --detach --wait --wait-timeout 300 \
		|| { echo "ERROR: a service did not start; see: make ps, then make logs s=<service>"; exit 1; }
	@echo "OK: running at http://localhost:5173 - make logs to follow output, make stop to stop"

.PHONY: stop
stop: ## Stop local containers (data is kept)
	$(call require,compose.yaml,Local environment)
	$(COMPOSE) --profile preview --profile tunnel down

.PHONY: ps
ps: ## Show local containers and their health
	$(call require,compose.yaml,Local environment)
	$(COMPOSE) ps

.PHONY: logs
logs: ## Follow logs of all services (or: make logs s=backend)
	$(call require,compose.yaml,Local environment)
	$(COMPOSE) logs -f $(s)

.PHONY: shell
shell: ## Django shell inside the backend container
	$(call require,compose.yaml,Local environment)
	$(COMPOSE) exec backend python manage.py shell

.PHONY: tunnel
tunnel: ## HTTPS URL to the dev server for a phone (hot reload, not installable; run make dev first)
	$(call require,compose.yaml,Local environment)
	$(COMPOSE) --profile tunnel run --rm tunnel

.PHONY: preview
preview: ## Production build + HTTPS URL for a phone: test installing and offline (Ctrl+C ends the tunnel)
	$(call require,compose.yaml,Local environment)
	@echo "Building the production frontend (about a minute)..."
	@$(COMPOSE) --profile preview up --build --detach --wait --wait-timeout 300 --force-recreate preview \
		|| { echo "ERROR: preview did not start; see: make logs s=preview"; exit 1; }
	@echo "OK: preview at http://localhost:4173 - opening the tunnel"
	TUNNEL_TARGET=http://preview:4173 $(COMPOSE) --profile tunnel run --rm tunnel

##@ Database

.PHONY: migrate
migrate: ## Apply database migrations (make dev also does this on start)
	$(call require,compose.yaml,Local environment)
	$(COMPOSE) run --rm migrate

.PHONY: makemigrations
makemigrations: ## Create migrations (optional: make makemigrations app=crews)
	$(call require,$(BACKEND_DIR)/pyproject.toml,Backend)
	$(UV) python manage.py makemigrations $(app) --settings=config.settings.test

.PHONY: superuser
superuser: ## Create a Django admin user (asks for username, email, password); admin at /admin
	$(call require,compose.yaml,Local environment)
	$(COMPOSE) run --rm backend python manage.py createsuperuser

.PHONY: seed
seed: ## Load the demo crew and a challenge running this month (local only)
	$(call require,compose.yaml,Local environment)
	$(COMPOSE) run --rm backend sh -c "python manage.py seed_demo && python manage.py seed_demo_challenge"

##@ Quality

.PHONY: install
install: ## Install backend and frontend dependencies and the git hooks
	$(call require,$(BACKEND_DIR)/pyproject.toml,Backend)
	uv --directory $(BACKEND_DIR) sync --frozen
	$(PNPM) install --frozen-lockfile
	@command -v pre-commit >/dev/null && pre-commit install \
		|| echo "SKIP: pre-commit not found; install it with 'pipx install pre-commit', then run make install"

.PHONY: check
check: check-repo check-compose check-backend check-frontend check-contract ## Everything CI runs; must pass before a task is done
	@echo "OK: make check passed"

.PHONY: check-repo
check-repo: ## Repo-level checks: docs links, referenced paths, ASCII, required files
	@out=$$($(PYTHON) -m unittest discover -s tools/tests 2>&1) || { echo "$$out"; echo "ERROR: tool tests failed"; exit 1; }; echo "OK: tool tests passed"
	@$(PYTHON) tools/check_repo.py

.PHONY: check-compose
check-compose: ## Validate compose.yaml (skipped when Docker is not installed)
ifeq ($(HAS_COMPOSE),)
	$(call skip,compose check)
else
	@if command -v docker >/dev/null; then \
		$(COMPOSE) --profile tunnel config --quiet && echo "OK: compose.yaml is valid"; \
	else echo "SKIP: compose check: docker not installed"; fi
endif

.PHONY: check-backend
check-backend: ## Backend: format, lint, types, layers, migrations, tests + coverage
ifeq ($(HAS_BACKEND),)
	$(call skip,backend checks)
else
	$(UV) ruff format --check .
	$(UV) ruff check .
	$(UV) mypy .
	$(UV) lint-imports
	$(UV) python manage.py makemigrations --check --dry-run --settings=config.settings.test
	$(UV) pytest --cov
endif

.PHONY: check-frontend
check-frontend: ## Frontend: format, lint, types, tests, build
ifeq ($(HAS_FRONTEND),)
	$(call skip,frontend checks)
else
	$(PNPM) run format:check
	$(PNPM) run lint
	$(PNPM) run typecheck
	$(PNPM) run test
	$(PNPM) run build
endif

.PHONY: check-contract
check-contract: ## Fail if the committed API contract (and TS client) is out of date
ifeq ($(HAS_BACKEND),)
	$(call skip,contract drift check)
else
	@$(MAKE) schema >/dev/null
	@git diff --exit-code -- contracts/openapi.yaml $(if $(HAS_FRONTEND),$(FRONTEND_DIR)/src/api/schema.gen.ts) \
		|| { echo "ERROR: API contract is out of date: run 'make schema' and commit the result."; exit 1; }
	@echo "OK: API contract is up to date"
endif

.PHONY: e2e
e2e: ## End-to-end tests (Playwright) against the real backend; needs Postgres and Redis
	$(call require,$(FRONTEND_DIR)/package.json,Frontend)
	$(PNPM) exec playwright test

.PHONY: test
test: ## Run all tests
ifneq ($(HAS_BACKEND),)
	$(UV) pytest
endif
ifneq ($(HAS_FRONTEND),)
	$(PNPM) run test
endif
	@true

.PHONY: test-fast
test-fast: ## Run tests only for apps and files changed on this branch
ifneq ($(HAS_BACKEND),)
	$(UV) pytest $$($(PYTHON) tools/test_targets.py backend)
endif
ifneq ($(HAS_FRONTEND),)
	$(PNPM) exec vitest run --changed main
endif
	@true

.PHONY: fmt
fmt: ## Format all code
ifneq ($(HAS_BACKEND),)
	$(UV) ruff format .
	$(UV) ruff check --fix .
endif
ifneq ($(HAS_FRONTEND),)
	$(PNPM) run format
endif
	@true

##@ API contract

.PHONY: schema
schema: ## Regenerate contracts/openapi.yaml (and the frontend TS client once frontend/ exists)
	$(call require,$(BACKEND_DIR)/pyproject.toml,Backend)
	$(UV) python manage.py spectacular --validate --fail-on-warn --settings=config.settings.test \
		--file ../contracts/openapi.yaml
ifneq ($(HAS_FRONTEND),)
	$(PNPM) exec openapi-typescript ../contracts/openapi.yaml -o src/api/schema.gen.ts
endif
	@echo "OK: contract regenerated"
