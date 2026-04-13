.PHONY: install install-dev test test-fast lint format typecheck run clean check all build

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	python -m pytest tests/ -v --tb=short

test-fast:
	python -m pytest tests/ -v -m "not slow"

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

typecheck:
	mypy --strict src/

run:
	python -m src.server

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache dist build
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.eggs" -exec rm -rf {} + 2>/dev/null || true

check: lint typecheck test

all: lint typecheck test

build:
	python -m build
