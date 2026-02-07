.PHONY: lint
lint:
	uv run ruff check --exit-zero .
	uv run ruff format --check .

.PHONY: format
format:
	uv run ruff check --fix .
	uv run ruff format .

.PHONY: typecheck
typecheck:
	uv run pyright --project pyproject.toml .

.PHONY: check
check: typecheck format lint

.PHONY: test
test:
	uv run pytest -v .
