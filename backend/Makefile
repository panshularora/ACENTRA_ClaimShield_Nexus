.PHONY: sync test demo generate lint

sync:
	uv sync --extra dev

test:
	uv run pytest

demo:
	uv run uvicorn claimshield.api.main:app --reload --app-dir src --host 127.0.0.1 --port 8000

generate:
	uv run python -m claimshield generate --profile tiny --seed 7

lint:
	uv run ruff check src tests
