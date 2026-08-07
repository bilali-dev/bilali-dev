.PHONY: install test lint run docker-build docker-run

install:
	python -m pip install --upgrade pip
	python -m pip install -r requirements-dev.txt

test:
	pytest -q

lint:
	ruff check .

run:
	uvicorn app.main:app --reload

docker-build:
	docker build -t market-seller-api .

docker-run:
	docker run --rm -p 8000:8000 market-seller-api
