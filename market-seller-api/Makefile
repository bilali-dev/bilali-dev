.PHONY: install test lint run worker migrate makemigration docker-build docker-run compose-up compose-down

install:
	python -m pip install --upgrade pip
	python -m pip install -r requirements-dev.txt

test:
	pytest -q

lint:
	ruff check .

run:
	uvicorn app.main:app --reload

worker:
	python -m app.worker

migrate:
	alembic upgrade head

# Usage: make makemigration m="add column foo to bar"
makemigration:
	alembic revision --autogenerate -m "$(m)"

docker-build:
	docker build -t market-seller-api .

docker-run:
	docker run --rm -p 8000:8000 market-seller-api

compose-up:
	docker compose up --build

compose-down:
	docker compose down
