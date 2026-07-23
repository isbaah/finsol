# Loan Management System

A lean, auditable loan management web application: customers request loans, staff draft and send
amortization offers, customers digitally sign, staff record manual disbursements and repayments,
and Hubtel SMS keeps everyone informed. See `claude/CLAUDE_LOAN_MANAGEMENT_SYSTEM_MASTER_PROMPT.md`
for the full product specification and `docs/` for the living architecture/decision record.

No money moves through this application — disbursements and repayments happen outside it (bank /
mobile-money transfer) and are only **recorded** here by staff.

## Project status

Building stage-by-stage per `docs/BUILD_PROGRESS.md`. Currently: **Stage 1 — Project Foundation
and Local Development**.

## Prerequisites

- Docker Desktop (or Docker Engine + Compose plugin) — this is the only hard requirement to run
  the stack locally. The backend runs Python 3.13 and the frontend runs Node.js 24 **inside their
  containers**, so you do not need either installed on your host.
- Git.

## Setup

```bash
cp .env.example .env       # then edit values as needed for your machine
make setup                 # builds the Docker images
make dev                   # starts db, backend, frontend
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Backend health checks: http://localhost:8000/health/live/ and http://localhost:8000/health/ready/
- OpenAPI schema: http://localhost:8000/api/schema/ — interactive docs at http://localhost:8000/api/docs/
- Django admin (technical support only, not the business admin UI): http://localhost:8000/admin/

Stop the stack with `make stop`. Tail logs with `make logs`.

## Docker workflow

`docker-compose.yml` defines three services:

- `db` — PostgreSQL 17, with a healthcheck the backend waits on before starting.
- `backend` — Django, running `manage.py migrate` then the dev server on container start, with the
  `backend/` directory bind-mounted for hot reload.
- `frontend` — Next.js dev server (Turbopack), with the `frontend/` directory bind-mounted for hot
  reload; `node_modules` and `.next` are kept in named volumes so host/container installs don't
  collide.

Rebuild images after dependency changes with `docker compose build` (or `make setup`).

## Authentication setup (Stage 2)

Email/password + Google sign-in via `django-allauth[headless]`. Not yet wired up — see
`docs/BUILD_PROGRESS.md` for the stage plan. Google OAuth client ID/secret will be read from
`GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — never hard-coded.

## Hubtel setup (Stage 11)

SMS is disabled by default (`HUBTEL_ENABLED=false`, `SMS_DRY_RUN=true`). Real sending requires
explicit configuration of `HUBTEL_BASE_URL`, `HUBTEL_CLIENT_ID`, `HUBTEL_CLIENT_SECRET`, and
`HUBTEL_SENDER_ID` — see `docs/SMS_TEMPLATES.md` (added in Stage 11) once available.

## Email setup

Local development uses Django's console email backend by default (emails print to the backend
container's logs instead of sending). Set `EMAIL_BACKEND`, `EMAIL_HOST*`, and `DEFAULT_FROM_EMAIL`
for a real SMTP provider. `AGREEMENT_ACTION_EMAIL` is the mailbox that receives signed loan
agreements — it is a required, non-hard-coded configuration value (wired up in Stage 8).

## Running the scheduler (Stage 11)

Scheduled SMS reminders run via `python manage.py process_due_sms`, invoked by host/platform cron
or your deployment platform's scheduler — no Celery, no Redis. Not implemented yet.

## Tests

```bash
make test            # backend + frontend
make test-backend    # pytest, inside the backend container
make test-frontend   # vitest, inside the frontend container
```

Backend tests run against a real PostgreSQL test database (Django's standard `test_<name>`
database), not SQLite — see `docs/ARCHITECTURE.md` for why.

## Other developer commands

```bash
make lint         # ruff (backend) + eslint (frontend)
make format       # ruff format (backend) + prettier (frontend)
make typecheck     # tsc --noEmit (frontend)
make build         # rebuild Docker images + Next.js production build
make migrate       # apply Django migrations
make makemigrations
```

`make seed`, `make sms-dry-run`, and `make reconcile` are defined but not yet backed by real
management commands — they print a note pointing at the stage that implements them (Stage 3,
Stage 11, and Stage 10 respectively), so the documented command surface exists from day one without
pretending unbuilt functionality works.

## Production notes

Not yet documented — production deployment, reverse-proxy routing, managed PostgreSQL, object
storage, and backup/restore procedures are Stage 15 deliverables (`docs/DEPLOYMENT.md`,
`docs/RUNBOOK.md`).

## Troubleshooting

- **`docker compose up` fails on `db` healthcheck** — give Postgres a few more seconds on first
  run (initializing the data directory takes longer than subsequent starts).
- **Backend can't reach the database** — confirm `.env` exists (copied from `.env.example`) and
  `DATABASE_URL` points at `db`, the compose service name, not `localhost`.
- **Frontend shows a blank/errored page** — check `docker compose logs frontend`; a first `npm
  install` inside the container can take a minute before the dev server comes up.
- **Port already in use** — something else on your machine is using 3000, 8000, or 5432; stop it or
  adjust the port mappings in `docker-compose.yml`.

## Documentation map

- `docs/PRODUCT_ASSUMPTIONS.md` — locked MVP scope assumptions.
- `docs/ARCHITECTURE.md` — system design, ADRs.
- `docs/DATA_MODEL.md` — entity reference.
- `docs/STATUS_TRANSITIONS.md` — state machines for every workflow entity.
- `docs/SECURITY.md` — security control checklist.
- `docs/TEST_PLAN.md` — test strategy.
- `docs/BUILD_PROGRESS.md` — stage-by-stage build log and requirement traceability matrix.
