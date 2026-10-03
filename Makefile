.PHONY: install lint test db-up run clean

install:
	python -m pip install -e ".[dev]"

lint:
	ruff check src tests

test:
	pytest

db-up:
	docker compose up -d postgres

run:
	docker compose --profile pipeline run --rm pipeline run-all

clean:
	docker compose down

