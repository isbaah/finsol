# Loan Management System

A lean, auditable loan management web application: customers request loans, staff draft and send
amortization offers, customers digitally sign, staff record manual disbursements and repayments,
and Hubtel SMS keeps everyone informed. See `claude/CLAUDE_LOAN_MANAGEMENT_SYSTEM_MASTER_PROMPT.md`
for the full product specification and `docs/` for the living architecture/decision record.

No money moves through this application — disbursements and repayments happen outside it (bank /
mobile-money transfer) and are only **recorded** here by staff.

## Project status

Building stage-by-stage per `docs/BUILD_PROGRESS.md`. Currently: **Stage 7 — Admin Review and
Versioned Loan Offers** (Stage 6, Customer Loan Request Workflow, is also complete).

## Prerequisites

- Docker Desktop (or Docker Engine + Compose plugin) — this is the only hard requirement to run
  the stack locally. The backend runs Python 3.13 and the frontend runs Node.js 24 **inside their
  containers**, so you do not need either installed on your host.
- Git.
- `make` (optional). If it isn't available on your machine (e.g. plain Windows without WSL/Git
  Bash `make`), run the `docker compose ...` command inside each Makefile target directly — every
  target is a thin one-line wrapper, see `Makefile`.

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

## Authentication setup

Email/password + Google sign-in via `django-allauth[headless]`, session-cookie based (no auth
token is ever stored in `localStorage`). Email is the sole login identifier; verification is
mandatory before a session becomes fully authenticated.

- Frontend auth pages: `/auth/login`, `/auth/signup`, `/auth/verify-email`,
  `/auth/forgot-password`, `/auth/reset-password`, `/auth/google/callback`.
- Backend JSON API: `/_allauth/browser/v1/...` (allauth headless) and `/accounts/...` (Google's
  OAuth redirect/callback machinery only — no server-rendered account pages, since the project runs
  `HEADLESS_ONLY = True`).
- In local dev, verification/reset emails print to the `backend` container's logs (console email
  backend) — run `docker compose logs backend` after signing up and look for the
  `/auth/verify-email?key=...` link.

### Google OAuth setup

1. Create an OAuth 2.0 Client ID in Google Cloud Console (type: Web application).
2. Authorised redirect URI: `<API_BASE_URL>/accounts/google/login/callback/` (e.g.
   `http://localhost:8000/accounts/google/login/callback/` for local dev).
3. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env` — never hard-coded, and `.env` is
   gitignored.
4. No restart-time validation is required for these two values (unlike `DJANGO_SECRET_KEY` etc. in
   production) — the sign-in button works as soon as they're set and the backend container is
   restarted to pick up the new `.env` values (`docker compose restart backend` or `make dev`).

## Customer profiles and roles

New customers complete their profile (phone number + payout details) at `/onboarding/profile`
before they can do anything else in the app; `GET /api/v1/me/` reports `profile_completed` so the
frontend knows when to redirect there. Payout account numbers are always masked outside the
profile owner's own view — see `docs/BUILD_PROGRESS.md`'s Stage 3 notes for why there is currently
no way to see them unmasked anywhere else (the authorised staff reveal workflow arrives in Stage 9).

Internal staff roles (`LOAN_OFFICER`, `APPROVER`, `FINANCE_OFFICER`, `AUDITOR`, `SUPER_ADMIN`) are
Django Groups, seeded idempotently:

```bash
make seed   # runs manage.py seed_roles
```

Assign a user to a role via Django admin (`/admin/accounts/user/<id>/change/` → Permissions →
Groups) — there is no dedicated frontend role-management screen yet. Business roles are
deliberately independent of Django's `is_staff`/`is_superuser` flags, which only gate the
technical Django admin site.

To create your first admin account with both Django admin access **and** the `SUPER_ADMIN`
business role in one step:

```bash
make createsuperuser   # prompts interactively, or override ADMIN_EMAIL/ADMIN_PASS on the CLI
```

Plain `python manage.py createsuperuser` only grants Django's technical `is_superuser`/`is_staff`
flags — it does **not** add the user to `SUPER_ADMIN`, so it alone can't call any
`has_any_role(*STAFF_ROLES)`-gated business endpoint. `make createsuperuser` runs
`manage.py create_super_admin`, which does both.

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

`make seed` now runs `seed_roles` (see "Customer profiles and roles" above). `make sms-dry-run` and
`make reconcile` are still defined but not yet backed by real management commands — they print a
note pointing at the stage that implements them (Stage 11 and Stage 10 respectively), so the
documented command surface exists from day one without pretending unbuilt functionality works.

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
