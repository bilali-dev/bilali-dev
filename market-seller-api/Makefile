.PHONY: install test lint run worker docker-build docker-run compose-up compose-down

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

docker-build:
	docker build -t market-seller-api .

docker-run:
	docker run --rm -p 8000:8000 market-seller-api

compose-up:
	docker compose up --build

compose-down:
	docker compose down
