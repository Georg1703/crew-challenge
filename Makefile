# Crew Challenges - the single entry point for every command.
# Agents and humans: run `make help`. Never call tools directly when a target exists.
#
# Targets for parts that do not exist yet print which work package adds them.
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

# $(call require,<path>,<what>,<package>) - stop with a helpful message if <path> is missing.
define require
	@test -e $(1) || { echo "ERROR: $(2) is not available yet. It is added in work package $(3) (docs/milestones/m1.md)."; exit 1; }
endef

# $(call skip,<what>,<package>)
define skip
	@echo "SKIP: $(1): not scaffolded yet (added in $(2))"
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
	$(call require,compose.yaml,Local environment,M1.6)
	@test -f .env || { cp .env.example .env; echo "created .env from .env.example"; }
	$(COMPOSE) build
	$(COMPOSE) up -d db redis
	$(COMPOSE) run --rm backend python manage.py migrate
	$(COMPOSE) run --rm backend python manage.py seed_demo
	@echo "OK: setup done - run: make dev"

##@ Running locally

.PHONY: dev
dev: ## Run everything locally (app at http://localhost:5173)
	$(call require,compose.yaml,Local environment,M1.6)
	$(COMPOSE) up

.PHONY: stop
stop: ## Stop local containers
	$(call require,compose.yaml,Local environment,M1.6)
	$(COMPOSE) down

.PHONY: logs
logs: ## Follow logs of all services (or: make logs s=backend)
	$(call require,compose.yaml,Local environment,M1.6)
	$(COMPOSE) logs -f $(s)

.PHONY: shell
shell: ## Django shell inside the backend container
	$(call require,compose.yaml,Local environment,M1.6)
	$(COMPOSE) exec backend python manage.py shell

.PHONY: tunnel
tunnel: ## Public HTTPS tunnel to the local app, for testing on a phone
	$(call require,compose.yaml,Local environment,M1.6)
	docker run --rm -it cloudflare/cloudflared:latest tunnel --no-autoupdate --url http://host.docker.internal:5173

##@ Database

.PHONY: migrate
migrate: ## Apply database migrations
	$(call require,compose.yaml,Local environment,M1.6)
	$(COMPOSE) run --rm backend python manage.py migrate

.PHONY: makemigrations
makemigrations: ## Create migrations (optional: make makemigrations app=crews)
	$(call require,$(BACKEND_DIR)/pyproject.toml,Backend,M1.2)
	$(UV) python manage.py makemigrations $(app)

.PHONY: seed
seed: ## Load the demo crew (known users and passwords, local only)
	$(call require,compose.yaml,Local environment,M1.6)
	$(COMPOSE) run --rm backend python manage.py seed_demo

##@ Quality

.PHONY: check
check: check-repo check-backend check-frontend check-contract ## Everything CI runs; must pass before a package is done
	@echo "OK: make check passed"

.PHONY: check-repo
check-repo: ## Repo-level checks: docs links, ADR index, milestone format, required files
	@out=$$($(PYTHON) -m unittest discover -s tools/tests 2>&1) || { echo "$$out"; echo "ERROR: tool tests failed"; exit 1; }; echo "OK: tool tests passed"
	@$(PYTHON) tools/check_repo.py

.PHONY: check-backend
check-backend: ## Backend: format, lint, types, layers, migrations, tests
ifeq ($(HAS_BACKEND),)
	$(call skip,backend checks,M1.2)
else
	$(UV) ruff format --check .
	$(UV) ruff check .
	$(UV) mypy .
	$(UV) lint-imports
	$(UV) python manage.py makemigrations --check --dry-run
	$(UV) pytest
endif

.PHONY: check-frontend
check-frontend: ## Frontend: format, lint, types, tests, build
ifeq ($(HAS_FRONTEND),)
	$(call skip,frontend checks,M1.4)
else
	$(PNPM) run format:check
	$(PNPM) run lint
	$(PNPM) run typecheck
	$(PNPM) run test
	$(PNPM) run build
endif

.PHONY: check-contract
check-contract: ## Fail if the committed API contract or TS client is out of date
ifeq ($(and $(HAS_BACKEND),$(HAS_FRONTEND)),)
	$(call skip,contract drift check,M1.2 + M1.4)
else
	@$(MAKE) schema
	@git diff --exit-code -- contracts/openapi.yaml $(FRONTEND_DIR)/src/api/schema.gen.ts \
		|| { echo "ERROR: API contract is out of date: run 'make schema' and commit the result."; exit 1; }
endif

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
schema: ## Regenerate contracts/openapi.yaml and the frontend TS client
	$(call require,$(BACKEND_DIR)/pyproject.toml,Backend,M1.2)
	$(call require,$(FRONTEND_DIR)/package.json,Frontend,M1.4)
	$(UV) python manage.py spectacular --validate --file ../contracts/openapi.yaml
	$(PNPM) exec openapi-typescript ../contracts/openapi.yaml -o src/api/schema.gen.ts
	@echo "OK: contract regenerated"
