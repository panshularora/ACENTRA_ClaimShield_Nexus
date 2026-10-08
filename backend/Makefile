.PHONY: sync test demo generate train lint format typecheck check

sync:
	uv sync --frozen --extra dev

test:
	uv run pytest

demo:
	uv run uvicorn claimshield.api.main:app --reload --app-dir src --host 127.0.0.1 --port 8000

generate:
	uv run python -m claimshield generate --profile tiny --seed 7

train:
	uv run python -m claimshield train --profile panel --seed 7

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

format:
	uv run ruff format src tests

typecheck:
	uv run mypy

check: lint typecheck test
