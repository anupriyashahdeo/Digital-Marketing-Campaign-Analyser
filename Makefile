dev:
	docker compose up --build
test:
	cd apps/api && pip install -e ".[dev]" -q && pytest -q
lint:
	cd apps/api && ruff check src tests
migrate:
	docker compose run --rm api alembic upgrade head
revision:
	docker compose run --rm api alembic revision --autogenerate -m "$(m)"
