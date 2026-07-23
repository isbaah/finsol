.PHONY: setup dev stop logs migrate makemigrations seed test test-backend test-frontend lint format typecheck build sms-dry-run reconcile

setup:
	cp -n .env.example .env || true
	docker compose build

dev:
	docker compose up

stop:
	docker compose down

logs:
	docker compose logs -f

migrate:
	docker compose exec backend python manage.py migrate

makemigrations:
	docker compose exec backend python manage.py makemigrations

seed:
	@echo "No seed data required yet — role seeding (seed_roles) arrives in Stage 3."

test: test-backend test-frontend

test-backend:
	docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.test backend pytest

test-frontend:
	docker compose exec frontend npm run test

lint:
	docker compose exec backend ruff check .
	docker compose exec frontend npm run lint

format:
	docker compose exec backend ruff format .
	docker compose exec frontend npm run format

typecheck:
	docker compose exec frontend npm run typecheck

build:
	docker compose build
	docker compose exec frontend npm run build

sms-dry-run:
	@echo "process_due_sms is not implemented yet — arrives in Stage 11."

reconcile:
	@echo "Reconciliation reporting command is not implemented yet — arrives in Stage 10."
