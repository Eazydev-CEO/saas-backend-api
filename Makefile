.PHONY: help up down logs build shell migrate makemigrations seed test lint format superuser

help:
	@echo "Common targets:"
	@echo "  up              Start dev stack (postgres, redis, mailhog, web, worker, beat)"
	@echo "  down            Stop and remove containers"
	@echo "  logs            Tail logs"
	@echo "  build           Rebuild images"
	@echo "  shell           Open a Django shell inside the web container"
	@echo "  migrate         Run migrations"
	@echo "  makemigrations  Generate new migrations"
	@echo "  seed            Seed canonical plans"
	@echo "  test            Run pytest"
	@echo "  lint            Run ruff"
	@echo "  format          Auto-fix with ruff"
	@echo "  superuser       Create a Django superuser"

up:
	docker compose up

down:
	docker compose down

logs:
	docker compose logs -f web worker beat

build:
	docker compose build

shell:
	docker compose exec web python manage.py shell

migrate:
	docker compose exec web python manage.py migrate

makemigrations:
	docker compose exec web python manage.py makemigrations

seed:
	docker compose exec web python manage.py seed_plans

test:
	docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.test web pytest

lint:
	docker compose exec web ruff check .

format:
	docker compose exec web ruff check --fix .

superuser:
	docker compose exec web python manage.py createsuperuser
