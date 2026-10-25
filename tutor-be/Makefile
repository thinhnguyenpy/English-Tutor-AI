.PHONY: install run start upgrade downgrade migrate format lint test help

install:
	uv sync

run:
	uv run fastapi dev src/main.py --port 8000

start:
	uv run python -m uvicorn src.main:app --host 0.0.0.0 --port 8000

upgrade:
	uv run alembic upgrade head

downgrade:
	uv run alembic downgrade -1

migrate:
	uv run alembic revision --autogenerate -m "$(filter-out $@,$(MAKECMDGOALS))"

%:
	@:

format:
	uv run ruff check src tests --fix
	uv run ruff format src tests

lint:
	uv run ruff check src tests

test:
	uv run pytest

help:
	@echo "Available targets:"
	@echo "  install    Install dependencies"
	@echo "  run        Run dev server with reload (:8000)"
	@echo "  start      Run production server"
	@echo "  upgrade    Apply all migrations"
	@echo "  downgrade  Rollback one migration"
	@echo "  migrate    Generate a new migration (pass a description)"
	@echo "  format     Auto-format + autofix with ruff"
	@echo "  lint       Lint with ruff"
	@echo "  test       Run pytest"
