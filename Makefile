.PHONY: help sync install hooks hooks-run test test-unit lint lint-fix format format-check audit ci check clean

help: ## Lists all available Makefile commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}'

sync: ## Installs runtime and dev dependencies using uv
	uv sync

install: sync ## Alias for sync

hooks: ## Installs the pre-commit hooks into .git/hooks
	uv run pre-commit install

hooks-run: ## Runs all pre-commit hooks against all files
	uv run pre-commit run --all-files

test: ## Runs the test suite with pytest
	uv run pytest

test-unit: ## Run unit tests only (no docker required)
	uv run pytest tests/unit

lint: ## Checks code with ruff
	uv run ruff check .

lint-fix: ## Automatically fixes ruff lint issues
	uv run ruff check --fix .

format: ## Formats code with ruff
	uv run ruff format .

format-check: ## Verifies formatting with ruff without modifying files
	uv run ruff format --check .

audit: ## Audits dependencies for known security vulnerabilities
	uv run pip-audit

ci: lint format-check audit test ## Runs full verification pipeline locally

check: ci ## Alias for ci

clean: ## Cleans build artifacts and caches
	rm -rf .ruff_cache .pytest_cache dist build *.egg-info .coverage htmlcov
	find . -type d -name '__pycache__' -not -path './.venv*' -exec rm -rf {} +

.PHONY: db-up db-down migrate migration

db-up: ## Start local postgres and wait for it to be healthy
	docker compose up -d --wait db

db-down: ## Stop local postgres
	docker compose down

migrate: ## Apply migrations up to head
	uv run alembic upgrade head

migration: ## Autogenerate a migration: make migration MSG="describe change"
	uv run alembic revision --autogenerate -m "$(MSG)"
