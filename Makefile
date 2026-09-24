.PHONY: up down down-volumes ps logs logs-fetcher fetch test

up:
	docker compose up -d --build

down:
	docker compose down

down-volumes:
	docker compose down -v

ps:
	docker compose ps

logs:
	docker compose logs -f

logs-fetcher:
	docker compose logs -f fetcher

fetch:
	docker compose exec fetcher python run.py

test:
	python -m pytest
