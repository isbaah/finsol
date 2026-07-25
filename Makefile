.PHONY: setup dev stop logs migrate makemigrations seed test test-backend test-frontend lint format typecheck build sms-dry-run reconcile createsuperuser

# ── Local dev credentials (override on the CLI: make createsuperuser ADMIN_PASS=…) ──
# No ADMIN_USER: the custom User model (apps/accounts/models.py) has no
# username field at all — email is the sole identifier (USERNAME_FIELD).
ADMIN_EMAIL ?= admin@flexibuygh.com
ADMIN_PASS  ?= admin1234

# ── Base compose command (auto-loads docker-compose.override.yml locally) ──────
DC = docker compose

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
	docker compose exec backend python manage.py seed_roles

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
	docker compose exec backend python manage.py process_due_sms --dry-run

reconcile:
	docker compose exec backend python manage.py reconcile

createsuperuser:
	$(DC) exec \
		-e DJANGO_SUPERUSER_EMAIL=$(ADMIN_EMAIL) \
		-e DJANGO_SUPERUSER_PASSWORD=$(ADMIN_PASS) \
		backend python manage.py create_super_admin --noinput