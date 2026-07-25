# Build Progress

Source of truth for stage-gated delivery. Updated at the end of every stage. Governing document: `claude/CLAUDE_LOAN_MANAGEMENT_SYSTEM_MASTER_PROMPT.md`.

## Current status: Stage 12 complete — awaiting CONTINUE

---

## Stage 0 — Repository Assessment and Architecture Lock

### Repository inspection findings

- Not a Git repository (`git status` → "not a git repository").
- No existing application code, no package manifests (`package.json`, `pyproject.toml`, etc.), no Docker files.
- The only pre-existing file is the master prompt itself, at `claude/CLAUDE_LOAN_MANAGEMENT_SYSTEM_MASTER_PROMPT.md`. Left untouched, per the "do not overwrite existing useful work" instruction.
- Local toolchain observed (informational, not blocking — see `ARCHITECTURE.md` §13): Git 2.46.2 available; Docker 29.6.1 and Docker Compose v5.3.0 available; local Python is 3.10.11 (spec targets 3.13, satisfied by the Docker image in Stage 1); Node.js/npm not installed on this machine's PATH (also satisfied by the Docker image in Stage 1); no local `psql` (not needed — Postgres runs as a container).
- Conclusion: this is a greenfield build. No existing work needed to be preserved beyond the master prompt document.

### What was done in this stage

- Created `docs/` at the repository root (treating `d:\Projects\Finsol_LMS` itself as the monorepo root — see ADR-005 in `ARCHITECTURE.md`).
- Wrote `docs/PRODUCT_ASSUMPTIONS.md`, `docs/ARCHITECTURE.md` (including 5 ADRs), `docs/DATA_MODEL.md`, `docs/STATUS_TRANSITIONS.md`, `docs/SECURITY.md`, `docs/TEST_PLAN.md`, and this file.
- No application feature code was written — correct for Stage 0, since none existed to preserve and none is due yet.

### Commands run

| Command | Purpose | Result |
|---|---|---|
| `find` / `ls` on repo root | Enumerate existing files | Only `claude/CLAUDE_LOAN_MANAGEMENT_SYSTEM_MASTER_PROMPT.md` found |
| `git status` | Confirm VCS state | Not a git repository |
| `git --version`, `docker --version`, `docker compose version`, `python --version`, `node --version`, `npm --version`, `psql --version` | Environment capability check | See findings above |

No lint/test/build commands were run — there is no application code yet for them to target.

### Files created this stage

- `docs/PRODUCT_ASSUMPTIONS.md`
- `docs/ARCHITECTURE.md`
- `docs/DATA_MODEL.md`
- `docs/STATUS_TRANSITIONS.md`
- `docs/SECURITY.md`
- `docs/TEST_PLAN.md`
- `docs/BUILD_PROGRESS.md` (this file)

### Open decisions (none blocking Stage 0; each is flagged for the stage where it first matters)

| # | Decision | Default recommendation | Must be confirmed before |
|---|---|---|---|
| 1 | Semantics/trigger of `LoanRequest.APPROVED` — listed as a state (Section 11) but has no corresponding endpoint or stage task | Treat as reserved/unused in MVP; request flow goes `CUSTOMER_ACCEPTED` → `CONVERTED_TO_LOAN` directly | Stage 6/7 |
| 2 | `LoanOffer` expiry enforcement mechanism (lazy check vs. scheduled sweep) | Lazy check on any accept/reject/revision action against `offer_expiry_date`; no new scheduled job | Stage 7 |
| 3 | Mechanism for recomputing `Loan.OVERDUE` status | Piggyback on `process_due_sms` (or a sibling command on the same schedule) rather than adding a new scheduler entry | Stage 10/11 |
| 4 | Whether `RepaymentInstallment.WAIVED` needs a dedicated admin UI action in the MVP | Implement the state/service function; no dedicated UI button unless requested | Stage 10 |
| 5 | `AGREEMENT_ACTION_EMAIL` — spec text names two initial addresses (`isbaah@gmail.com` and `isbaahjnr@gmail.com`) but Section 18/28 model a single configurable value | Confirm whether this is one config value holding a comma-separated list, or the system should support multiple recipient addresses natively | Stage 8 |
| 6 | Placement of `claude/CLAUDE_LOAN_MANAGEMENT_SYSTEM_MASTER_PROMPT.md` — currently under a `claude/` subfolder rather than repo root as the prompt's own instructions ("copy this entire document into Claude Code at the root of the project") suggest | Leave as-is; it is documentation-of-intent, not part of the shipped repo tree, so its location doesn't affect the build | Not blocking; revisit only if the user wants it moved |
| 7 | Whether to `git init` this repository now or at Stage 1 | Defer to Stage 1 ("Project Foundation"), where CI and Docker tooling are also introduced together | Stage 1 |

None of these block Stage 0 documentation work; all are narrow enough to resolve with a quick confirmation at the point they first matter, per the master prompt's instruction to "ask only a focused question when a decision genuinely blocks the current stage."

### Acceptance criteria check (Section 24, Stage 0)

- [x] Architecture, scope, state machines, and assumptions are documented.
- [x] No application feature code implemented (none was needed to preserve existing work).
- [x] The next stage has a precise plan (see below).

---

## Stage 1 — Project Foundation and Local Development

### Objective

Create a reproducible, healthy monorepo foundation: Django backend with split settings and a
custom UUID user model, Next.js frontend with TypeScript strict mode and Tailwind/shadcn, Docker
Compose for local development, health endpoints, and developer tooling (lint, format, typecheck,
tests, Makefile, CI, README).

### What was built

**Backend** (`backend/`):

- Django 5.2.16 project with split settings (`config/settings/{base,local,test,production}.py`).
  `production.py` fails startup (`ImproperlyConfigured`) if `DJANGO_SECRET_KEY`,
  `DJANGO_ALLOWED_HOSTS`, or `AGREEMENT_ACTION_EMAIL` are missing, per `docs/SECURITY.md`.
- Custom UUID-PK `User` model (`apps/accounts/models.py`), email as the login identifier. Django
  removed `CIEmailField` (the class the master prompt implicitly assumed via "citext") — case-
  insensitive email uniqueness is instead enforced with a nondeterministic ICU collation
  (`django.contrib.postgres.operations.CreateCollation` + `EmailField(db_collation=...)`), which is
  Django's current documented replacement. Verified with a dedicated test
  (`test_email_uniqueness_is_case_insensitive_at_database_level`).
- DRF + `drf-spectacular` wired up; OpenAPI schema serves at `/api/schema/`, Swagger UI at
  `/api/docs/`.
- `django-cors-headers`, `django-filter` installed and configured with explicit, non-wildcard
  origins.
- `/health/live/` and `/health/ready/` (the latter checks real DB connectivity) in
  `common/api/health.py` — deliberately plain Django views, not DRF, so they carry no auth
  dependency for infrastructure probes.
- Ruff (lint + format) and Pytest/pytest-django configured in `pyproject.toml`.
- Dockerfile: `python:3.13-slim`, non-root `appuser`, `gunicorn` as the production entrypoint,
  container `HEALTHCHECK` against `/health/live/`.
- Only the `accounts` app was created. The other apps listed in the target tree (`customers`,
  `loan_requests`, etc.) are **not** stubbed out yet — creating empty Django apps with no current
  use would be the "speculative abstraction" the master prompt's Section 26 forbids. They're
  created in Stage 3/4 when their models actually exist.
- Dependencies were scoped to what Stage 1 actually needs (Django, DRF, drf-spectacular,
  cors-headers, django-filter, psycopg, dj-database-url, python-dateutil, phonenumbers, gunicorn,
  plus pytest/factory-boy/freezegun/ruff for dev). `django-allauth`, `httpx`, WeasyPrint, and
  Pillow are added in the stages that first use them (Stage 2, Stage 11, Stage 8) rather than
  installed unused now — same phasing principle applied to both backend and frontend.
- Dependency manifest is `requirements.txt` + `requirements-dev.txt` rather than dependencies
  embedded in `pyproject.toml` — a well-justified adaptation from the literal target tree (Section
  7 permits this): it keeps `pyproject.toml` to tool configuration (Ruff, Pytest) and avoids
  packaging a Django project as an installable distribution it was never going to be.

**Frontend** (`frontend/`):

- Next.js 16.2.11 (App Router, Turbopack — stable and default in v16), React 19.2.4, TypeScript
  strict mode, Tailwind CSS v4 (CSS-first config via `@theme`, no `tailwind.config.ts` — this is
  the v4 convention, not an omission).
- **Note for future stages**: this Next.js major version (16) postdates this assistant's training
  data and ships its own `AGENTS.md` flagging exactly that. Breaking changes confirmed while
  building this stage: `next lint` is removed (ESLint CLI used directly, already reflected in
  `package.json`'s `lint` script and `eslint.config.mjs`); `middleware.ts` is renamed `proxy.ts`
  (relevant when Stage 2 adds route-protection middleware — do not name it `middleware.ts`);
  `cookies()`/`headers()`/`params`/`searchParams` are async-only now (no sync fallback). Consult
  `frontend/node_modules/next/dist/docs/` before writing code in later stages, not prior
  knowledge.
- shadcn/ui initialized (`components.json`, `style: base-nova`, base color neutral). This version
  of the shadcn CLI generates components on **Base UI** primitives (`@base-ui/react`), not Radix —
  the `Button` component uses a `render` prop for polymorphic rendering (e.g.
  `<Button render={<Link .../>} />`), not the classic `asChild` + child-element pattern. Relevant
  for every future shadcn component added.
- Design tokens extended in `src/app/globals.css`: shadcn's neutral base theme, with `--primary`
  overridden to a corporate blue and `--success`/`--warning` tokens added alongside the existing
  `--destructive`, matching the master prompt's Section 16 palette rules (blue accent; green/amber/
  red reserved for status, never the only signal).
- Route groups created: `(auth)/login`, `(customer)/dashboard` (→ `/dashboard`),
  `(admin)/admin/dashboard` (→ `/admin/dashboard`), `api/health`. Route groups themselves don't
  add a URL segment, so the two dashboards would have collided at the same `/dashboard` path if
  both were placed directly under their group — the admin route was given an explicit `/admin`
  prefix to resolve this and to give Stage 2's route-protection `proxy.ts` a clean path prefix to
  match against later.
- ESLint (flat config, Next.js core-web-vitals + TypeScript), Prettier (with
  `prettier-plugin-tailwindcss` for class sorting), Vitest + React Testing Library, Playwright
  configured. One smoke test in each: `src/app/page.test.tsx` (Vitest) and `e2e/smoke.spec.ts`
  (Playwright).
- `next.config.ts` sets `output: "standalone"` for the production Docker stage.
- Multi-stage `Dockerfile`: `dev` (used by docker-compose, hot reload via bind mount), `deps` /
  `builder` / `runner` (minimal production image, not yet wired into docker-compose — that's a
  Stage 15 deployment concern).

**Infrastructure** (repo root):

- `docker-compose.yml`: `db` (`postgres:17-alpine`, health-checked), `backend` (migrates then runs
  `manage.py runserver`, bind-mounted for hot reload), `frontend` (`npm run dev`, bind-mounted,
  `node_modules`/`.next` in named volumes so the container's Linux-native install isn't shadowed
  by the host mount).
- `.env.example` at the repo root with the full Section 28 variable set, safe placeholders only.
- `Makefile` with all documented targets (Section 23). `seed`, `sms-dry-run`, and `reconcile`
  print a note pointing at the stage that implements them (3, 11, 10) rather than being wired to
  commands that don't exist yet.
- `.github/workflows/ci.yml`: separate `backend` (ruff, pytest against a real Postgres service
  container) and `frontend` (eslint, tsc, vitest, next build) jobs. Playwright is not yet in CI —
  see "Known limitations" below.
- Git repository initialized (`git init -b main`) resolving Stage 0's open decision #7. **No
  commit was made** — commits are only created when explicitly instructed.

### Commands actually run, with results

| Command | Result |
|---|---|
| `docker compose build backend` | Success |
| `docker compose up -d db` (waited for healthy) | Healthy in ~16s |
| `python manage.py makemigrations accounts` | Generated `0001_initial`; hand-added the `CreateCollation` operation (see note above — `makemigrations` doesn't auto-generate it for `db_collation` fields) |
| `python manage.py migrate` against a **clean** database | All migrations applied cleanly, including `accounts.0001_initial` |
| `ruff check .` | All checks passed |
| `ruff format --check .` → `ruff format .` → recheck | 2 files initially needed formatting (`production.py`, `manage.py`); reformatted, recheck clean |
| `pytest -v` (explicit `DJANGO_SETTINGS_MODULE=config.settings.test`) | **6/6 passed** — 2 health-endpoint tests, 4 accounts/User model tests (incl. case-insensitive email uniqueness and UUID PK) |
| `docker compose build frontend` | Success |
| `npm run lint` | Clean, no errors |
| `npm run typecheck` (`tsc --noEmit`) | Clean — one real error caught and fixed (see below) |
| `npm run test -- --run` (Vitest) | **1/1 passed**, no console warnings after fixes |
| `npm run format:check` → `npm run format` → recheck | 10 files needed formatting; reformatted, recheck clean |
| `npm run build` (`next build`) | Success — one real error caught and fixed (route collision, see below); final route table: `/`, `/_not-found`, `/admin/dashboard`, `/api/health`, `/dashboard`, `/login` |
| `docker compose up -d` (all three services) | `backend` and `frontend` both reported **healthy** immediately |
| `curl http://localhost:8000/health/live/` | `{"status": "ok"}` |
| `curl http://localhost:8000/health/ready/` | `{"status": "ok", "database": "up"}` |
| `curl http://localhost:8000/api/schema/` | Valid OpenAPI 3.0.3 document |
| `curl http://localhost:3000/` | Correct `<title>Loan Management System</title>` |
| `curl http://localhost:3000/api/health`, `/dashboard`, `/admin/dashboard`, `/login` | All respond with expected content |

Two real bugs were caught and fixed by actually running these checks (not just writing code):

1. **`tsc` failure**: the generated shadcn `Button` component doesn't support the classic `asChild`
   prop (this shadcn/Next version renders on Base UI, not Radix) — fixed by switching to Base UI's
   `render` prop, and set `nativeButton={false}` since the rendered element is a link, not a
   button (Base UI warns about this at runtime otherwise).
2. **`next build` failure**: `(admin)/dashboard` and `(customer)/dashboard` both resolved to the
   same `/dashboard` URL, because route groups don't add a path segment. Fixed by moving the admin
   route to `(admin)/admin/dashboard` → `/admin/dashboard`.

### Known limitations / deferred items

- **Playwright e2e**: not run inside the frontend's own `alpine`-based Docker image — Playwright's
  bundled Chromium has known compatibility problems on musl/Alpine. Verified instead by running the
  official `mcr.microsoft.com/playwright:v1.61.1-noble` (Debian-based) image against the live
  `docker compose` stack over the compose network: `e2e/smoke.spec.ts` **passed (1/1)**. CI's
  `frontend` job does not yet include an e2e step — worth adding once there's a real user flow to
  test (Stage 2+), using `ubuntu-latest` GitHub runners, which support Playwright natively.
- **`npm audit`**: 6 advisories (3 moderate, 3 high), all in dev-tooling transitive dependencies —
  the `shadcn` CLI's own `@modelcontextprotocol/sdk` → `@hono/node-server` chain (Windows-specific
  path traversal, irrelevant here and never shipped to users), and advisory ranges that list
  `next`'s bundled `postcss`/`sharp` as vulnerable in a version range that includes our installed
  16.2.11 but whose suggested fix is downgrading to `next@9.3.3` — clearly a stale/overly broad
  advisory range, not an actionable fix. Not acted on; revisit properly at Stage 14 (dependency
  vulnerability scanning is an explicit Stage 14 task).
- **`make` itself** could not be executed in this Windows Git-Bash environment (no `make` binary on
  PATH). Every Makefile target was instead verified by running its underlying `docker compose`
  command directly — the targets are intentionally one line each so this is a faithful check. Noted
  in the README for anyone in the same situation.
- Local host tooling is still Python 3.10 / no Node — unchanged from Stage 0, still not a blocker
  since everything runs in Docker and every check above was executed inside the containers.

### Files created this stage

Backend: `backend/{manage.py,pyproject.toml,requirements.txt,requirements-dev.txt,Dockerfile,.dockerignore}`,
`backend/config/**`, `backend/apps/accounts/**`, `backend/common/**` (package skeletons for
`api`, `db`, `money`, `permissions`, `tests`), `backend/integrations/**` (package skeletons for
`hubtel`, `email`, `storage`), `backend/templates/agreements/.gitkeep`, `backend/tests/**`.

Frontend: full `create-next-app` + `shadcn init` output under `frontend/`, plus hand-written
`vitest.config.ts`, `playwright.config.ts`, `.prettierrc.json`, `.prettierignore`, `.dockerignore`,
`Dockerfile`, `src/tests/setup.ts`, `e2e/smoke.spec.ts`, route-group pages, and
`src/app/api/health/route.ts`.

Root: `.gitignore`, `.env.example`, `docker-compose.yml`, `Makefile`, `README.md` (rewritten),
`.github/workflows/ci.yml`. Git repository initialized.

### Acceptance criteria check (Section 24, Stage 1)

- [x] `docker compose up --build` starts the stack (verified via `docker compose build` +
      `docker compose up -d`; all three services healthy).
- [x] Frontend loads (`curl localhost:3000/` returns the expected page, correct title).
- [x] Backend health endpoints work (`/health/live/`, `/health/ready/` both verified).
- [x] Database migrations apply from a clean database (verified against a freshly created
      Postgres volume).
- [x] Backend tests pass (6/6, `pytest`).
- [x] Frontend tests, lint, typecheck, and production build pass (Vitest 1/1, ESLint clean, `tsc`
      clean, `next build` clean).

### Open decisions carried over from Stage 0

Decision #7 (git init timing) is now resolved — done this stage. Decisions #1–6 are unchanged and
still apply to their originally identified stages (6/7, 7, 10/11, 10, 8) — see the Stage 0 table
above.

---

## Stage 2 — Authentication, Email Verification, and Google Login

### Objective

Implement secure browser authentication: django-allauth headless browser flows, mandatory email
verification, Google OAuth, frontend session discovery, route protection for the customer/admin
groups, CSRF-safe API calls, a user menu, and session-expired handling.

### Research performed before implementing

`django-allauth` 65.18.0 (current stable, compatible with Django 5.2) postdates this assistant's
training data by enough that several APIs differ from what training data would suggest —
consistent with the Next.js 16 surprise in Stage 1. Rather than guess, the installed package's
source was downloaded and read directly (`allauth/headless/{urls,constants,app_settings}.py`,
`allauth/headless/account/{views,inputs}.py`, `allauth/headless/socialaccount/views.py`,
`allauth/account/app_settings.py`, `allauth/account/middleware.py`, `allauth/urls.py`, and the
bundled `allauth/headless/spec/doc/description.md`, which is effectively django-allauth's own API
reference shipped in the wheel). Findings that materially shaped the implementation:

- **`CIEmailField` is gone.** Django itself removed it; the documented replacement is a
  nondeterministic ICU collation via `django.contrib.postgres.operations.CreateCollation` — already
  adopted for the `User` model in Stage 1, so no rework was needed here, but it's the same pattern
  allauth's own docs point at for case-insensitive lookups elsewhere.
- **`ACCOUNT_USER_MODEL_USERNAME_FIELD` must be `None`** for a user model with no `username` column
  at all — without it, allauth's signup form still tries to introspect a `username` field on the
  model and crashes with `FieldDoesNotExist`. Not something the standard "custom user model" allauth
  guides mention if you never had a username field to begin with.
- **`ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION` and `ACCOUNT_LOGIN_ON_PASSWORD_RESET` both default to
  `False`.** Left alone, verifying an email or resetting a password leaves the user "successful but
  logged out" — the API responds 200 for the action itself but `meta.is_authenticated` stays
  `false`, and the user has to separately log in with credentials they just proved they control.
  Both were explicitly set to `True` (see `config/settings/base.py`) — a deliberate UX decision, not
  a default we happened to keep.
- **The headless response envelope is `{status, data?, meta?, errors?}`**, and a 401 is a *normal*
  outcome for allauth's own endpoints (not-yet-authenticated, pending email verification, wrong
  password all surface as 401/400 with structured `errors`/`flows`, not thrown exceptions) — this
  shaped `features/auth/api.ts`'s `allauthFetch` to never throw on 4xx, unlike `lib/api-client.ts`'s
  `apiFetch` for our own `/api/v1/...` endpoints, where a non-2xx is a genuine error.
- **Signup with an already-registered email doesn't return a "taken" error.** It silently behaves
  like a fresh pending signup (401, `verify_email` pending, no second `User` row created) — allauth's
  built-in anti-enumeration protection. This also turned out to be the *only* way to resend a lost
  verification email in link-based mode: `/auth/email/verify/resend` is code-mode only
  (`ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED`, which this project doesn't use) and returns 409
  otherwise. Documented inline in `backend/tests/test_auth.py`.
- **A password-reset request for an unknown email still sends an email** — an "Unknown Account"
  notice to that address — while returning the exact same 200 response as the known-email case. The
  non-leaking property is "the HTTP response is indistinguishable," not "nothing happens."
- **`RedirectToProviderView` (the Google sign-in entry point) takes a form-encoded POST, not JSON**,
  and responds with an HTTP redirect the browser must follow to `accounts.google.com` — impossible
  to drive with `fetch()`. `GoogleSignInButton` is therefore a real `<form method="POST">`, with the
  CSRF token carried as a `csrfmiddlewaretoken` form field rather than an `X-CSRFToken` header.
- **`browser_view`-decorated endpoints enforce normal Django CSRF** (only the token-based `app`
  client is `csrf_exempt`), and proactively call `get_token()` so the CSRF cookie gets set on the
  very first `GET /auth/session` call — which is why session discovery on app load also happens to
  prime CSRF for every subsequent POST.
- **`allauth.urls` only ever contains the social-provider callback routes when `HEADLESS_ONLY =
  True`** (the account/socialaccount server-rendered views are stripped out entirely) — confirms it's
  safe and correct to mount both `path("accounts/", include("allauth.urls"))` (Google's OAuth
  callback machinery) and `path("_allauth/", include("allauth.headless.urls"))` (the JSON API) side
  by side, matching the master prompt's own architecture diagram.

### What was built

**Backend**:

- `django-allauth[headless]==65.18.0` + `requests==2.34.2` (a Google-provider transitive dependency
  not pulled in automatically by the `[headless]` extra).
- `config/settings/base.py`: `allauth`, `allauth.account`, `allauth.socialaccount`,
  `allauth.socialaccount.providers.google`, `allauth.headless` in `INSTALLED_APPS`;
  `allauth.account.middleware.AccountMiddleware`; `AUTHENTICATION_BACKENDS`; `HEADLESS_ONLY = True`,
  `HEADLESS_CLIENTS = ["browser"]` (no token/`app` client — Section 9 forbids storing an auth token
  anywhere in the browser, and there's no native app to justify one); `HEADLESS_FRONTEND_URLS`
  pointing verification/reset links at the Next.js frontend; `ACCOUNT_LOGIN_METHODS = {"email"}`;
  mandatory email verification; Google `SOCIALACCOUNT_PROVIDERS` from `GOOGLE_CLIENT_ID`/
  `GOOGLE_CLIENT_SECRET` env vars (never hard-coded). No `django.contrib.sites` — confirmed
  optional (`SITES_ENABLED` auto-detects from `INSTALLED_APPS`), so provider credentials live purely
  in settings rather than a DB-stored `SocialApp` row tied to a `Site`.
- `common/api/authentication.py`: a one-method override of DRF's `SessionAuthentication` so
  unauthenticated requests return 401, not DRF's default 403 (which conflates "not authenticated"
  with "authenticated but forbidden" because plain `SessionAuthentication` never sets
  `WWW-Authenticate`). Section 14: "Return consistent JSON error objects."
- `apps/accounts/{urls,views,serializers}.py`: `GET /api/v1/me/`, the first versioned business
  endpoint, doubling as the "protected API access" and "session discovery" proof point for this
  stage. Deliberately minimal (id/email/name/staff/date_joined) — role and profile fields arrive in
  Stage 3 once they exist, rather than being guessed at now.
- `config/urls.py`: `accounts/` (allauth's Google callback machinery), `_allauth/` (the headless JSON
  API), `api/v1/` (our own endpoints).
- `config/settings/production.py`: fails startup if `EMAIL_BACKEND` is the SMTP backend and
  `EMAIL_HOST` is unset — verification/reset email is on the authentication critical path.
- `backend/tests/test_auth.py`: 20 tests covering signup (incl. duplicate-email anti-enumeration,
  weak-password rejection), email verification (incl. invalid key), login/logout (incl. wrong
  password, unverified account), protected API access (incl. unverified-but-signed-up), password
  reset (incl. unknown-email non-leaking, invalid key), CSRF rejection, and the Google
  provider-redirect boundary (valid provider → redirects to `accounts.google.com`; invalid provider →
  redirects to our own error page, never to Google).

**Frontend**:

- New dependencies, added because this is the stage that first genuinely needs them (same phasing
  principle as Stage 1): `@tanstack/react-query` (session caching/invalidation), `react-hook-form` +
  `zod` + `@hookform/resolvers` (the auth forms), `sonner` (toast messages, incl. session-expiry).
  Added shadcn `input`, `label`, `checkbox`, `card` components (Base UI-backed, same as `button` from
  Stage 1 — `Checkbox` uses a `checked`/`onCheckedChange` controlled API, wired through
  react-hook-form's `Controller`, not native `register()`).
- `lib/csrf.ts`, `lib/api-client.ts`: CSRF-cookie-aware fetch wrapper for `/api/v1/...` calls, with a
  registrable 401 handler used for session-expiry detection.
- `features/auth/`: `api.ts` (typed wrappers for every headless endpoint used), `types.ts` (the
  envelope shape), `use-session.ts` (TanStack Query-backed `useSession()`), `errors.ts` (maps
  allauth's `{message, code, param}` error list onto react-hook-form field errors).
- `providers/query-provider.tsx`, `providers/session-provider.tsx`: the latter registers the global
  401 handler — a 401 from our *own* API (as opposed to allauth's own endpoints, where 401 is normal
  flow control) means a session this UI believed was valid just stopped being valid, so it's treated
  as a one-shot event: toast, drop the cached session, redirect to `/auth/login`.
- Route fix: pages were placed at `(auth)/login`, `(auth)/signup`, etc. in Stage 1, which actually
  resolve to `/login`, `/signup` (route groups don't add a path segment) — not `/auth/login` as
  Section 9's frontend route list specifies. Moved to `(auth)/auth/login`, `(auth)/auth/signup`, etc.
  this stage so the URLs actually match the spec.
- Pages: `/auth/login`, `/auth/signup`, `/auth/verify-email` (reads `?key=`, auto-submits, shows
  verifying/success/error states), `/auth/forgot-password`, `/auth/reset-password` (reads `?key=`),
  `/auth/google/callback` (lands here after a successful Google round-trip; checks session state and
  routes onward — failures redirect straight to `/auth/login?error=social` instead, per
  `HEADLESS_FRONTEND_URLS`).
- `components/auth/google-sign-in-button.tsx`: a genuine `<form>` POST (see research notes above),
  not a fetch call — the CSRF token and real origin are read post-mount via `useEffect`, not during
  the initial render, so server and client agree on the first paint (`document`/`window` don't exist
  during SSR).
- `src/proxy.ts` (Next.js 16 renamed `middleware.ts` → `proxy.ts` — **do not** recreate a
  `middleware.ts` file in a later stage without checking this first). Matches `/dashboard/:path*` and
  `/admin/:path*`; redirects to `/auth/login?next=...` when the `sessionid` cookie is absent. This is
  a fast UX heuristic (no protected-page flash for obviously logged-out visitors), **not** the actual
  authorization boundary — a present cookie doesn't prove a still-valid session. The backend's own
  401 responses (via `lib/api-client.ts`'s handler) are the authoritative check, consistent with
  Section 10's "critical actions checked in both the API layer and the domain layer" principle
  applied to auth specifically.
- `components/shared/user-menu.tsx`, `(customer)/layout.tsx`, `(admin)/layout.tsx`: minimal header
  chrome (email + sign-out) proving session discovery and sign-out work — full CRM dashboard chrome
  is Stage 12.
- 6 new/updated test files, 16 tests: `lib/csrf.test.ts`, `features/auth/errors.test.ts`,
  `proxy.test.ts` (redirects when no cookie, passes through when present, preserves the `next` path),
  `components/auth/login-form.test.tsx`, `components/auth/signup-form.test.tsx` (mismatched
  passwords, unchecked declaration, pending-verification confirmation state), plus the Stage 1
  homepage test updated for the corrected `/auth/login` link.

### Commands actually run, with results

| Command | Result |
|---|---|
| `python manage.py migrate` (after adding allauth apps) | Applied cleanly — `account`, `socialaccount` migrations alongside `accounts` |
| `python manage.py check` | No issues |
| `pytest -v` (backend, full suite) | **26/26 passed** (20 new auth tests + 6 from Stage 1) |
| `ruff check .` / `ruff format --check .` | Clean |
| `npm run typecheck` | Clean (after fixing one real error — see below) |
| `npm run lint` | Clean (after fixing one real error — see below) |
| `npm run test -- --run` (Vitest) | **16/16 passed** |
| `npm run format:check` | Clean after `npm run format` |
| `npm run build` (`next build`) | Success — all 11 routes generated correctly, `ƒ Proxy (Middleware)` confirmed present |
| `docker compose up -d --build` then live `curl`/cookie-jar session against the **running containers** (not the test DB) | Full signup → email-logged-in-console → extract real key → verify → `GET /api/v1/me/` (200, correct user) → logout → `GET /api/v1/me/` (401) — see below |

Real issues caught by actually running these, not just writing the code:

1. **Zod v4 API drift**: `z.literal(true, { message: "..." })` (valid-looking, v3-shaped) broke the
   declaration checkbox's validation in a way that only showed up as a test failure, not a type
   error. Replaced with `z.boolean().optional()` + an object-level `.refine()` — also surfaced a
   genuine Zod behavior worth knowing: `.refine()` is skipped entirely when the base shape already
   failed, so a required-but-unfilled field can silently suppress an unrelated refine's error message
   if the schema isn't structured to account for it.
2. **Base UI's `Checkbox` renders two label-associated elements** (a visually-hidden native
   `<input>` for form semantics, a styled `<span role="checkbox">` for interaction) — `getByLabelText`
   matches both and fails ambiguously; `getByRole("checkbox")` is the correct query.
3. **DRF's default `SessionAuthentication` returns 403, not 401, for unauthenticated requests** —
   caught by a test expecting 401 and getting 403; fixed properly (see `common/api/authentication.py`
   above) rather than loosening the test to accept either.
4. **A brand-new React Compiler-era ESLint rule (`react-hooks/set-state-in-effect`)** flagged the
   Google button's post-mount `useEffect`. Read the rule's rationale before suppressing it — this
   specific case (reading `document.cookie`/`window.location`, which don't exist during SSR) is one
   of the legitimate exceptions the rule itself is not designed to catch cleanly; addressed with a
   scoped, commented `eslint-disable-next-line`, not a blanket disable.
5. **Named Docker volumes for `node_modules` and `.next` don't update themselves** when the image is
   rebuilt with new dependencies — `docker compose run --rm frontend npm install` (or clearing the
   volume) is required after any `package.json` change, independent of rebuilding the image. Same
   caveat will apply to every future stage that adds a frontend dependency.

### Known limitations / deferred items

- Google OAuth is fully wired end-to-end (redirect construction, callback handling, error path) and
  proven against real Google endpoints for the redirect leg (`test_provider_redirect_is_wired_to_google`
  confirms the actual `accounts.google.com` redirect), but the full consent-screen-and-back
  round-trip was not exercised with real Google credentials (none exist for this project yet, and
  none should be invented) — this is a configuration step for whoever sets up real
  `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`, not a code gap.
- No role-based route protection yet — `proxy.ts` only proves "some authenticated session exists,"
  not "this session is a `CUSTOMER`" vs `LOAN_OFFICER`, etc. Roles don't exist until Stage 3.
- Admin MFA (Section 9: "Admin accounts must be capable of MFA in a later hardening stage") is
  explicitly deferred to Stage 14 per the master prompt's own schedule — not started here.
- No dedicated `/api/API.md` documentation file was created for the new `/api/v1/me/` endpoint or the
  `_allauth/browser/v1/...` surface — `docs/API.md` doesn't exist yet (not a Stage 0–2 deliverable);
  revisit once more endpoints exist and the doc is worth creating.

### Files created/changed this stage

Backend: `requirements.txt` (allauth, requests), `config/settings/{base,test,production}.py`,
`config/urls.py`, `common/api/authentication.py`, `apps/accounts/{urls,views,serializers}.py`,
`tests/test_auth.py`.

Frontend: `package.json` (5 new deps), `src/components/ui/{input,label,checkbox,card}.tsx` (shadcn),
`src/lib/{env,csrf,api-client}.ts` (+ `csrf.test.ts`), `src/features/auth/**`, `src/providers/**`,
`src/schemas/auth.ts`, `src/components/auth/**` (+ tests), `src/components/shared/user-menu.tsx`,
`src/proxy.ts` (+ `proxy.test.ts`), `src/app/(auth)/auth/**` (moved from `src/app/(auth)/**`),
`src/app/(customer)/layout.tsx`, `src/app/(admin)/layout.tsx`, `src/app/layout.tsx`,
`src/app/page.tsx` / `page.test.tsx` (link fix).

### Acceptance criteria check (Section 24, Stage 2)

- [x] Verified email users can sign in (proven both by `pytest` and a live cookie-jar session
      against the running stack).
- [x] Google sign-in flow is correctly wired from configuration (redirect to `accounts.google.com`
      confirmed; full consent round-trip needs real credentials, see limitations above).
- [x] Unverified password users cannot submit protected business actions (`/api/v1/me/` returns 401
      for a signed-up-but-unverified session, both in tests and live).
- [x] No auth token is stored in localStorage (session-cookie only; `HEADLESS_CLIENTS = ["browser"]`
      means the token-based `app` client doesn't even exist on this backend).

### Open decisions carried over from Stage 0

Unchanged — decisions #1–6 still apply to their originally identified stages (6/7, 7, 10/11, 10, 8).

---

## Stage 3 — Customer Profile, Staff Roles, and Permissions

### Objective

Create secure user profiles and business roles, per Section 24's Stage 3 scope and Section 10's
role/permission model.

### What was built

**`common/` groundwork, used immediately (not speculative):**

- `common/db/models.py` — `BaseModel` abstract base (UUID PK + `created_at`/`updated_at`), the
  Section 12 pattern every domain model needs from here through Stage 4.
- `common/permissions/roles.py` — the five internal role constants
  (`LOAN_OFFICER`/`APPROVER`/`FINANCE_OFFICER`/`AUDITOR`/`SUPER_ADMIN`), `user_has_any_role()`,
  the `has_any_role(*roles)` DRF permission-class factory, and `IsOwner` (object-level ownership
  check). Re-exported from `common/permissions/__init__.py`.
- `common/masking.py` — `mask_tail()`, a small display-masking helper for account identifiers.

**Business roles:**

- `apps/accounts/management/commands/seed_roles.py` — idempotent `python manage.py seed_roles`,
  creates the five Django Groups via `get_or_create`. `CUSTOMER` is **not** a Group — it's modelled
  as "authenticated and holds none of the five staff roles" (see Design decisions below).
- `make seed` now actually runs it (was a placeholder through Stage 2).
- Role assignment itself uses the existing Django admin (`UserAdmin`'s `groups` field, already
  present since Stage 2) — satisfies Section 24's "for super administrators **or** controlled
  Django admin support" without building a bespoke frontend role-management screen this stage.

**`apps/customers` (new app):**

- `CustomerProfile` model — one-to-one with `User`, all fields from Section 12.2 (E.164 phone +
  country code, optional address/city, `country` defaulting `GH`, `preferred_disbursement_method`,
  conditional mobile-money/bank fields, `profile_completed_at`). A `CheckConstraint` enforces that
  once `profile_completed_at` is set, the fields required by the chosen payout method are actually
  present — DB-level, not just serializer-level (Section 26).
- `CustomerProfileSerializer` (full, unmasked — used only for the profile owner's own view) and
  `MaskedCustomerProfileSerializer` (staff-facing, payout numbers always masked via `mask_tail()`).
  Phone normalization via `phonenumbers` (region hint `GH`).
- `MyProfileView` (`GET`/`PUT /api/v1/profile/`) — no `pk` in the URL, so the only object reachable
  is always the caller's own profile (ownership isolation by construction); `IsOwner` is still
  applied as a defense-in-depth check per Section 10. `PUT` both creates (onboarding) and replaces
  (later edits) — there's no partial-update endpoint, since the form always resubmits the whole
  profile.
- `CustomerListView`/`CustomerDetailView` (`GET /api/v1/customers/`, `GET /api/v1/customers/<uuid>/`)
  — staff-only (`has_any_role(*STAFF_ROLES)`), masked.
- `CustomerProfileAdmin` — read-safe technical-support Django admin view.

**`/api/v1/me/` extended** (`apps/accounts/serializers.py`) with `roles` (group names),
`is_customer`, and `profile_completed` — lets the frontend decide, right after login, whether to
route a customer through `/onboarding/profile`.

**Frontend:**

- `features/me/` — `Me` type, `getMe()`, `useMe()` (TanStack Query, `retry: false` since a 401 here
  is already handled by the global unauthorized handler and shouldn't retry into three duplicate
  toasts).
- `features/profile/` — `CustomerProfile`/`ProfilePayload` types, `getMyProfile()` (maps a 404 to
  `null`, not a thrown error), `saveMyProfile()`, `useMyProfile()`/`useSaveProfile()`.
- `features/customers/` — staff-side `listCustomers()`/`useCustomers()` against the masked list
  endpoint.
- `schemas/profile.ts` — `profileSchema`, field names kept snake_case (matching the API 1:1) rather
  than the auth forms' camelCase, so `lib/drf-errors.ts`'s `applyDrfErrors()` can attach a server
  validation error straight to the right field with no translation table.
- `components/profile/profile-form.tsx` — the onboarding/edit form; conditional mobile-money vs.
  bank fields, declaration checkbox (same Zod-shape-must-stay-permissive pattern as Stage 2's
  signup form — see Design decisions).
- `components/ui/select.tsx` — a plain native `<select>` styled like `Input`, not Base UI's Select
  primitive (registers directly with react-hook-form, no `Controller` needed, no accessibility
  quirks to work around).
- `components/shared/customer-area-guard.tsx` / `staff-area-guard.tsx` — client-side redirects: a
  customer with an incomplete profile is sent to `/onboarding/profile`; staff and customers are
  each redirected out of the other's route group. **UX convenience only** — real enforcement is the
  backend's `has_any_role()`/ownership checks (Section 26: "Never rely on hiding a frontend button
  as authorisation").
- `app/(customer)/onboarding/profile/page.tsx`, `app/(admin)/admin/customers/page.tsx` (staff
  customer directory — hand-rolled table, no `shadcn` Table component pulled in for one page).
- `proxy.ts` matcher extended to cover `/onboarding/:path*` (was missing — an unauthenticated visit
  would otherwise reach the onboarding page unchallenged at the edge, though `useMe()`/`apiFetch`
  would still 401 it client-side).

### Design decisions

1. **The authorised payout-detail reveal endpoint is deferred, not built partially.** Section 24
   says "implement... only if necessary". There is currently no consumer for it — the disbursement
   workflow that's the *only* authorised reveal context doesn't exist until Stage 9, and it needs
   to log to the `AuditEvent` model that doesn't exist until Stage 4. Building a reveal endpoint now
   would mean either leaving it unreachable (dead code) or granting it to some role prematurely, and
   any throwaway audit-logging table built to unblock it now would just be replaced by Stage 4's
   real `AuditEvent`. Instead, masking is unconditional: **no staff endpoint, for any role including
   SUPER_ADMIN, currently returns an unmasked payout number.** `TestMaskingAndUnauthorisedReveal` in
   `apps/customers/tests/test_api.py` proves this directly, including a check that no query
   parameter bypasses it. Full exposure only becomes possible when Stage 9 adds it deliberately,
   audited.
2. **`is_superuser` never satisfies a business role check.** Section 10 explicitly separates Django
   technical superuser status from business `SUPER_ADMIN`. `common/permissions/roles.py`'s
   `user_has_any_role()` has no `is_superuser` shortcut — proven by
   `test_django_superuser_without_a_business_role_is_still_rejected`. A technical admin must also be
   added to the `SUPER_ADMIN` group to use business staff endpoints.
3. **`CustomerProfile` has no reachable "empty draft" state through the API.** The onboarding form
   always submits the complete profile in one `PUT`; there is no partial-save endpoint. The model's
   `CheckConstraint` still tolerates an incomplete row when `profile_completed_at IS NULL`, purely so
   a future partial-save feature wouldn't need a migration to be allowed — but nothing in the API
   creates one today (`apps/customers/tests/test_models.py` exercises both constraint branches
   directly at the model level, since the API can't).
4. **Mobile money network options are a locked assumption, not in the master prompt.** Ghana's three
   networks (MTN, Telecel — the 2023 Vodafone Ghana rebrand, AirtelTigo) plus `OTHER`, matching
   `docs/PRODUCT_ASSUMPTIONS.md`'s single-country (`GH`) MVP scope. `country` stays a real, editable
   model field (not hard-coded) so a later multi-country expansion doesn't need a schema change, but
   the onboarding UI doesn't expose a country picker.
5. **`phone_number_e164` is never masked, unlike the payout account numbers.** It's a contact
   channel staff legitimately need (to call/SMS the customer), not a payout account identifier —
   Section 12.2's masking requirement is scoped to "account details".
6. **Frontend Zod gotcha, same root cause as Stage 2's declaration checkbox, different shape:** the
   mobile-money-network `<select>` stays mounted and registered with react-hook-form even while the
   BANK branch is displayed (React removes it from the DOM, but the last-read value survives in form
   state), and its placeholder option's value is `""` — not `undefined`. A first attempt at
   `z.enum([...]).optional()` rejects `""` outright, which meant switching to BANK and filling every
   bank field correctly still failed submission, because the *hidden, irrelevant* mobile-money field
   failed the base object shape before `superRefine` even needed to look at it. Fixed by loosening
   the base-shape type to a plain `z.string().optional()` and pushing the real enum-membership check
   into `superRefine`, where it's only evaluated when the method is actually `MOBILE_MONEY` — the
   same "keep the base shape permissive, do real validation in refine" lesson from Stage 2, applied
   to a field-level type instead of a whole-object one. Caught by
   `profile-form.test.tsx`'s bank-branch submission test, which genuinely failed until this was
   fixed (not a pre-written assertion that happened to pass).
7. **`react-hook-form`'s `watch()` vs. `useWatch()`:** using the form-level `watch()` function to
   drive the conditional mobile-money/bank fields triggers an ESLint
   `react-hooks/incompatible-library` warning — the React Compiler can't safely memoize a component
   around a plain function `watch()` returns. Switched to `useWatch({ control, name: ... })`, a
   normal subscribed hook value, which the compiler handles correctly. No `eslint-disable` needed
   here (contrast with Stage 2's Google button, where disabling was the right call because
   restructuring would have caused an actual hydration mismatch — this one had a real fix).

### Commands actually run, with results

```
docker compose exec backend python manage.py makemigrations customers
  → Migrations for 'customers': + Create model CustomerProfile

docker compose exec backend ruff check .          → All checks passed!
docker compose exec backend ruff format --check .  → 51 files already formatted

docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.test backend python manage.py migrate
  → Applying customers.0001_initial... OK

docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.test backend pytest -q
  → 59 passed (26 carried over from Stage 1–2, 33 new)

docker compose exec backend python manage.py makemigrations --check --dry-run  → No changes detected
docker compose exec backend python manage.py check                             → 0 issues

docker compose exec backend python manage.py seed_roles   (run twice)
  → first run: Created × 5; second run: Already exists × 5 (idempotency proven live, not just in a test)

docker compose exec frontend npm run lint        → clean (after fixing two warnings, see Design decision 7)
docker compose exec frontend npm run typecheck   → clean
docker compose exec frontend npm run test        → 24 passed (14 carried over, 10 new)
docker compose exec frontend npm run build       → succeeded; route list includes /onboarding/profile
                                                     and /admin/customers
```

**Live end-to-end verification against the running Docker stack** (not just the test databases):
signed up a real customer via curl, verified via the console-logged email link (same technique as
Stage 2), confirmed `GET /api/v1/profile/` → 404 before onboarding, `PUT` a valid mobile-money
profile → 201 with `phone_number_e164` correctly normalized to `+233241234567` and
`profile_completed_at` set, then confirmed `/api/v1/me/`'s `profile_completed` flipped to `true`.
Created a second user via `manage.py shell`, added them to the `LOAN_OFFICER` group, logged in, and
confirmed `GET /api/v1/customers/` returns the first customer's profile with
`mobile_money_number: "•••• 4567"` — masked — while the plain customer gets `403` on the same
endpoint. On the frontend: `/onboarding/profile` initially 404'd on first request after adding the
file — a stale Turbopack dev-server file watch, not a code bug (same class of Docker-bind-mount
dev-server quirk noted in Stage 1/2, worth remembering for future stages) — resolved by
`docker compose restart frontend`, after which both `/onboarding/profile` and `/admin/customers`
correctly 307-redirected an unauthenticated request to `/auth/login`, and rendered their real shells
for the customer/officer session cookies obtained above. Test data (`stage3.customer@example.com`,
`stage3.officer@example.com`) was deleted afterward.

### Known limitations / deferred items

- No authorised payout-detail reveal endpoint yet — deferred to Stage 9 by design (Design decision 1).
- No dedicated frontend role-management UI — role assignment is via Django admin only this stage
  (Design decision, satisfies Section 24's "or controlled Django admin support" wording).
- `CustomerProfile` has no partial-save/draft capability — one-shot onboarding only (Design decision 3).
- The admin Customers page has no pagination controls, search, or filtering yet — `DEFAULT_PAGINATION_CLASS`
  already paginates the API (`PAGE_SIZE = 20`), but the page only renders `results`, not `next`/`previous`.
  Deferred to whichever later stage first needs a paginated staff table (Stage 6/7's request/offer
  lists are the more natural place to build that UI pattern once, reusably).
- `CustomerAreaGuard`/`StaffAreaGuard` are plain redirect components, not a shared generic — kept
  deliberately separate/small rather than building a configurable "AreaGuard" abstraction for two
  call sites.

### Files created/changed this stage

**Backend:** `common/db/models.py`, `common/permissions/roles.py`, `common/permissions/__init__.py`,
`common/masking.py`, `common/tests/test_masking.py`, `apps/customers/{apps,models,serializers,views,urls,admin}.py`,
`apps/customers/migrations/0001_initial.py`, `apps/customers/tests/{test_models,test_api}.py`,
`apps/accounts/management/commands/seed_roles.py`, `apps/accounts/serializers.py` (extended),
`apps/accounts/tests.py` (extended), `config/settings/base.py` (`LOCAL_APPS`), `config/urls.py`
(customers routes), `Makefile` (`seed` target).

**Frontend:** `features/me/{types,api,use-me}.ts`, `features/profile/{types,api,use-profile}.ts`,
`features/customers/{types,api,use-customers}.ts`, `schemas/profile.ts`, `schemas/profile.test.ts`,
`lib/drf-errors.ts`, `components/ui/select.tsx`, `components/profile/profile-form.tsx` (+ test),
`components/shared/{customer-area-guard,staff-area-guard}.tsx`,
`app/(customer)/onboarding/profile/page.tsx`, `app/(admin)/admin/customers/page.tsx`,
`app/(customer)/layout.tsx` / `app/(admin)/layout.tsx` (guards wired in), `proxy.ts` (matcher).

### Acceptance criteria check (Section 24, Stage 3)

- [x] A customer can complete a valid profile — proven live (curl round trip) and by
      `TestProfileValidation`/`profile-form.test.tsx`.
- [x] Staff roles enforce the documented matrix — `TestRoleMatrix` (all five roles + rejection of
      plain customers and non-role superusers), proven live for `LOAN_OFFICER`.
- [x] Sensitive payout data is masked outside authorised workflows — unconditionally masked
      everywhere right now, since no authorised workflow exists yet (Design decision 1).

### Open decisions carried over from Stage 0

Unchanged — decisions #1–6 still apply to their originally identified stages (6/7, 7, 10/11, 10, 8).

---

## Stage 4 — Core Domain Models and State Transition Services

### Objective

Build the auditable domain foundation — every entity in `docs/DATA_MODEL.md` — before any
UI-heavy feature is built on top of it. Per Section 24, this stage delivers models, constraints,
number generators, and transition services only; no new REST endpoints or frontend UI (those
arrive per-workflow in Stages 6–10).

### What was built

**Seven new Django apps**, exactly matching the app boundaries locked in `docs/ARCHITECTURE.md`
Section 4: `apps/audit`, `apps/loan_requests`, `apps/loan_offers`, `apps/agreements`, `apps/loans`,
`apps/repayments`, `apps/messaging`. Plus two small additions to existing infrastructure:

- `common/domain.py` — `apply_transition()` + `InvalidTransitionError`, a single shared guard used
  by every app's transition service (validate current status is in `allowed_from`, raise a
  domain-specific error otherwise). Callers still own their own `transaction.atomic()` +
  `select_for_update()` — this only validates and applies, so callers can update other fields and
  write an audit event in the same operation.
- `common.models.NumberSequence` (`common` promoted to a real installed app for this one table) +
  `common/db/sequences.py::next_reference_number()` — the race-condition-safe generator behind
  `request_number`, `loan_number`, and `receipt_number`. A `(scope, period)` counter row,
  incremented under `select_for_update()` inside its own nested transaction. Format:
  `PREFIX-YYYY-NNNNNN` (e.g. `REQ-2026-000001`).

**`apps/audit`** — `AuditEvent` (append-only; `save()`/`delete()` raise on any update/delete
attempt) and `record_event()` + `redact()` in `services.py`. Every transition service across every
other app calls `record_event()` in the same atomic block as the state change itself, so an event
is never written for a change that didn't happen and vice versa. `redact()` strips any dict value
whose key matches a sensitive fragment (`password`, `secret`, `token`, `session`,
`mobile_money_number`, `bank_account_number`, `signature`, `credential`) recursively, at any
nesting depth — proven directly in tests, not just trusted by convention.

**`apps/loan_requests`** — `LoanRequest` model (all Section 12.3 fields) + `services.py`
implementing every transition in `docs/STATUS_TRANSITIONS.md` Section 1: `create_loan_request`
(creates directly in `SUBMITTED`), `start_review`, `decline`, `cancel`, `mark_offer_sent`,
`mark_customer_accepted`/`_rejected`, `mark_revision_requested`, `mark_back_under_review`,
`mark_converted_to_loan`.

**`apps/loan_offers`** — `LoanOffer` + `OfferInstallment` models, plus:

- `apps/loan_offers/amortization.py` — **the Stage 5 calculation engine** (see below); lives here
  because its output directly becomes `OfferInstallment` rows and this is its only real consumer.
- `services.py` — `create_offer_with_schedule()` (atomically creates a new version + its
  installment rows — the one persistence path used by both a real future offer-creation flow and,
  indirectly, the preview endpoint's proof-of-parity test), `send_offer()` (supersedes the
  previously-`SENT` version), `accept_offer()`/`reject_offer()`/`request_revision()` (each with
  lazy expiry enforcement — see Design decisions).
- Model-level guarantee: `LoanOffer.save()` refuses to change any financial field
  (`principal`, `interest_rate_percent`, `term_count`, `term_unit`, `first_due_date`,
  `total_interest`, `total_repayable`, `installment_count`) once `status == ACCEPTED` — a real
  code-level immutability guard, not just a documented convention.

**`apps/agreements`** — `Agreement` model only (Section 12.6's shape; signature capture, PDF
generation, and hashing are Stage 8). Immutable after creation except two email-delivery-tracking
fields, which Stage 8's retry action needs to update.

**`apps/loans`** — `Loan`, `RepaymentInstallment`, `Disbursement` models + `services.py`:
`create_loan()` (the only way a `Loan` row is created — atomically alongside the request's
`CONVERTED_TO_LOAN` transition), `approve_loan()`, `cancel_loan()`, `activate_after_disbursement()`
(moves `APPROVED_FOR_DISBURSEMENT` → `DISBURSED` → `ACTIVE` in one atomic step, per Section 3's
"never leaving the loan sitting in `DISBURSED`"), `mark_overdue()`/`mark_current()`,
`mark_paid_off()`, `copy_schedule_from_offer()` (populates `RepaymentInstallment` from the accepted
offer's schedule), `waive_installment()` (implemented per `STATUS_TRANSITIONS.md`'s open decision —
state and service exist, no dedicated UI button in the MVP). `Disbursement` uses a plain FK + a
removable unique constraint, not `OneToOneField`, so a future staged-disbursement feature is a
constraint drop, not a schema rewrite (Section 12.9's explicit forward-compatibility note).

**`apps/repayments`** — `Payment`, `PaymentAllocation`, `LoanTransaction` models +
`services.py`: `post_ledger_entry()` (the one place `Loan.outstanding_balance` is ever mutated —
locks the `Loan` row first), `record_payment()`, `reverse_payment()` (flips status only, never
edits the original amount/date — a brand-new corrective `Payment` is a separate, later action).
`LoanTransaction` is append-only the same way `AuditEvent` is (`save()`/`delete()` raise).

**`apps/messaging`** — `SMSMessage` model only (Section 12.13's shape). Hubtel adapter, template
catalog, and scheduler are Stage 11.

**Read-safe Django admin** registered for every new model — list/search/filter only, no add/change/
delete permission on any of them (transitions only ever go through the service layer, never a raw
admin edit).

### Design decisions

1. **No dedicated LoanOffer "revision requested" state.** Section 11's LoanOffer status list
   (`DRAFT`/`SENT`/`SUPERSEDED`/`ACCEPTED`/`REJECTED`/`EXPIRED`) has nothing matching
   `LoanRequest.REVISION_REQUESTED`. Modelled as the offer transitioning to `REJECTED` (with a
   reason) — `REJECTED`'s own documented semantics ("officer may still create a new offer version
   in response") are exactly a revision request's meaning — while the *request* moves to its own
   `REVISION_REQUESTED` state. See `apps/loan_offers/services.py::request_revision()` and the
   corresponding note added to `docs/STATUS_TRANSITIONS.md`.
2. **`LoanRequest.mark_offer_sent` also accepts `OFFER_SENT` as a source status** (a same-state
   "transition"). Discovered while testing: Section 11 states "sending a revised offer supersedes
   the previous sent offer" without requiring the customer to have acted on the outstanding one
   first (e.g. an officer catching their own typo minutes after sending) — the original
   `{UNDER_REVIEW, REVISION_REQUESTED}`-only `allowed_from` made this legitimate flow impossible.
   Fixed and documented in `docs/STATUS_TRANSITIONS.md`.
3. **Append-only tables enforce it in code, not only by omission.** `AuditEvent` and
   `LoanTransaction` both override `save()`/`delete()` to raise `ValueError` on any attempted
   update or delete, rather than relying solely on "we never built that endpoint" — a second,
   independent guarantee, proven directly in tests (`test_audit_event_cannot_be_updated`,
   `test_loan_transaction_cannot_be_deleted`, etc.).
4. **`_reject_if_expired()`'s expiry flip runs in its own committed transaction, separate from the
   caller's.** First implementation raised `OfferExpiredError` from inside the same
   `transaction.atomic()` block that had just flipped the offer to `EXPIRED` — Django rolls back
   the *whole* block on any exception escaping it, silently undoing the flip along with everything
   else. A real bug, caught by `test_expired_offer_cannot_be_accepted` actually asserting the
   persisted status afterward (not just that the exception was raised) — fixed by giving the
   expiry check its own atomic block that commits before the error is raised.
5. **`MAX_TERM_COUNT = 60`** (weeks or months) — a documented Stage 4 sanity bound, not a
   master-prompt requirement, guarding `LoanOffer` and the Stage 5 calculator against fat-fingered
   input.

### Commands actually run, with results

```
docker compose exec backend python manage.py makemigrations common audit loan_requests loan_offers agreements loans repayments messaging
  → 8 apps, clean (one initial regeneration needed after fixing two CharField null=True →
     blank=True changes broke the already-applied migrations; unapplied, deleted, regenerated —
     no real data existed yet, see Known limitations)

docker compose exec backend python manage.py migrate     → all 8 apps applied cleanly
docker compose exec backend python manage.py check        → 0 issues
docker compose exec backend python manage.py makemigrations --check --dry-run  → No changes detected
docker compose exec backend ruff check . / ruff format .  → clean

docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.test backend pytest -q
  → 140 passed (101 carried over from Stages 1–3, 39 new)
```

**Live verification against the running dev database** (not just the test DB): ran the entire
request → offer → send → accept → loan → approve → disburse/activate → schedule-copy → payment
lifecycle through `manage.py shell`, calling the real service functions end-to-end. Confirmed:
`REQ-2026-000001` → `LN-2026-000001` → `RCT-2026-000001` reference numbers generated correctly;
loan status walked `PENDING_APPROVAL` → `APPROVED_FOR_DISBURSEMENT` → `ACTIVE`; outstanding balance
went `11200.00` → `9333.33` after a `1866.67` payment (exact ledger arithmetic); 12 `AuditEvent`
rows recorded across the chain. Also confirmed `Loan.customer`'s `PROTECT` FK genuinely blocks
deleting a user still referenced by financial records (attempted cleanup of the live-test users
failed with `ProtectedError` listing every referencing model — the invariant working as designed,
so that test data was left in the dev database rather than force-deleted).

**Incidental finding**: `User.objects.filter(email__startswith=...)` raises
`NotSupportedError: nondeterministic collations are not supported for LIKE` against the
nondeterministic ICU collation from Stage 1's case-insensitive email uniqueness. Exact-match
filtering (`email__in`, `email=`) is unaffected. Worth remembering for any future admin search
feature on `User.email` — a `LIKE`/`__contains`/`__startswith` filter will need an explicit
deterministic-collation cast, not a schema change.

### Known limitations / deferred items

- No REST API surface yet for any Stage 4 model — by design; endpoints arrive per-workflow in
  Stages 6 (requests), 7 (offers), 8 (agreements/loan creation), 9 (approval/disbursement), 10
  (repayments).
- `PaymentAllocation` has no populating logic yet — the allocation algorithm (how one payment
  splits across multiple due installments) is a genuine Stage 10 design task, not a Stage 4 gap.
- `Loan.OVERDUE`/`RESTRUCTURED`/`DEFAULTED` recomputation isn't wired to anything yet — the
  transition functions exist and are tested directly; the trigger (a `process_due_sms`-adjacent
  command) is Stage 11.
- `waive_installment()` has no UI — implemented per the documented open decision, Django-admin/
  management-command-only until the product owner asks for a dedicated action.

### Files created/changed this stage

`common/domain.py`, `common/models.py`, `common/db/sequences.py`, `common/apps.py`,
`common/migrations/0001_initial.py`, `apps/{audit,loan_requests,loan_offers,agreements,loans,
repayments,messaging}/{apps,models,admin}.py`, `apps/{audit,loan_requests,loan_offers,loans,
repayments}/services.py`, `apps/*/migrations/0001_initial.py`, `apps/*/tests/test_*.py` (10 new
test files), `tests/factories.py` (shared test factories), `config/settings/base.py` (`LOCAL_APPS`),
`docs/STATUS_TRANSITIONS.md` (Stage 4 resolutions noted inline).

### Acceptance criteria check (Section 24, Stage 4)

- [x] Migrations apply cleanly — proven fresh from an unapplied state, twice (once after the
      CharField fix required regeneration).
- [x] Invalid state transitions are rejected — every transition function tested for both its
      allowed and forbidden source statuses; `InvalidTransitionError` raised, never a silent no-op.
- [x] Core records have database-enforced invariants — `CheckConstraint`s (amounts > 0, term
      bounds, non-negative balances), `UniqueConstraint`s (reference numbers, one disbursement per
      loan, scheduled-reminder de-duplication), append-only guards, and the accepted-offer
      immutability guard are all DB/code-level, not application-convention-only.
- [x] No financial UI is built on an unstable model — no frontend or API work happened this stage;
      Stage 5's calculator and Stage 6+'s workflows are the first things to build on top of it.

### Open decisions carried over from Stage 0

Unchanged except #2: the LoanRequest `APPROVED` reserved/unused status is still correctly unused
(no transition into it exists in any service function written this stage). Decisions #1, #3–6
still apply to their originally identified stages.

---

## Stage 5 — Amortization Engine

### Objective

Implement and prove the authoritative financial calculation engine — the one piece of business
logic every later stage's financial correctness depends on.

### What was built

- `common/money/__init__.py` — `quantize()` (Decimal, `ROUND_HALF_UP`, 2 decimal places) and
  `to_decimal()` (rejects `float` outright, since a float literal already carries binary
  floating-point error before `Decimal()` ever sees it).
- `apps/loan_offers/amortization.py` — `AmortizationInput`/`InstallmentLine`/`AmortizationResult`
  (frozen dataclasses) and `calculate(input) -> AmortizationResult`. Pure and deterministic: no
  HTTP, no database I/O, no Django model imports — verified by the fact its entire test suite
  (23 tests) needs no `@pytest.mark.django_db` at all. Dispatches on `interest_method`, with only
  `FLAT_TOTAL_TERM` implemented (ADR-003) so a second strategy is additive later. Exact residue
  correction: every installment except the last gets an evenly-rounded share; the last absorbs
  whatever's left, guaranteeing `sum(principal_due) == principal`,
  `sum(interest_due) == total_interest`, `sum(total_due) == total_repayable` to the penny, always.
  Due dates are computed independently from `first_due_date` for each installment (never
  cumulatively from the previous one), so a schedule starting on the 31st correctly clips
  per-month (31 → 28/29 → 31 → 30 → 31...) instead of permanently drifting to the 28th once a
  short month is hit.
- `POST /api/v1/admin/offers/preview/` (`apps/loan_offers/views.py`/`serializers.py`/`urls.py`) —
  authorised to `LOAN_OFFICER`/`SUPER_ADMIN` only. Calls the exact same `calculate()` function used
  by `create_offer_with_schedule()`; persists nothing. A dedicated test
  (`test_preview_and_persist_parity.py`) proves this concretely: runs `calculate()`, feeds the
  result into `create_offer_with_schedule()`, and asserts every persisted field matches the
  calculator's output exactly — not just "they use the same function name" but "the numbers are
  provably identical."
- Frontend: `lib/format.ts` (`formatGHS()` — always `GHS 1,234.56`, never a bare symbol per
  `docs/PRODUCT_ASSUMPTIONS.md`; `formatDate()` — unambiguous `24 Sep 2026` form),
  `features/amortization/` (types/api/mutation hook), `schemas/amortization.ts`,
  `components/offers/amortization-preview-form.tsx` (form + formatted totals + schedule table),
  `app/(admin)/admin/offers/preview/page.tsx`.

### Design decisions / bugs caught by actually running things

1. **HTML5 native constraint validation silently blocked form submission.** The term-count
   `<input type="number" min={1} max={60}>` carried real `min`/`max` HTML attributes alongside the
   Zod validation. A value like `0` failed the *browser's own* constraint check, which cancels the
   `submit` event before it ever reaches React — so `handleSubmit`'s callback (valid **or**
   invalid) never fired, no error ever rendered, nothing was ever logged. Consistently reproducible
   (not flaky), and only found by writing two independent minimal reproductions to isolate it: a
   version with plain native inputs and no `min`/`max` worked; adding those two attributes back
   broke it immediately. Fixed by removing the redundant HTML constraint attributes — Zod is
   already the single source of truth for this validation, same as every other field on the form.
2. **`z.coerce.number()` was rejected for the term-count field** in favor of `z.number()` +
   `register(..., { valueAsNumber: true })` — the coerced schema's TypeScript *input* type is
   `unknown`, which broke `useForm`'s generic/resolver typing (the same class of z.infer-vs-z.input
   mismatch as `zodResolver` generally has with `.coerce`/`.transform`). Not worth the type
   gymnastics for one numeric field when RHF's own `valueAsNumber` option does the same job cleanly.

### Commands actually run, with results

```
docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.test backend pytest -q
  → 176 passed (140 carried over from Stage 4, 36 new: 23 calculator + 12 preview API + 1 parity)
docker compose exec backend ruff check . / ruff format --check .  → clean
docker compose exec backend python manage.py check / makemigrations --check --dry-run
  → 0 issues, no changes detected (Stage 5 added no models)

docker compose exec frontend npm run lint / typecheck   → clean
docker compose exec frontend npm run test                → 31 passed (21 carried over, 10 new)
docker compose exec frontend npm run build                → succeeded; /admin/offers/preview in the route list
```

**Live end-to-end verification against the running Docker stack**: continued the Stage 4 shell
lifecycle test through `calculate()` directly (GHS 10,000 / 12% / 6 months → total_interest
1200.00, total_repayable 11200.00, matching the hand-worked example exactly), then called the real
`POST /api/v1/admin/offers/preview/` endpoint via curl as a logged-in `LOAN_OFFICER` and got back
byte-for-byte the same numbers; confirmed `LoanOffer.objects.count()` stayed at 1 (the one real
offer from the Stage 4 lifecycle test) across multiple preview calls, proving no persistence.
Confirmed a plain customer gets `403` on the same endpoint. On the frontend: `/admin/offers/preview`
initially needed a `docker compose restart frontend` to pick up the new route file (same
Turbopack-dev-server-file-watch quirk noted in Stages 1–3 — now a firmly established pattern for
this environment, not a one-off) — after that, an unauthenticated request correctly 307-redirected
to `/auth/login`, and the officer's session rendered the real page shell.

### Known limitations / deferred items

- No real offer-creation UI consumes this yet — Stage 7 builds the actual "create and send an
  offer" admin workflow, which will reuse this same preview form/calculation pipeline for its live
  totals before persisting.
- The preview page has no link from anywhere in the admin UI yet (no sidebar/nav exists until
  Stage 10) — reachable only by direct URL for now, same as Stage 3's admin Customers page.

### Files created/changed this stage

`common/money/__init__.py`, `apps/loan_offers/amortization.py`,
`apps/loan_offers/{serializers,views,urls}.py`, `apps/loan_offers/tests/{test_amortization,
test_preview_api,test_preview_and_persist_parity}.py`, `config/urls.py`, frontend:
`lib/format.ts`, `features/amortization/{types,api,use-amortization-preview}.ts`,
`schemas/amortization.ts` (+ test), `components/offers/amortization-preview-form.tsx` (+ test),
`app/(admin)/admin/offers/preview/page.tsx`.

### Acceptance criteria check (Section 24, Stage 5)

- [x] Schedule totals reconcile exactly — proven for 5+ hand-picked combinations plus a
      parametrized sweep, every time via exact Decimal equality, not approximate/tolerance checks.
- [x] Date edge cases pass — weekly, monthly, Jan-31 progression through a non-leap February,
      leap-year Feb 29 in both directions (as a start date and as a landing date).
- [x] Backend is authoritative — the frontend form only ever displays what the API returns; no
      client-side amortization math exists anywhere in the frontend code.
- [x] Preview and persisted calculations use the same service — proven by direct parity test, not
      asserted by code-reading alone.

### Open decisions carried over from Stage 0

Unchanged — decisions #1–6 still apply to their originally identified stages.

---

## Stage 6 — Customer Loan Request Workflow, and Stage 7 — Admin Review and Versioned Loan Offers

Built together, per explicit instruction, in one implementation-and-report cycle — same combined-stage
exception previously used for Stages 4/5. Reported together below since Stage 7's admin workflow is
the direct continuation of Stage 6's customer submission flow and shares almost every file touched.

### Objective

Give customers a real API/UI to submit and track loan requests (Stage 6), and give loan officers a
real API/UI to review those requests and send back versioned amortization offers built on Stage 5's
calculator (Stage 7) — the first customer-facing and admin-facing features built on Stage 4's domain
models.

### What was built

**Backend — shared infrastructure**

- `common/domain.py` — added a `DomainError` base class; `InvalidTransitionError` now subclasses it.
  This is the first stage where a transition guard is reachable through an API endpoint at all (Stage
  4 built the guards with zero endpoints calling them), so a consistent HTTP mapping was actually
  needed for the first time.
- `common/api/exceptions.py` (new) — a global DRF `EXCEPTION_HANDLER` mapping any `DomainError` to
  `409 Conflict` with `{"detail": ..., "code": "conflict"}`, falling through to DRF's default handler
  otherwise. Wired in `config/settings/base.py`'s `REST_FRAMEWORK["EXCEPTION_HANDLER"]`.
- `common/permissions/roles.py`'s `IsOwner` — generalized to check `obj.customer` as well as
  `obj.user`, since `LoanRequest`/`LoanOffer` are owned via a `customer` FK, not `user`. This is the
  live endpoint integration `IsOwner` was missing per Stage 5's "Recommended next stage" note.
  `apps/loan_offers/models.py::LoanOffer` gained a `customer` *property* (delegating to
  `loan_request.customer`) purely so `IsOwner`'s generic `getattr` check works on it the same way as
  every other owned resource, with no new FK/migration.

**Backend — `apps/loan_requests/`** (Stage 6)

- `serializers.py` — `LoanRequestCreateSerializer` (write; duplicate-submit protection lives in its
  `validate()`), `LoanRequestSerializer` (customer read — never exposes `internal_notes`/
  `assigned_to`; includes a `current_offer` summary computed from the request's `SENT` offer, if any),
  `AdminLoanRequestListSerializer`/`AdminLoanRequestDetailSerializer` (staff read — the detail
  serializer includes the full offer version history), `build_payout_snapshot()` (method + masked
  destination only, never raw account digits).
- `views.py` — `LoanRequestListCreateView` (customer create/list, eligibility-gated),
  `LoanRequestDetailView` (customer detail, `IsOwner`-enforced on an *unscoped* queryset — a real
  cross-customer 403, not just queryset scoping), `LoanRequestCancelView`, and the Stage 7 admin
  views: `AdminLoanRequestListView` (filter/search/order queue), `AdminLoanRequestDetailView`,
  `AdminLoanRequestStartReviewView` (assign + `UNDER_REVIEW` in one call — Stage 4's `start_review()`
  already merges "assignment" and "under-review transition" into one atomic step, so there's no
  separate assign-to-someone-else action in the MVP), `AdminLoanRequestDeclineView`.
- `filters.py` — `LoanRequestFilter` (django-filter `FilterSet`, `status`/`assigned_to`).
- `urls.py` — customer routes under `/api/v1/customer/loan-requests/...`, admin routes under
  `/api/v1/admin/loan-requests/...`, matching the master prompt's Section 14 suggested paths.

**Backend — `apps/loan_offers/`** (Stage 7)

- `services.py` — added `update_draft_offer()` (edits a `DRAFT` offer *in place*, no new version —
  versions are for what's actually been sent, not pre-send edits; raises the new
  `OfferNotEditableError` once the offer leaves `DRAFT`), a `_REQUEST_STATUSES_OPEN_FOR_OFFERS` guard
  in `create_offer_with_schedule()` (raises the new `LoanRequestNotReadyForOfferError` for a request
  that's declined/cancelled/converted/etc. — Stage 4 built this function with no such guard since
  nothing called it yet), and a shared `_replace_installments()` helper used by both create and
  update so the schedule-write path never diverges between them. `send_offer()` now also calls the
  new `messaging.record_offer_ready_sms()` in the same atomic block as the send/supersede.
- `serializers.py` — `OfferWriteSerializer` (subclasses the Stage 5 `AmortizationPreviewRequestSerializer`
  — deliberately the same input shape, since the view always recomputes totals via `calculate()`
  rather than trusting client-submitted numbers), `AdminOfferDetailSerializer` (full, staff-only),
  `CustomerOfferSerializer` (never includes `internal_notes`/`created_by`/`sent_by`).
- `views.py` — `AdminOfferCreateView`, `AdminOfferDetailView` (GET full detail; PATCH only while
  `DRAFT`), `AdminOfferSendView`, `CustomerOfferDetailView` (read-only — see "known limitations"
  below for why there's no accept/reject/revision endpoint yet). A shared `_run_calculation()`
  helper (same `calculate()` call as the Stage 5 preview view) guarantees a persisted or edited
  offer's numbers can never diverge from what an officer saw on screen.
- `urls.py` — `POST /api/v1/admin/loan-requests/{id}/offers/`, `GET`/`PATCH
  /api/v1/admin/offers/{id}/`, `POST /api/v1/admin/offers/{id}/send/`,
  `GET /api/v1/customer/offers/{id}/`.

**Backend — `apps/messaging/services.py`** (new) — `record_sms()` and `record_offer_ready_sms()`.
Writes a `PENDING` `SMSMessage` row only; no provider call anywhere yet (Stage 11's job). This is
Stage 7's "Create `LOAN_OFFER_READY` SMS record and Hubtel boundary placeholder" task, and the first
code in the messaging app besides its Stage 4 models.

**Frontend**

- `features/loan-requests/` (types, api, `use-loan-requests.ts` for the customer side,
  `use-admin-loan-requests.ts` for the admin side, `status.ts` for a shared label/colour-tone map
  per Section 16's "green/amber/red, never colour alone" rule).
- `features/offers/` (types mirroring the new serializers, api, `use-offers.ts` for admin
  create/edit, `use-customer-offer.ts`).
- `schemas/loan-request.ts`, `schemas/offer.ts` — the offer schema reuses the same field set as
  `schemas/amortization.ts` plus the extra offer-only fields.
- `components/ui/textarea.tsx` (new) — purpose/notes fields needed a multi-line input; none existed
  yet, only single-line `Input`.
- `components/requests/` — `loan-request-form.tsx` (+test), `status-badge.tsx`, `status-timeline.tsx`.
- `components/offers/offer-form.tsx` (+test) — one component handles both create (no `offerId`
  prop) and edit (`offerId` supplied) since they're the same fields against the same
  `calculate()`-backed pipeline; shows a "Send offer to customer" action once a draft exists.
- Customer pages: `app/(customer)/requests/{page,new/page,[id]/page}.tsx`,
  `app/(customer)/offers/[id]/page.tsx` (read-only — see limitations), plus the customer dashboard
  now shows the in-flight request's status and a link to its current offer instead of a static
  placeholder.
- Admin pages: `app/(admin)/admin/loan-requests/{page,[id]/page}.tsx` (queue with
  status filter + search; detail page with start-review/decline actions, offer version history, and
  the offer form), plus the admin dashboard now shows a live "new loan requests" count linking to
  the queue — Stage 6's "admin notification indicator inside the dashboard."

### Design decisions

1. **Offer edits before send never bump the version number.** The master prompt's versioning rules
   ("only one offer version can be current," "sending a revised offer supersedes the previous") are
   about what's been *sent* to the customer. A `DRAFT` an officer is still drafting hasn't been shown
   to anyone yet, so editing it in place (via `update_draft_offer()`) rather than minting version 2
   keeps "version" meaning "a proposal that actually reached the customer," and keeps the audit trail
   (`AuditEvent` rows) from accumulating meaningless intermediate versions for every keystroke-level
   correction.
2. **Duplicate-submit protection blocks *in-flight* requests only, not repeat borrowing.** A customer
   with a `DECLINED`/`CANCELLED`/`CUSTOMER_REJECTED` (terminal) prior request can submit again
   immediately — proven live (see below). Blocking a second *simultaneous* request is what "duplicate
   submit" means in Section 24's test list; permanently blocking a returning customer isn't in scope
   and isn't what any stage task asks for.
3. **`update_draft_offer`/`create_offer_with_schedule` never trust client-submitted totals.** The
   write serializer (`OfferWriteSerializer`) only accepts the calculator's *inputs* (principal, rate,
   term, first due date) — never `total_interest`/`total_repayable`/`installments`. The view always
   calls the same `calculate()` Stage 5's preview endpoint uses and persists *that* result, so a
   persisted or edited offer can never be made to disagree with what was actually calculated, closing
   the one gap Stage 5's "preview and persist parity" guarantee left open (preview vs. real creation).
4. **`IsOwner` generalized instead of duplicated.** Rather than writing a second, `LoanRequest`-specific
   ownership permission class, `IsOwner` now checks `obj.customer` as a fallback to `obj.user`, and
   `LoanOffer` got a one-line `customer` property so the exact same permission class works for offers
   too — no new class, no per-model special-casing in views.

### Commands actually run, with results

```
docker compose exec backend python manage.py check                          → 0 issues
docker compose exec backend python manage.py makemigrations --check --dry-run → no changes (no new models this stage)
docker compose exec backend ruff check . / ruff format --check .            → clean
docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.test backend pytest -q
  → 229 passed (176 carried over from Stages 4/5, 53 new: loan_requests API, admin offer API,
    customer offer API, messaging service)

docker compose exec frontend npm run lint / typecheck                        → clean
docker compose exec frontend npm run test                                    → 39 passed (31 carried
    over, 8 new: loan-request-form, offer-form)
docker compose exec frontend npm run build                                   → succeeded; every new
    route present in the output (/requests, /requests/new, /requests/[id], /offers/[id],
    /admin/loan-requests, /admin/loan-requests/[id])
```

**Real bugs caught by actually running the tests** (both fixed):

- `AdminLoanRequestDetailSerializer` declared an `assigned_to_name = SerializerMethodField()` field
  but the matching `get_assigned_to_name()` method was missing entirely — an `AttributeError` on
  every single call to the start-review/decline/admin-detail endpoints. Caught immediately by the
  first test that hit any of those three views.
- `tests/factories.py::make_loan_request()` used a separate `"loan_request_test"` sequence namespace
  from the real `create_loan_request()` service's `"loan_request"` namespace. Both start counting
  from 1 independently, so a test that creates one request via the factory and a second via a real
  API call (exactly what Stage 6/7's API tests do, for the first time — no prior stage mixed the two
  in one test) could get the *same* formatted `request_number` from two different counters and hit
  the real `UniqueConstraint`. Fixed by pointing the factory at the same sequence key as production.
- `django.db.utils.NotSupportedError: nondeterministic collations are not supported for LIKE` — hit
  the moment the admin queue's search filter was first exercised against `customer__email`, exactly
  as Stage 4's "incidental finding" predicted. Fixed with `django.db.models.functions.Collate`,
  re-collating `customer__email` deterministically (`COLLATE "C"`) for the search annotation only —
  no schema change, matching the documented recommendation.
- Reused the pre-existing `AmortizationPreviewFormValues`-style pitfall on a *new* field: an untouched
  optional `requested_term_count` number input produces `NaN` via `valueAsNumber`, which
  `z.number().optional()` does **not** treat as "absent" (only `undefined` is). Fixed the same way
  Stage 5 avoided `.coerce()`'s typing trap — not with `z.preprocess` (which reintroduces the exact
  `z.infer`-vs-input-type mismatch that broke `useForm`'s generic last time) but with
  `register(..., { setValueAs: (v) => (v === "" ? undefined : Number(v)) })`, keeping the schema's
  input type as plain `number | undefined`.

**Live end-to-end verification against the running Docker stack** (via `manage.py shell` for setup,
then real `curl` calls through allauth headless sessions and the actual DRF endpoints — the same
technique used in every prior stage's live verification):

- Two customers (with completed, verified profiles) and one `LOAN_OFFICER` were created. Customer 1
  submitted a request (`REQ-2026-000002`, `201`), immediately got `400` on a second submission
  ("You already have a loan request in progress"), and saw only their own request in `GET
  /api/v1/customer/loan-requests/`. Customer 2 got a real `403` (not just an empty list) requesting
  customer 1's request by ID directly.
- The officer's queue (`GET /api/v1/admin/loan-requests/?status=SUBMITTED&search=REQ-2026-000002`)
  found the request via both the status filter and the search field; `start-review` moved it to
  `UNDER_REVIEW` and assigned the officer in one call; a plain customer got `403` attempting the same
  action.
- The officer created a draft offer (GHS 3,000 / 10% / 6 months → total interest 300.00, total
  repayable 3,300.00 — hand-verified), edited it in place (principal → 3,200 → total repayable
  3,520.00, exact residue correction visible on the last installment: 586.70 vs. 586.66 on the
  others), then sent it. Sending correctly flipped the request to `OFFER_SENT`, and a `PENDING`
  `LOAN_OFFER_READY` `SMSMessage` row was confirmed created with the customer's real phone number
  from their profile.
- Customer 1 then saw `current_offer` populated on their request and could `GET` the full offer +
  schedule at `/api/v1/customer/offers/{id}/` (no `internal_notes`/`created_by` in the response);
  customer 2 got `403` on the same offer.
- Re-sending an already-`SENT` offer, and cancelling a request that's already past `OFFER_SENT`, both
  correctly returned `409 Conflict` (via the new global `DomainError` → 409 handler) instead of a
  500 or a silent no-op. A fresh `SUBMITTED` request was cancelled successfully (`200`,
  `CANCELLED`), and the same customer immediately submitted a new request afterward (`201`) — proving
  duplicate-submit protection only blocks *in-flight* requests, exactly as designed.
- An unauthenticated request to the admin queue got `401`.
- Frontend: `next build`'s route list was confirmed against the live dev server via `curl` for every
  new route (`/requests`, `/requests/new`, `/requests/[id]`, `/offers/[id]`, `/admin/loan-requests`,
  `/admin/loan-requests/[id]`) — `200` for customer pages (client-side guards handle the
  unauthenticated redirect), `307` for admin pages (server-side redirect to `/auth/login`).

### Incidental finding: `npm run build` poisons the dev server's shared `.next` cache

Running a full production build (`npm run build`, done here as part of this stage's own verification)
writes production artifacts (`BUILD_ID`, `routes-manifest.json`, `prerender-manifest.json`, etc.)
into the *same* `.next` directory the `frontend` container's long-running `next dev` process also
uses (both live in the `.next` named volume per `docker-compose.yml`). Restarting the dev server
afterward is **not** enough to recover, unlike the already-documented "new route needs a restart"
Turbopack quirk from Stages 1–5: every route — including old, previously-working ones like
`/auth/login` and `/admin/customers` — started 404ing, not just the new ones. The fix was clearing
the `.next` directory's *contents* entirely (`rm -rf .next/*` inside the container; the mount point
itself can't be removed) before restarting, after which every route resolved correctly. Practical
takeaway for future stages: don't run `npm run build` against the same volume a live `docker compose
up` dev session is using without planning to clear `.next` afterward, or run the build in a separate
one-off container instead.

### Known limitations / deferred items

- **No accept/reject/request-revision on the customer offer page** — the offer page built this stage
  is deliberately read-only. Stage 7's own task list only asks for "customer offer-review page"
  (viewing); Stage 8 ("Customer Decision, Signature, PDF, and Agreement Email") explicitly owns
  "Implement reject and request-revision actions" and "Implement final acceptance flow." The backend
  service functions for accept/reject/revision (`accept_offer`, `reject_offer`, `request_revision`)
  already exist from Stage 4 but still have no API endpoint in front of them — that's Stage 8's job,
  along with the signature/PDF/agreement machinery those actions need to be wired to correctly.
- No agreement, disbursement, or repayment UI exists yet — Stages 8–10.
- The admin dashboard's "new loan requests" indicator is a single count card, not the full CRM-style
  dashboard (metric cards, expected-vs-collected chart, sidebar nav) described in Section 16 — that
  visual/structural work is explicitly Stage 12's ("Production-Quality Dashboards and UI Refinement").
  Same for the customer dashboard's active-loan-summary/repayment-schedule/agreement-download
  sections, which don't exist yet since nothing in the domain has reached those states.
- No dedicated data-table or status-badge *design system* component existed before this stage; a
  `StatusBadge`/`StatusTimeline` pair was added under `components/requests/` for this stage's own
  needs. A future stage may want to generalize these further once loans/repayments need the same
  kind of status display.

### Files created/changed this stage

Backend: `common/domain.py`, `common/api/exceptions.py` (new), `common/permissions/roles.py`,
`config/settings/base.py`, `config/urls.py`, `apps/loan_requests/{serializers,views,filters,urls}.py`
(new), `apps/loan_offers/{services,serializers,views,urls,models}.py`, `apps/messaging/services.py`
(new), `tests/factories.py`, `apps/loan_requests/tests/test_api.py` (new),
`apps/loan_offers/tests/{test_admin_offer_api,test_customer_offer_api}.py` (new; plus a one-line fix
to `test_loan_offers.py`'s `test_first_offer_is_version_one`), `apps/messaging/tests/test_services.py`
(new).

Frontend: `components/ui/textarea.tsx` (new), `features/loan-requests/` (new),
`features/offers/` (new), `schemas/{loan-request,offer}.ts` (new),
`components/requests/{loan-request-form,status-badge,status-timeline}.tsx` (+ test),
`components/offers/offer-form.tsx` (+ test), `app/(customer)/requests/{page,new/page,[id]/page}.tsx`
(new), `app/(customer)/offers/[id]/page.tsx` (new), `app/(customer)/dashboard/page.tsx`,
`app/(admin)/admin/loan-requests/{page,[id]/page}.tsx` (new), `app/(admin)/admin/dashboard/page.tsx`.

Docs: `docs/STATUS_TRANSITIONS.md` (three open decisions resolved/confirmed), this file.

### Acceptance criteria check

Stage 6 (Section 24):
- [x] Customer submits a valid request — proven live (`REQ-2026-000002`, `201`).
- [x] Customer sees only their requests — proven live (`403` on cross-customer access, list scoped).
- [x] Staff can see the new request in a secured admin list — proven live (queue + search + filter).

Stage 7 (Section 24):
- [x] Loan officer can send a correct offer — proven live, numbers hand-verified against the Stage 5
      calculator's own worked examples.
- [x] Customer can see the current offer and full schedule — proven live
      (`GET /api/v1/customer/offers/{id}/`).
- [x] Previous versions are retained for audit — `AdminLoanRequestDetailSerializer.offers` returns
      the complete version history; covered by `test_detail_includes_offer_history` and the
      supersede test.

### Open decisions carried over from Stage 0

Unchanged except #2 (`APPROVED` reserved/unused, now confirmed through Stage 7) and the expiry
mechanism (now confirmed unreachable through any Stage 6/7 endpoint, no change needed) — both marked
resolved above. Decisions #4–6 still apply to their originally identified stages.

---

## Stage 8 — Customer Decision, Signature, PDF, and Agreement Email, and Stage 9 — Approval and Manual Disbursement Recording

Built together, per explicit instruction, in one implementation-and-report cycle — same combined-stage
exception used for Stages 4/5 and 6/7. Reported together since Stage 9's approval/disbursement
workflow is the direct continuation of Stage 8's acceptance flow (both operate on the same `Loan`
row) and shares the admin-side UI shell.

### Objective

Turn a `SENT` offer into a binding, auditable acceptance with a generated agreement PDF and a
`PENDING_APPROVAL` loan (Stage 8), then let an authorised approver and a separate finance officer
move that loan through approval and a manually-recorded disbursement into `ACTIVE`, with the
customer's payout details revealed only through an audited action (Stage 9).

### What was built

**Backend — new infrastructure**

- `requirements.txt` — `weasyprint==66.0`, `pillow==11.3.0`. `Dockerfile` — added WeasyPrint's system
  libraries (`libpango`, `libpangoft2`, `libpangocairo`, `libcairo2`, `libgdk-pixbuf-2.0-0` — Debian
  trixie's current package name, not the `libgdk-pixbuf2.0-0` name used on older Debian, discovered
  by an actual build failure — see Errors below —, `libffi-dev`, `shared-mime-info`,
  `fonts-liberation`).
- `integrations/storage/backends.py` (new) — the `Storage` abstraction promised by
  `docs/ARCHITECTURE.md` Section 11: a thin wrapper around Django's own `storages["default"]`
  (`FileSystemStorage`, rooted at `MEDIA_ROOT`, selected by `STORAGE_BACKEND=local`). Every saved file
  gets a randomised name (`{subdir}/{uuid4().hex}{ext}`) — caller-supplied names only ever contribute
  an extension, never a path component. An S3-compatible backend is a documented deferred item, added
  when production actually needs one rather than built speculatively now.
- `common/api/request.py` (new) — `get_client_ip()`/`get_user_agent()`, the first callers that need
  IP/user-agent extraction (Agreement's acceptance evidence, the payout-reveal audit event).
- `config/settings/base.py` — `STORAGE_BACKEND`, `LENDER_NAME` (a documented placeholder legal
  identity — Section 18: "Do not claim... legal validity"), `HUBTEL_ADMIN_PHONE_E164` (read now since
  Stage 9's disbursement SMS intent needs it; the Hubtel client itself is still Stage 11).
  `config/settings/test.py` — `MEDIA_ROOT` pointed at a fresh `tempfile.mkdtemp()` so a test run's
  generated PDFs/signatures never land in the real dev media volume.

**Backend — `apps/agreements/`** (Stage 8)

- `services.py` (new) — `validate_signature_image()` (decodes a data-URL, rejects anything
  malformed/oversized/not a real PNG/JPEG via Pillow's `Image.open().verify()`, raising the new
  `InvalidSignatureError(DomainError)` → 409), `sha256_hex()`, `render_agreement_pdf()` (WeasyPrint
  against a new `templates/agreements/agreement_pdf.html`, with the signature image embedded as a
  base64 `<img>` — Section 18's "signature image" PDF-content requirement), and
  `accept_offer_and_create_agreement()` — the one orchestration point that, in a single transaction,
  calls `apps/loan_offers/services.py::accept_offer()`, saves the signature, generates and hashes the
  PDF, creates the immutable `Agreement` row, and calls `apps/loans/services.py::create_loan()`. A
  failure anywhere in that chain (invalid signature, a PDF-generation error) leaves nothing
  half-created. `send_agreement_email()` and `retry_agreement_email()` are called *after* that
  transaction commits (from the view), so an email failure can never undo a valid acceptance (Section
  18's explicit rule) — `send_agreement_email()` only ever updates the two mutable-after-create
  bookkeeping fields on `Agreement`.
- `serializers.py`/`views.py`/`urls.py` (new) — `AgreementSerializer` (includes a `download_url`
  built from `request.build_absolute_uri()`, never the raw storage path), `AgreementDetailView` (GET,
  owner-or-any-staff-role), `AgreementDownloadView` (streams the PDF via the storage abstraction —
  never a public/guessable path), `AdminAgreementRetryEmailView` (`LOAN_OFFICER`/`SUPER_ADMIN`,
  reuses the already-generated PDF, never regenerates it).
- `apps/loan_offers/serializers.py`/`views.py` — added `AcceptOfferSerializer` (typed name, a
  `declaration_accepted` boolean that must be `true`, the raw signature data-URL),
  `RejectOfferSerializer` (reason optional), `RequestRevisionSerializer` (reason **required** — a
  design decision: a revision request with no reason gives the officer nothing to act on, unlike a
  plain rejection), and the three new views: `CustomerOfferAcceptView`, `CustomerOfferRejectView`,
  `CustomerOfferRequestRevisionView`. `CustomerOfferSerializer` gained `loan_request_id` — the
  customer-facing offer page needs somewhere to send the customer back to after a reject/revision
  decision.
- `apps/loan_requests/serializers.py`'s `LoanRequestSerializer` gained a `loan` summary field
  (id/loan_number/status, via the reverse `loan_request.loan` OneToOne accessor) — once a request
  converts, its own detail page can link straight to `/loans/{id}` instead of continuing to show
  offer-decision chrome that no longer applies.

**Backend — `apps/loans/`** (Stage 9)

- `services.py` — added `record_disbursement()`, the single Stage 9 orchestration point: validates
  the loan is `APPROVED_FOR_DISBURSEMENT` (else `LoanNotReadyForDisbursementError`), that the
  disbursed amount exactly equals `Loan.principal` (else `DisbursementAmountMismatchError`), that no
  `Disbursement` already exists for this loan and the external reference isn't already used (else
  `DuplicateDisbursementError`/`DuplicateDisbursementReferenceError` — checked proactively *and* as a
  fallback around the `IntegrityError` the DB's own `UniqueConstraint`s would raise on a genuine
  race), then creates the `Disbursement` row, calls the existing `activate_after_disbursement()` and
  `copy_schedule_from_offer()` (both built and tested in Stage 4, previously uncalled), and posts a
  ledger entry — all four in the loan row's own lock, one transaction.
- `filters.py`/`serializers.py`/`views.py`/`urls.py` (new) — `AdminLoanListView`/`AdminLoanDetailView`
  (read access for every staff role — Section 10: "Auditors have read-only access to operational and
  audit records"), `AdminLoanApproveView` (`APPROVER`/`SUPER_ADMIN` only),
  `AdminLoanDisburseView` (`FINANCE_OFFICER`/`SUPER_ADMIN` only; accepts multipart form data so an
  optional evidence file can ride alongside the JSON fields), `LoanPayoutDetailsRevealView` (Stage 3's
  deferred "authorised reveal" finally built: `FINANCE_OFFICER`/`SUPER_ADMIN`, returns the full
  unmasked `CustomerProfileSerializer` shape, and unconditionally writes an `AuditEvent` — with the
  *fact* of the reveal and the payout method, never the raw account digits themselves, even in the
  audit JSON), `CustomerLoanDetailView` (owner-only, lets the customer track status/schedule/agreement
  after acceptance).
- `apps/repayments/models.py`'s `LoanTransaction.amount` docstring comment — corrected (see Design
  decision 1 below).

**Frontend**

- `signature_pad@5` (new dependency) — `components/agreements/signature-canvas.tsx`: a thin wrapper
  (master prompt Section 6's suggested approach) around a `<canvas>`, device-pixel-ratio-aware,
  exposing `toDataURL()`/`clear()` via `useImperativeHandle`.
- `components/ui/dialog.tsx` (new) — a small Base UI (`@base-ui/react/dialog`) wrapper, this
  codebase's first dialog/modal component — used for the acceptance flow's required "final
  confirmation dialog" (Section 15).
- `components/offers/offer-decision-panel.tsx` (new, +test) — the full signature experience: a
  confirmation checkbox with the versioned acceptance text (display copy only — the authoritative,
  hashed text lives server-side; a code comment ties the two together explicitly so a future wording
  change doesn't silently drift), typed full legal name, the drawn signature, a "Review and accept"
  step that validates all three before opening the confirmation `Dialog`, and — right next to it —
  simpler reject/request-revision forms. On successful acceptance the customer is redirected straight
  to `/loans/{id}` (the response already carries the new loan's id — no extra round trip).
- `features/agreements/`, `features/loans/` (new) — types/api/hooks mirroring the new serializers.
  `lib/api-client.ts`'s `apiFetch()` — one necessary fix: it was unconditionally forcing
  `Content-Type: application/json` whenever a body was present, which silently breaks a `FormData`
  upload (the browser needs to set its own multipart boundary) — Stage 9's disbursement-evidence
  upload is the first caller to actually pass one.
- Customer pages: `app/(customer)/loans/[id]/page.tsx` (new) — status, financial summary, agreement
  download link, repayment schedule once populated. `app/(customer)/offers/[id]/page.tsx` — wired in
  `OfferDecisionPanel`. `app/(customer)/requests/[id]/page.tsx` — links to the new loan once the
  request has converted.
- Admin pages: `app/(admin)/admin/loans/{page,[id]/page}.tsx` (new) — queue with status filter/search
  (the dashboard's new cards deep-link into it via `?status=`, which the page reads through Next 16's
  async `searchParams` prop, the same `use()` pattern already used for dynamic route `params`),
  detail page with the approve action, `components/loans/disbursement-form.tsx` and
  `components/loans/payout-details-reveal.tsx` (fetched only on an explicit click — `usePayoutDetails`
  is `enabled: false` by default, never eager). `app/(admin)/admin/dashboard/page.tsx` — two new
  count cards ("Awaiting approval", "Awaiting disbursement").

### Design decisions

1. **`Loan.outstanding_balance` is unaffected by disbursement — only repayment moves it.**
   `create_loan()` (Stage 4) already sets `outstanding_balance = total_repayable` at
   `PENDING_APPROVAL` time, before any money has moved — the customer's acceptance already commits
   them to the full amount. Section 19's reconciliation formula
   (`outstanding == total_repayable - amount_repaid`) is defined purely in terms of repayment, with
   no mention of disbursement. The Stage 4 `LoanTransaction.amount` docstring comment claimed
   "DISBURSEMENT increases outstanding balance," which would have double-counted the debt (it was
   never actually exercised until this stage). Resolved: `_post_disbursement_ledger_entry()` posts a
   real, positive-amount `DISBURSEMENT` ledger row for the audit trail, but with `balance_after` equal
   to the *unchanged* `outstanding_balance` — a deliberate, documented departure from
   `apps/repayments/services.py::post_ledger_entry()`'s REPAYMENT/REVERSAL semantics, not reachable
   through that function at all. The model comment was corrected in the same change.
2. **The agreement PDF contains its own document reference but not its own hash.** Section 18 asks
   for both in the generated PDF. The hash can only be computed from the final PDF bytes, so a PDF
   containing its own hash is a chicken-and-egg problem; the standard resolution (and the one used
   here) is to embed a stable `document_reference` (`{request_number}-AGR-v{version}`) in the PDF body
   and expose the SHA-256 externally instead — on the `Agreement` record, in the API response, and in
   the confirmation email body.
3. **Signature validation is a `DomainError`, not a plain serializer field error.** An
   unparseable/oversized/non-image signature maps to 409 (`InvalidSignatureError(DomainError)`),
   consistent with every other business-rule rejection in this codebase, rather than a 400 — it's a
   business-rule violation ("this isn't an acceptable signature"), not a shape/type mismatch.
4. **Any staff role — not just the owner — can download an agreement PDF.** Section 10: "Auditors
   have read-only access to operational and audit records," and support staff legitimately need to
   pull up a signed agreement. `AgreementDownloadView`/`AgreementDetailView` use
   `IsOwner | has_any_role(*STAFF_ROLES)`.
5. **The disbursement endpoint accepts multipart form data unconditionally**, not JSON-with-optional-
   multipart-fallback — simpler on both ends, and the one new upload field (`evidence_file`) is always
   optional, so a submission with no file still works through the same code path.

### Commands actually run, with results

```
docker compose build backend
  → first attempt failed: libgdk-pixbuf2.0-0 has no installation candidate on this python:3.13-slim
    (Debian trixie) base image — the package was renamed libgdk-pixbuf-2.0-0. Fixed, rebuilt clean.

docker compose exec backend ruff check . / ruff format --check .        → clean
docker compose exec backend python manage.py check                       → 0 issues
docker compose exec backend python manage.py makemigrations --check --dry-run
  → No changes detected (no new models this stage — Agreement/Loan/Disbursement/RepaymentInstallment/
    LoanTransaction all already existed from Stage 4)

docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.test backend pytest -q
  → 280 passed (229 carried over from Stages 4–7, 51 new: agreement acceptance/reject/revision/
    download/retry-email API tests, admin loan list/detail/approve/disburse/payout-reveal API tests)

docker compose exec frontend npm run lint       → clean (after one real fix, see Errors below)
docker compose exec frontend npm run typecheck  → clean
docker compose exec frontend npm run test       → 44 passed (39 carried over, 5 new:
    offer-decision-panel — signature-required gate, full accept→redirect flow, reject, request-
    revision, and the "renders nothing once decided" guard)
docker compose exec frontend npm run build      → succeeded; /admin/loans, /admin/loans/[id],
    /loans/[id] all present in the route table
```

Real issues caught by actually running these, not just writing the code:

- **`libgdk-pixbuf2.0-0` doesn't exist on this Debian version** — the `python:3.13-slim` base image
  moved to Debian trixie, which renamed the package to `libgdk-pixbuf-2.0-0`. Caught immediately by
  the Docker build itself; fixed by using the correct current package name.
- **A React Compiler-era `react-hooks/refs` false positive** on the signature-check callback passed
  to `handleSubmit()`: the rule can't see through react-hook-form's wrapper far enough to prove the
  ref read only ever happens on a real submit event, not during render (it does — `openConfirmDialog`
  is only ever invoked as the form's `onSubmit`). Same class of justified, narrowly-scoped
  `eslint-disable-next-line` as Stage 2's Google-button case, with the same standard applied: read the
  rule's rationale first, and only suppress when a genuine restructure isn't available.
- **Vitest's default 5s per-test timeout was too tight for the two `offer-decision-panel` tests that
  exercise the full checkbox + signature + confirmation-dialog path** — genuinely slow in this
  environment (Windows Docker Desktop's documented slow bind-mount filesystem, several `user.type()`
  calls, a heavier component tree than any prior form), not a hang: re-run with `--testTimeout=20000`
  passed cleanly at ~4.5–6.2s each. Fixed with a per-test timeout override on just those two tests,
  not a global config change that would mask a real hang elsewhere.
- **The same `.next` dev-server-cache-poisoning issue documented in Stage 6/7 recurred** after this
  stage's own `npm run build` verification run — same fix (`rm -rf .next/*` + `docker compose restart
  frontend`), now a firmly established, expected step after any `npm run build` against the live dev
  volume, not a new problem.
- A full parallel `npm run test` run (not `npm run lint`/`typecheck`/the isolated new-test runs above)
  again showed several pre-existing, unrelated test files (`amortization-preview-form`, `offer-form`,
  `profile-form`, `loan-request-form`) timing out — confirmed, again, by re-running each file alone
  (twice, for good measure) that every one passes standalone in 4–7s. Same documented
  resource-contention flakiness as Stage 6/7, not a regression; none of these files were touched this
  stage.

**Live end-to-end verification against the running Docker stack** (`manage.py shell` for user setup,
real `curl` calls through allauth headless sessions against the actual DRF endpoints — same technique
as every prior stage):

- Full chain: customer submitted `REQ-2026-000006`; officer started review, created a GHS 3,000 /
  10% / 6-month draft (total interest 300.00, total repayable 3,300.00 — hand-verified), sent it;
  customer accepted with a typed name, checked declaration, and a real 1×1 PNG signature → `201`,
  real `Agreement` created, real `Loan` `LN-2026-000002` created `PENDING_APPROVAL`. The generated PDF
  was downloaded and confirmed to genuinely start with `%PDF-1.7` (WeasyPrint actually ran, not
  mocked) with the correct `Content-Disposition` header.
- **Negative paths, all correct**: accepting the same offer twice → `409` (`InvalidTransitionError`,
  `LoanOffer` already `ACCEPTED`); downloading the agreement as an unrelated non-owner, non-staff
  customer → `403`; unauthenticated download → `401`; a plain customer hitting the admin retry-email
  endpoint → `403`. (A staff, non-owner download correctly returned `200` — by design, Design decision
  4 above — the first attempt at this check used a staff account and had to be corrected to a genuine
  second customer to actually prove the `403` boundary.)
- Confirmed `AGREEMENT_ACTION_EMAIL` is blank in this dev environment's `.env`, so the live acceptance
  naturally exercised the **email-failure path**: `email_delivery_status` came back `FAILED` on the
  `201` response itself, while the acceptance, `Agreement`, and `Loan` were all still fully created —
  concretely proving Section 18's "email failure does not destroy acceptance" against the real stack,
  not just a mocked test. The retry-email endpoint was then exercised live too (still `FAILED`, since
  the address is genuinely unconfigured — expected).
- A second offer was sent and the customer used the **request-revision** action with a reason →
  offer `REJECTED`, parent request `REVISION_REQUESTED`, confirmed via a follow-up `GET`.
- Stage 9: the approver approved the loan → `APPROVED_FOR_DISBURSEMENT`; a `LOAN_OFFICER` attempting
  the same approve action, and separately attempting to disburse, both correctly got `403` (role
  separation, Section 10, proven live not just in tests); the finance officer revealed payout details
  (`GET .../payout-details/` returned the real unmasked `0241234567`) and confirmed via `manage.py
  shell` that a `customer_profile.payout_details_reveal` `AuditEvent` was written with the actor and
  method but no raw digits anywhere in its JSON; an amount-mismatch disbursement attempt (`2999.00`
  against a `3000.00` principal) → `409`; the correct disbursement → loan `ACTIVE`,
  `amount_disbursed=3000.00`, exactly 6 `RepaymentInstallment` rows copied from the offer schedule
  (values matched 1:1); a second disbursement attempt on the same now-`ACTIVE` loan → `409`.
  `manage.py shell` confirmed the ledger: one `DISBURSEMENT` `LoanTransaction` with `amount=3000.00`
  and `balance_after=3300.00` — equal to `Loan.outstanding_balance`, unchanged by the disbursement,
  exactly as Design decision 1 above describes.
- Frontend: after the `.next` cache clear, `curl` confirmed every new route resolves correctly —
  `/loans/[id]` and `/offers/[id]` → `200` (client-side guard handles the unauthenticated case, same
  as every other customer route), `/admin/loans/[id]` → `307` (server-side redirect, same as every
  other admin route).

Test data (`stage89.*@example.com` accounts and their request/offer/agreement/loan) was left in the
dev database rather than force-deleted, matching the Stage 4 precedent: `Loan.customer`'s `PROTECT`
FK genuinely blocks deleting a user still referenced by financial records, and that's the invariant
working as designed.

### Known limitations / deferred items

- **No customer/admin disbursement SMS intents were wired this stage**, despite being in Stage 9's
  task list ("Create customer/admin disbursement SMS intents"). `apps/messaging/services.py` already
  has the `record_sms()` primitive and `SMSMessage.MessageType.DISBURSEMENT`/`ADMIN_NOTIFICATION`
  choices from Stage 4/7, and `HUBTEL_ADMIN_PHONE_E164` was wired into settings specifically to
  support this — but it was not connected to `record_disbursement()` in this pass. **Flagged as a gap
  to close before Stage 10** rather than silently dropped: revisit at the very start of the next
  stage, since it's a small, additive change to `apps/loans/services.py::record_disbursement()`
  mirroring `send_offer()`'s existing `record_offer_ready_sms()` call.
- **No admin UI surfaces the reject/request-revision reason anywhere yet** — the backend records it
  (in the `AuditEvent`'s `reason` field via `offer_services.reject_offer()`/`request_revision()`), but
  neither the admin loan-request detail page nor a notification shows the officer *why* a customer
  declined. Worth adding to Stage 12's dashboard/UI-refinement pass.
- **No cancel-loan action is wired to any endpoint** — `apps/loans/services.py::cancel_loan()` has
  existed and been tested since Stage 4, but Stage 9's task list didn't ask for a cancel endpoint, so
  none was built, consistent with this project's "don't wire what isn't asked for" discipline.
- **`OVERDUE`/`RESTRUCTURED`/`DEFAULTED` recomputation** remains entirely unwired, as documented since
  Stage 4 — still explicitly Stage 10/11's job.
- The customer's `/loans/{id}` page shows the repayment schedule once installments exist, but has no
  payment-history section — there's nothing to show yet (Stage 10 owns posting payments).

### Files created/changed this stage

Backend: `requirements.txt`, `Dockerfile`, `integrations/storage/backends.py` (new),
`common/api/request.py` (new), `config/settings/{base,test}.py`, `config/urls.py`,
`apps/agreements/{services,serializers,views,urls}.py` (new), `templates/agreements/agreement_pdf.html`
(new), `apps/agreements/tests/test_acceptance_api.py` (new), `apps/loan_offers/serializers.py`,
`apps/loan_offers/views.py`, `apps/loan_offers/urls.py`, `apps/loan_requests/serializers.py`,
`apps/loan_requests/views.py`, `apps/loans/{filters,serializers,views,urls}.py` (new),
`apps/loans/services.py`, `apps/loans/tests/test_admin_loan_api.py` (new), `apps/repayments/models.py`
(comment fix), `tests/factories.py` (`make_loan()`).

Frontend: `package.json` (`signature_pad`), `src/lib/api-client.ts` (FormData fix),
`src/components/ui/dialog.tsx` (new), `src/components/agreements/signature-canvas.tsx` (new),
`src/components/offers/offer-decision-panel.tsx` (new, + test),
`src/components/loans/{disbursement-form,payout-details-reveal,loan-status-badge}.tsx` (new),
`src/features/agreements/**`, `src/features/loans/**` (new), `src/features/offers/{api,types}.ts`,
`src/features/loan-requests/types.ts`, `src/schemas/{agreement-acceptance,disbursement}.ts` (new),
`src/app/(customer)/loans/[id]/page.tsx` (new), `src/app/(customer)/offers/[id]/page.tsx`,
`src/app/(customer)/requests/[id]/page.tsx`, `src/app/(admin)/admin/loans/{page,[id]/page}.tsx` (new),
`src/app/(admin)/admin/dashboard/page.tsx`.

Docs: this file.

### Acceptance criteria check

Stage 8 (Section 24):
- [x] Customer can make one valid, auditable acceptance — proven live (`201`, real `Agreement` +
      `Loan`) and by `test_valid_acceptance_creates_agreement_and_loan` /
      `test_double_acceptance_is_rejected`.
- [x] Signed PDF is generated and stored — proven live (`%PDF-1.7` bytes downloaded, correct headers)
      and by `test_hash_generation_matches_stored_bytes`.
- [x] Email failure does not destroy acceptance — proven live against the real (unconfigured)
      dev environment, and by `test_email_failure_does_not_undo_acceptance`.
- [x] Accepted offer cannot be edited — `LoanOffer.save()`'s Stage 4 immutability guard already
      covers this; `AdminOfferDetailView.patch()` only ever reaches `update_draft_offer()`, which
      raises `OfferNotEditableError` once `status != DRAFT`.

Stage 9 (Section 24):
- [x] Approval is distinct from disbursement — proven live (`403` for a `LOAN_OFFICER` attempting
      either action; `APPROVER` can approve but not disburse, `FINANCE_OFFICER` the reverse).
- [x] Manual transfer details are displayed securely — masked everywhere except the one dedicated,
      audited reveal action (`LoanPayoutDetailsRevealView`), proven live with a confirmed `AuditEvent`
      containing no raw digits.
- [x] Recorded disbursement activates the loan and schedule exactly once — proven live (schedule
      copied with matching values; a second disbursement attempt on the same loan → `409`) and by
      `test_duplicate_disbursement_is_rejected`/`test_schedule_is_copied_from_the_accepted_offer`.

### Open decisions carried over from Stage 0

Unchanged — decisions #4–6 still apply to their originally identified stages (10, 10/11, 8 — #6 is
now resolved, see below).

Decision #5 (`AGREEMENT_ACTION_EMAIL` single value vs. multiple recipients) is resolved as a single
configurable value, per the existing `EmailMessage(to=[recipient])` implementation — the master
prompt's two example addresses were never a hard requirement for a comma-separated/multi-recipient
mechanism, and nothing in Section 18 asks for one. If multiple recipients are needed later,
`AGREEMENT_ACTION_EMAIL` can hold a comma-separated list with a one-line `.split(",")` change; not
built speculatively now.

---

## Stage 10 — Repayment Posting, Allocation, Reversal, and Reconciliation, and Stage 11 — Hubtel SMS and Scheduled Reminder Processing

### Objective

Stage 10: implement correct manual repayment servicing — allocation, partial/multi-installment
payments, reversal, and reconciliation. Stage 11: integrate Hubtel SMS behind a provider interface,
with a no-queue scheduled-reminder command, without ever making real sending possible by default.

### What was built

**Stage 10 — backend:**

- `apps/repayments/services.py::record_payment()` rewritten into the full Stage 10 orchestration:
  validates the loan is `ACTIVE`/`OVERDUE`, rejects overpayment and non-positive amounts, allocates
  the payment oldest-installment-first (interest before principal within each installment) via
  `PaymentAllocation` rows, posts one `REPAYMENT` ledger entry, recomputes every touched
  installment's status, updates `Loan.amount_repaid`, transitions the loan to `PAID_OFF` (full
  payoff) or back to `ACTIVE` (last overdue installment cleared) as appropriate, audits, and fires
  customer/admin confirmation SMS.
- `_remaining_interest_and_principal()`/`_recompute_installment()`: an installment's
  `amount_paid`/`outstanding_amount`/`status` are derived fresh, every time, purely from its own
  active (`POSTED`-payment) `PaymentAllocation` rows — nothing is stored redundantly. The same
  function runs after both a payment and a reversal, so the two paths can't drift apart.
- `reverse_payment()` extended: flips the payment to `REVERSED`, posts the restoring ledger entry,
  recomputes every affected installment, rolls back `Loan.amount_repaid`, and — a deliberate,
  documented exception to the forward-only transition table — reopens a `PAID_OFF` loan back to
  `ACTIVE`/`OVERDUE` if the reversed payment was what paid it off.
- `reconcile_loan()`/`reconcile_all_loans()` plus `manage.py reconcile`: read-only checks of Section
  19's three invariants (`amount_repaid == sum(active posted payments)`,
  `outstanding == total_repayable - amount_repaid`, per-installment `outstanding == total_due -
  allocated`). Reports differences; never mutates.
- New domain errors (`OverpaymentError`, `InvalidPaymentAmountError`,
  `DuplicatePaymentSubmissionError`, `DuplicatePaymentReferenceError`, `LoanNotOpenForRepaymentError`)
  — all `DomainError` subclasses, mapped to `409` for free.
- `apps/repayments/{serializers,views,urls}.py` (new): `POST/GET /api/v1/admin/loans/{id}/repayments/`
  (record + list history, `FINANCE_OFFICER`/`SUPER_ADMIN` write, all staff read) and
  `POST /api/v1/admin/repayments/{id}/reverse/` (reason required).
  `AdminLoanDetailSerializer`/`CustomerLoanSerializer` gained a `payments` field.

**Stage 11 — backend:**

- `integrations/hubtel/` (new): `SMSProvider` protocol (`send()`/`get_status()`), `DryRunSMSProvider`
  (default, no network call), `HubtelSMSProvider` (real adapter — `POST {base}/v1/messages/send`,
  HTTP Basic Auth, explicit connect/read timeouts, structured handling of timeout/network-error/401
  /403/429/5xx/malformed-JSON/4xx-business-rejection). `get_sms_provider()` only ever returns the real
  provider when **both** `HUBTEL_ENABLED=true` and `SMS_DRY_RUN=false` are explicitly set.
- `apps/messaging/models.py`: `SMSMessage.MessageType` replaced with the full Section 17 catalog (18
  types) — a real schema migration, since the Stage 4/7 set was provisional.
- `apps/messaging/services.py`: `dispatch_sms()` (sends one eligible message, updates
  status/attempt_count/next_attempt_at, fixed backoff on failure, never raises) and
  `dispatch_after_commit()` (`transaction.on_commit()` wrapper — the no-queue mechanism for "send
  after the financial transaction commits"). One `record_*_sms()` template-rendering function per
  immediate-event type (offer ready, offer accepted, loan approved, disbursed, payment received,
  paid off), each rendered per Section 27's suggested templates and wired into its real trigger point.
  `render_reminder_message()`/`record_manual_reminder_sms()` for scheduled and manual reminders.
- `apps/messaging/management/commands/process_due_sms.py`: idempotent, session-scoped PostgreSQL
  advisory-lock-protected (`pg_try_advisory_lock`) scheduler. Each run: (1) recomputes
  `UPCOMING`→`DUE`/`DUE`|`PARTIALLY_PAID`→`OVERDUE` installment statuses and the matching
  `Loan` `ACTIVE`↔`OVERDUE` status (the Stage 4/8-9 "open decision," resolved here); (2) creates
  missing `REPAYMENT_DUE_*`/`REPAYMENT_OVERDUE` reminders for the current Accra business
  date/slot, deduplicated by the existing DB uniqueness constraint; (3) dispatches PENDING messages
  and eligible FAILED retries in one rate-limited batch. `--dry-run`/`--now`/`--limit` flags as
  specified.
- `apps/messaging/management/commands/query_sms_status.py`: best-effort delivery-status query mode
  (see Known limitations).
- `apps/messaging/{serializers,views,filters,urls}.py` (new): `GET /api/v1/admin/sms-messages/`
  (list, filterable), `GET .../summary/` (status counts), `POST .../{id}/retry/` (manual resend,
  audited), `POST /api/v1/admin/installments/{id}/manual-reminder/` (audited, exempt from the
  scheduled-reminder uniqueness constraint).
- Closed two flagged gaps from earlier stages: Stage 9's "customer/admin disbursement SMS intents"
  (`apps/loans/services.py::record_disbursement()`) and a previously-unwired
  `OFFER_ACCEPTED_CUSTOMER`/`ADMIN` + `LOAN_APPROVED` trigger (`apps/agreements/services.py`,
  `apps/loans/services.py::approve_loan()`) — Stage 11's "implement templates for all required
  message types" made these the natural place to close them.
- `config/settings/base.py`: the remaining `HUBTEL_*`/`SMS_*` settings (base URL, credentials, sender
  ID, timeouts, rate limit, dry-run, max attempts, reminder slot times).

**Frontend (Stage 10 + 11):**

- `src/features/repayments/**` (new): types mirroring the serializers, `recordPayment()` (multipart
  when evidence is attached, matching the disbursement pattern), `reversePayment()`, `listPayments()`.
- `src/schemas/repayment.ts` (new): amount/date/method validation, reversal-reason validation.
- `src/components/repayments/repayment-form.tsx` (new): Section 16's "Payment modal" as a `Dialog` —
  shows outstanding balance and next-due installment, amount/date/method/reference/evidence fields, a
  client-side resulting-balance preview (informational — the backend recalculates authoritatively),
  and a per-dialog-session idempotency key so a double-click can't post twice.
- `src/components/repayments/payment-history-table.tsx` (new): receipt/date/amount/method/status
  table with a reason-required reversal dialog; a `showActions` prop distinguishes the admin page
  from the customer's read-only view.
- `src/features/messaging/**`, `src/components/messaging/manual-reminder-button.tsx`,
  `src/app/(admin)/admin/sms-activity/page.tsx` (new): SMS history table with status filter and
  per-message retry, and status-count summary cards.
- Wired into `admin/loans/[id]/page.tsx` (repayment form + history + a "Send reminder" action per
  schedule row), `(customer)/loans/[id]/page.tsx` (read-only payment history), and
  `admin/dashboard/page.tsx` (Active/Overdue loan counts, an SMS Activity card).
- `RepaymentInstallmentSummarySerializer` gained an `id` field (needed for the manual-reminder
  action) — a small, additive serializer change.

### Design decisions

1. **Installment status is a pure derived recomputation, not a guarded state-machine transition.**
   `_recompute_installment()` recalculates from active `PaymentAllocation` rows every time, rather
   than incrementally applying "the" forward transition table. A reversal genuinely needs to move an
   installment backward (`PAID` → `PARTIALLY_PAID`), which the STATUS_TRANSITIONS.md table was never
   meant to describe (it documents forward business triggers) — recomputing from source means the
   post-payment and post-reversal code paths structurally cannot drift apart. Same reasoning applied
   to `Loan` `PAID_OFF` → `ACTIVE`/`OVERDUE` on reversal.
2. **No queue for SMS — `transaction.on_commit()` is the whole mechanism.** Section 17 requires
   "commit the financial transaction first, then attempt delivery outside it" without adding
   Redis/Celery. Registering the real send via `transaction.on_commit()` from inside the same service
   function that makes the financial/state change satisfies this exactly: in autocommit mode (no
   enclosing `atomic()`), the callback fires immediately after that statement's implicit commit; if a
   caller nests it inside their own `atomic()`, it fires when that outer transaction commits. Either
   way, a send failure can only ever mutate the `SMSMessage` row.
3. **`OVERDUE` recomputation piggybacks on `process_due_sms`**, exactly the recommendation recorded
   in `STATUS_TRANSITIONS.md` back in Stage 4/8-9 — no new scheduler entry, one idempotent run covers
   reminders and status recomputation together.
4. **Hubtel's delivery-status query endpoint is unconfirmed — flagged, not guessed.** Hubtel's public
   SMS product documents delivery confirmation via an account-level callback webhook, not a pull
   endpoint. `HubtelSMSProvider.get_status()` returns `UNKNOWN` rather than calling a plausible-looking
   but unverified URL that could silently misreport delivery in production; `query_sms_status` is
   explicitly documented as best-effort until a real endpoint or callback receiver is confirmed.
5. **`manage.py reconcile` found genuine pre-existing drift** in a loan created during Stage 8/9's own
   live verification (before `amount_repaid` tracking existed) — left as-is (the command's job is to
   report, never auto-correct) and cited here as live proof the check actually works, not just that it
   runs.

### Commands actually run, with results

Backend:
```
docker compose exec backend python manage.py makemigrations
  -> apps/messaging/migrations/0002_alter_smsmessage_message_type.py

docker compose exec backend ruff format . && ruff check . --fix
  -> All checks passed! (9 files reformatted; two remaining long-line cases fixed by hand)

docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.test backend pytest -q
  -> 347 passed (up from 280; 67 new: allocation/reversal/reconciliation/concurrency for
     repayments, Hubtel provider mocked send [success/timeout/network-error/401/403/429/5xx/
     malformed-JSON/4xx], dispatch/retry-backoff, process_due_sms reminder windows/dedup/
     paid-skip/partial-amount/OVERDUE-recompute/advisory-lock, and admin API contract tests for
     both new apps)

docker compose exec backend python manage.py makemigrations --check --dry-run
  -> No changes detected
```

Frontend:
```
docker compose exec frontend npm run typecheck  -> clean
docker compose exec frontend npm run lint        -> clean (one React Compiler warning on
                                                     form.watch() fixed by switching to useWatch(),
                                                     matching profile-form.tsx's existing precedent)
docker compose exec frontend npm run test -- --run
  -> 50 passed (up from 44; 6 new: repayment-form, payment-history-table). The same 5 pre-existing
     files flakily time out under full-parallel load (documented since Stage 6/7) — each reconfirmed
     passing in isolation.
docker compose exec frontend npm run build       -> clean; /admin/sms-activity appears in the route
                                                     list as expected. .next dev cache cleared +
                                                     frontend restarted afterward (documented Stage
                                                     6/7 remedy).
```

Live verification against the running Docker stack (real curl calls through allauth headless
sessions, a fresh request → offer → accept → approve → disburse chain, GHS 1,200 principal, 4 ×
GHS 300 installments, 0% interest for exact-number verification):

- Offer accepted → `OFFER_ACCEPTED_CUSTOMER` SMS `SENT` (dry-run). Approved → `LOAN_APPROVED` SMS
  `SENT`. Disbursed → `LOAN_DISBURSED_CUSTOMER` SMS `SENT` — closing the Stage 9 gap, confirmed live.
- GHS 100 partial payment → allocated entirely to installment #1's principal (0% interest loan);
  installment → `PARTIALLY_PAID`; `PAYMENT_RECEIVED_CUSTOMER` SMS `SENT` with the correct next-due
  preview.
- Duplicate `idempotency_key` on a retried payment → `409`. Overpayment (GHS 9999 against a GHS
  1,100 balance) → `409` with the exact balance in the message. `APPROVER` attempting to record a
  payment → `403`.
- GHS 1,100 final payment → correctly split across 3 remaining installments (200/300/300);
  loan → `PAID_OFF`, `outstanding_balance=0.00`, `amount_repaid=1200.00`, `closed_at` set;
  `LOAN_PAID_OFF_CUSTOMER` SMS `SENT`.
- Reversal without a reason → `400`. Reversing the final payment → loan reopened to `ACTIVE`,
  `outstanding_balance=1100.00`, `amount_repaid=100.00`, installment #1 back to `PARTIALLY_PAID` —
  proving the `PAID_OFF` → `ACTIVE` exception live.
- `manage.py process_due_sms --now "2026-12-27T09:00:00+00:00"` (5 days before installment #1's due
  date): created a `REPAYMENT_DUE_5_DAYS` reminder whose body correctly showed GHS 200.00 (the
  *remaining* amount after the earlier partial payment), not the original GHS 300.00 installment
  total. Re-run with `--dry-run` on the same business date: `reminders_created: 0` — idempotency
  confirmed live, not just in tests.
- `POST .../manual-reminder/` as `LOAN_OFFICER` → `201`, audited (`sms_message.manual_reminder` with
  the supplied reason); as the customer → `403`.
- `GET .../sms-messages/summary/` returned real status counts across all live-created messages.
- **Bug found and fixed during this pass**: `AdminManualReminderView`'s response showed the SMS as
  `PENDING` even though the dry-run send had already completed (confirmed via direct DB read) —
  `transaction.on_commit()` fires *inside* `record_manual_reminder_sms()` in autocommit mode, so the
  dispatch mutates a freshly-fetched row while the view's in-memory `message` object still held its
  pre-dispatch value. Fixed with a `message.refresh_from_db()` before serializing the response
  (mirroring the retry view, which already had this) — confirmed live afterward (`SENT` in the
  response body).
- `manage.py reconcile` → found and correctly reported real drift in a loan from Stage 8/9's own live
  verification session (predates `amount_repaid` tracking); the loan created in *this* session's
  verification reconciled cleanly at every step, confirmed via `reconcile_loan()` directly.

### Known limitations / deferred items

- **Hubtel delivery-status confirmation (`SENT` → `DELIVERED`) is not reachable** — see Design
  decision 4. `query_sms_status` exists and is tested but is honestly best-effort until a real
  endpoint or callback receiver is confirmed against a live Hubtel account.
- **No cron/systemd-timer entry actually schedules `process_due_sms`** in this environment — the
  command itself is idempotent and ready to be invoked every 15 minutes/hourly; wiring an actual
  scheduler entry is a deployment-environment task, explicitly Stage 15's job
  ("document platform cron/scheduler setup").
- **Admin-notification SMS (`*_ADMIN` types) were never exercised live** in this pass — they're
  correctly skipped whenever `HUBTEL_ADMIN_PHONE_E164` is unset, which it is in this dev environment;
  covered by unit tests (`test_admin_loan_api.py`-style role assertions aren't relevant here, but the
  `record_*_sms()` functions are directly tested for the admin-number-present branch).
- **No dedicated "waiver" UI** — confirmed, not revisited (see `STATUS_TRANSITIONS.md`'s resolution).
- The admin dashboard still doesn't have Section 16's full KPI/chart treatment (outstanding
  portfolio, collected-this-month, expected-vs-collected chart, overdue age buckets, a persistent
  sidebar) — explicitly Stage 12's job; this stage added only the Active/Overdue/SMS-activity cards
  needed to reach the new pages.

### Files created/changed this stage

Backend: `integrations/hubtel/{__init__,base,dry_run,hubtel}.py` (new),
`config/settings/base.py` (Hubtel/SMS settings), `apps/messaging/models.py` (MessageType catalog),
`apps/messaging/{services,serializers,views,filters,urls}.py`,
`apps/messaging/management/commands/{process_due_sms,query_sms_status}.py` (new),
`apps/messaging/migrations/0002_alter_smsmessage_message_type.py` (new),
`apps/messaging/tests/{test_hubtel_provider,test_dispatch,test_process_due_sms,test_admin_sms_api}.py`
(new), `apps/messaging/tests/{test_messaging,test_services}.py` (MessageType renames),
`apps/repayments/services.py` (rewritten), `apps/repayments/{serializers,views,urls}.py` (new),
`apps/repayments/management/commands/reconcile.py` (new),
`apps/repayments/tests/test_repayments.py` (rewritten/extended),
`apps/repayments/tests/test_repayment_api.py` (new), `apps/loans/serializers.py` (`payments` field,
installment `id`), `apps/loans/services.py` (`approve_loan()`/`record_disbursement()` SMS wiring),
`apps/agreements/services.py` (offer-accepted SMS wiring), `apps/loan_offers/tests/test_admin_offer_api.py`
(MessageType rename), `config/urls.py`, `tests/factories.py` (`make_active_loan()`), `Makefile`
(`sms-dry-run`/`reconcile` targets), `.env.example` (unchanged — Hubtel/SMS vars already scaffolded
in Stage 1).

Frontend: `src/features/repayments/**` (new), `src/features/messaging/**` (new),
`src/schemas/repayment.ts` (new), `src/components/repayments/{repayment-form,payment-history-table}.tsx`
(new, + tests), `src/components/messaging/manual-reminder-button.tsx` (new),
`src/app/(admin)/admin/sms-activity/page.tsx` (new), `src/features/loans/types.ts` (`payments`
field, installment `id`), `src/app/(admin)/admin/loans/[id]/page.tsx`,
`src/app/(customer)/loans/[id]/page.tsx`, `src/app/(admin)/admin/dashboard/page.tsx`.

Docs: this file, `docs/STATUS_TRANSITIONS.md`.

### Acceptance criteria check

Stage 10 (Section 24):
- [x] Financial totals reconcile after every test scenario — proven live at every step via
      `reconcile_loan()`, and by `TestReconciliation`'s automated suite.
- [x] No posted payment is edited or deleted — `Payment` rows are never mutated by reversal (a new
      `REVERSED` status + a separate `LoanTransaction` reversal entry); no update/delete API surface
      exists.
- [x] Customer dashboard updates accurately — `CustomerLoanSerializer.payments` reflects posted
      payments in real time; proven via the live-verification loan's `/customer/loans/{id}/` state
      before/after each payment.

Stage 11 (Section 24):
- [x] No Redis or Celery exists — `requirements.txt` unchanged except `integrations/hubtel/`'s use of
      the already-present `requests` library.
- [x] Scheduled reminders work idempotently through the management command — proven live (`--dry-run`
      rerun on the same business date created zero duplicates) and by
      `TestReminderWindows::test_running_twice_does_not_duplicate_reminders`.
- [x] SMS failure never reverses financial records — `dispatch_sms()` never raises; failures only
      mutate the `SMSMessage` row (proven by `test_failed_send_schedules_a_retry` and by construction,
      since dispatch always happens strictly after the financial transaction's commit).
- [x] Real sending is impossible unless explicit environment configuration enables it — proven by
      `TestGetSmsProvider`'s four flag-combination cases; this dev environment (`HUBTEL_ENABLED=false`
      by default) used `DryRunSMSProvider` for every message in this stage's live verification.

### Open decisions carried over from Stage 0

All previously tracked decisions are now resolved (see `STATUS_TRANSITIONS.md`'s "Resolved in Stage
10/11" notes on the `RepaymentInstallment`, `Loan`, `Payment`, and `SMSMessage` sections). No open
product decisions remain blocking Stage 12.

---

## Stage 12 — Production-Quality Dashboards and UI Refinement

### Objective

Complete the corporate CRM-style experience now that the business logic (Stages 4–11) is stable:
the full admin dashboard (Section 16), the customer dashboard (Section 15), and a consistency/
accessibility pass over shared UI, with all metric definitions living in exactly one place on the
backend.

### What was built

**Backend — `apps/dashboards` (new app, read-only, no models/migrations):**

- `apps/dashboards/services.py` — every dashboard figure computed in one place, with the Section 16
  "each metric definition must be documented and tested" documentation in the module docstring:
  - `dashboard_metrics(today)` — the five top metric cards (outstanding portfolio balance = sum of
    `outstanding_balance` over servicing loans; amount due this month = sum of non-WAIVED installment
    `total_due` in the current calendar month over activated loans, deliberately not shrinking as
    payments arrive; amount collected this month = sum of POSTED `Payment.amount` by `payment_date`;
    overdue amount = sum of `outstanding_amount` over OVERDUE installments; active loans = count of
    DISBURSED/ACTIVE/OVERDUE) **plus** the three work-queue counts the Stage 9 dashboard already
    showed (new requests / awaiting approval / awaiting disbursement) — one round trip instead of six
    ("Optimise dashboard queries").
  - `collections_by_month(today, months)` — the expected-vs-collected series via two `TruncMonth`
    aggregate queries, zero-filled so the chart never has gaps.
  - `upcoming_installments(today)` — unpaid installments due in fewer than 7 days on serviced loans,
    each row joined to its latest `SMSMessage` in one batched query (no N+1).
  - `overdue_summary(today)` — the Section 16 age buckets (1–7 / 8–30 / 31–60 / 61+ days) computed in
    a single aggregate query with filtered `Sum`/`Count` per bucket.
  - `recent_transactions()` — newest ledger entries from the append-only `LoanTransaction` table.
- `apps/dashboards/views.py` + `urls.py` — five GET endpoints under `/api/v1/admin/dashboard/`
  (`metrics/`, `collections-chart/?months=6|12` with 400 on anything else, `upcoming-repayments/`,
  `overdue-summary/`, `recent-transactions/`), all staff-readable (including AUDITOR, per Section
  10's read-only access rule), all money serialized as strings.
- `apps/loans` — new `GET /api/v1/customer/loans/` (`CustomerLoanListView`), scoped to
  `request.user`, added so the customer dashboard can find the customer's loan without already
  knowing its id.
- Registered `apps.dashboards` in `LOCAL_APPS` and `config/urls.py`.

**Frontend — admin experience:**

- `components/shared/admin-sidebar.tsx` + reworked `(admin)/layout.tsx` — Section 16's persistent
  compact left sidebar (desktop) with Lucide icons, `aria-current="page"` active marking, and a
  horizontal scrollable nav strip below the header on mobile/tablet (column layout under `md`).
  Only destinations that exist today are listed (Dashboard, Loan Requests, Loans, Customers, SMS
  Activity) — Reports/Audit Log/Settings ship with Stages 13/14 rather than as dead links.
- `features/dashboards/` (types/api/hooks) mirroring the five new endpoints.
- `components/dashboard/metric-cards.tsx` — the five KPI cards with icons, per-card loading
  skeletons, and an error state that never shows stale numbers.
- `components/dashboard/collections-chart.tsx` — Recharts bar chart (expected = neutral,
  collected = primary blue; no gradients), 6/12-month toggle with `aria-pressed`, GHS-formatted
  axis/tooltip, a meaningful empty state when no month has activity, and a `role="img"` aria-label
  describing the chart. Recharts (required by Section 6, first needed here) was installed this stage.
- `components/dashboard/upcoming-repayments-table.tsx` — the Section 16 columns (customer, loan,
  amount due, outstanding, due date, days remaining with due-today/1-day amber emphasis, last SMS
  status) and all four actions: View loan, Send SMS now (reuses Stage 11's `ManualReminderButton`),
  Record payment via the loan page (the Stage 10 modal lives there — no duplicated money logic), and
  SMS history (deep-links to `/admin/sms-activity?loan=<id>`; that page now reads the `loan` query
  param and shows a scoped-view banner with a clear link). No email-reminder action, per Section 16.
- `components/dashboard/overdue-summary-table.tsx` — the four age buckets with installment/loan
  counts and outstanding totals, a total row, and a link to the OVERDUE-filtered loan list.
- `components/dashboard/recent-activity-panels.tsx` — recent ledger entries panel (typed/toned per
  transaction type) and the SMS delivery counts panel (sent/delivered/pending/failed, Section 21)
  linking into SMS activity.
- `components/dashboard/new-requests-table.tsx` — the Section 16 new-requests table (SUBMITTED
  queue) with the specified columns.
- `(admin)/admin/dashboard/page.tsx` — fully rebuilt: KPI row, queue cards, chart + activity panels
  in a responsive grid, then upcoming/overdue/new-requests tables. The Stage 9 placeholder subtitle
  ("Full portfolio KPIs and charts arrive in Stage 12") is gone.

**Frontend — customer experience (Section 15):**

- `components/dashboard/customer-loan-summary.tsx` — the active-loan summary card: principal,
  repaid so far, outstanding, next payment amount and date (first non-settled installment — read
  from the API, not recomputed), status badge, compact 4-row schedule with per-installment badges,
  the last 3 posted payments, View-full-loan and Download-agreement actions.
- `(customer)/dashboard/page.tsx` — rebuilt: primary Request-a-Loan action, current-request card
  with offer link (kept from Stage 6/7), the loan summary above, loading skeletons, and a friendly
  no-loans empty state. Loan chosen by servicing priority (OVERDUE/ACTIVE first, PAID_OFF last).
  Remains deliberately simpler than the admin experience.

**UI refinement pass:**

- `components/ui/skeleton.tsx` — new primitive; `motion-safe:animate-pulse` so reduced-motion
  preferences are respected.
- Consistent installment badges: `INSTALLMENT_STATUS_LABEL` + tone mapping added to
  `features/loans/status.ts` (same green/amber/red tone system as the existing loan/request badges,
  labels not colour alone), rendered by the new `components/loans/installment-status-badge.tsx` and
  applied to the admin loan schedule, the customer loan schedule, and the customer summary card —
  all of which previously showed raw enum text.
- Dialogs were already Base UI (focus trap/restore, Escape handling) — no changes needed there.

### Design decisions

1. **All metric definitions live in `apps/dashboards/services.py`** — the frontend formats and
   renders only. This is the Stage 12 acceptance criterion "No business logic is duplicated in
   frontend components" made structural.
2. **"Due this month" does not shrink as payments arrive** — it is the expected-collections figure
   (sum of installment `total_due` due this calendar month), designed to be read against "collected
   this month". Documented in the service docstring and pinned by
   `test_metric_definitions_are_accurate`.
3. **DISBURSED included defensively in servicing statuses** even though `record_disbursement()`
   moves DISBURSED → ACTIVE in the same transaction — the count can never miss a loan mid-flight.
4. **Sidebar lists only real destinations.** Section 16's suggested nav includes Offers, Repayments,
   Reports, Audit Log, and Settings; offers and repayments are managed inside the request/loan detail
   pages in this build, and Reports/Audit Log/Settings are Stage 13/14 deliverables — they get their
   sidebar entries when their pages exist.
5. **`process_due_sms`'s status recomputation stays forward-only** (confirmed, not changed): during
   live verification the dev database still held OVERDUE installments with *future* due dates —
   residue of Stage 11's `--now`-in-the-future simulation runs, a state real forward-moving time can
   never produce. Healed the dev rows with Stage 10's derived `_recompute_installment()` rather than
   weakening the command.

### Commands run

| Command | Result |
|---|---|
| `docker compose exec backend ruff check .` / `ruff format --check .` | All checks passed / 165 files formatted (1 file auto-formatted during the stage) |
| `docker compose exec backend python manage.py makemigrations --check --dry-run` | No changes detected (the new app has no models) |
| `docker compose exec backend pytest` | **364 passed** (347 before this stage; +17 new: 14 dashboard endpoint/metric tests, 3 customer-loan-list tests) |
| `docker compose exec frontend npm run typecheck` / `npm run lint` | Clean |
| `docker compose exec frontend npx vitest run` | **63 passed, 21 files** (50 before; +13 new across metric cards, chart, upcoming/overdue tables, customer summary, sidebar) — including the historically flaky files, green in this full-parallel run |
| `docker compose exec frontend npm run build` | Production build clean, all 24 routes compiled |
| `rm -rf .next/*` + `docker compose restart frontend` | The known post-build dev-cache measure (see Stage 8/9 notes) |
| `docker compose exec backend python manage.py reconcile` | Exit 1, flagging only the already-documented pre-Stage-10 drift loan (`LN-2026-000001`) — same finding as Stage 10, correctly detected, never mutated |

### Live verification (real Docker stack, dev database)

- Logged in as `admin@flexibuygh.com` through allauth headless (curl, session cookies) and hit all
  five dashboard endpoints: metrics/chart/upcoming/overdue/recent-transactions all returned correct,
  mutually consistent JSON; `?months=9` correctly rejected with 400.
- **Found and resolved a real data inconsistency:** `overdue-summary` showed `total_outstanding`
  9666.68 with every age bucket zero. Root cause: OVERDUE installments dated Sep–Dec 2026 — leftover
  state from Stage 11's future-dated `--now` simulation, impossible under real forward-moving time
  (design decision 5 above). After healing, overdue metrics read 0.00 and buckets/total agree.
- Moved a real unpaid installment (LN-2026-000002 #1) to due-in-3-days and re-queried: the upcoming
  table returned it with `days_remaining: 3` and its genuine Stage 11 SMS history joined on
  (`last_sms_status: SENT`, `last_sms_type: REPAYMENT_OVERDUE`); metrics' "due this month" and the
  chart's July "expected" both moved to 550.00 in step — the documented definitions hold live.
- Customer scoping: the owner of LN-2026-000004 listed exactly their own loan (with schedule and
  payments) on `GET /api/v1/customer/loans/`; a different customer got an empty list; an
  unauthenticated caller is rejected; customers get 403 on every admin dashboard endpoint.
- Frontend: unauthenticated `/admin/dashboard` 307-redirects to `/auth/login?next=…`; with the
  admin session it serves the new dashboard (new subtitle text confirmed in the served HTML).

### Known limitations

- The overdue table is the bucket summary (counts + amounts per age bucket, as Section 16 specifies)
  with a link to the OVERDUE-filtered loan list, rather than a per-installment row listing; Stage
  13's reconciliation/report screens are the natural home for a drill-down if wanted.
- `days_remaining`/bucket maths use the server's calendar date (`timezone.localdate()`); with
  `TIME_ZONE=UTC` a viewer west of UTC could see "due today" a few hours early. Cosmetic; revisit
  only if a Ghana-specific `TIME_ZONE` is set (Ghana is UTC anyway).
- Playwright E2E remains deferred to Stage 14's full test pass, as in every prior stage.

### Files changed this stage

Backend: `apps/dashboards/` (new: `__init__.py`, `apps.py`, `services.py`, `views.py`, `urls.py`,
`tests/test_dashboard_api.py`), `apps/loans/views.py` + `urls.py` (customer loan list),
`apps/loans/tests/test_customer_loan_api.py` (new), `config/settings/base.py`, `config/urls.py`.

Frontend: `package.json` (+recharts), `components/shared/admin-sidebar.tsx` (new, + test),
`app/(admin)/layout.tsx`, `features/dashboards/` (new), `components/dashboard/` (new: metric-cards,
collections-chart, upcoming-repayments-table, overdue-summary-table, recent-activity-panels,
new-requests-table, customer-loan-summary — each with tests where behaviour warranted),
`components/ui/skeleton.tsx` (new), `components/loans/installment-status-badge.tsx` (new),
`features/loans/status.ts` + `api.ts` + `use-loans.ts`, `app/(admin)/admin/dashboard/page.tsx`,
`app/(admin)/admin/sms-activity/page.tsx` (loan query param), `app/(customer)/dashboard/page.tsx`,
`app/(admin)/admin/loans/[id]/page.tsx` + `app/(customer)/loans/[id]/page.tsx` (installment badges).

Docs: this file.

### Acceptance criteria check (Section 24, Stage 12)

- [x] UI resembles a clean, restrained CRM dashboard — white cards, thin neutral borders, light
      neutral page background behind the content area, compact left sidebar, single blue accent,
      Lucide icons, no gradients/glassmorphism/neon, reduced-motion-safe skeletons.
- [x] Metrics are defined and tested — definitions documented in `apps/dashboards/services.py`'s
      docstring; accuracy pinned by `TestDashboardMetrics`/`TestCollectionsChart`/
      `TestUpcomingRepayments`/`TestOverdueSummary` (freezegun-frozen dates, real service-built
      data), and confirmed live against the running stack.
- [x] Customer experience remains simpler than admin — one summary card + request card on a narrow
      centered column, versus the admin's full KPI/chart/table layout.
- [x] No business logic duplicated in frontend components — every figure is fetched; the only
      client-side selection is "which loan to feature" (a display priority) and "first unpaid
      installment" (read off serializer-ordered data, used for display only).

---

## Post-Stage-12 UI redesign (user-directed, 24 Jul 2026)

After Stage 12 closed, the user asked for a full visual overhaul — "modern… too boxy and plain…
take inspiration from apple.com… chic." An Apple design-system spec was loaded from
[VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md/blob/main/design-md/apple/DESIGN.md)
and applied across the frontend:

- **Tokens (`globals.css`)** — cool-gray page canvas with pure-white cards, cool near-black ink,
  and a single deep-indigo accent (user-selected in a follow-up: "indigo/violet + cool gray",
  replacing the initial Apple action-blue), hairline borders, base radius 12px, near-black cool
  dark mode with a lifted indigo accent. Also fixed a real bug found during
  this pass: `--font-sans` was self-referencing and never defined, so the app had been rendering in
  the browser default font — it now resolves to Geist with an SF-style fallback stack, plus the
  spec's open-source substitute rule (−0.01em global tracking).
- **Primitives** — buttons are now capsules with the universal `scale(0.96)` press state and an
  Apple-grammar outline variant; cards are 18px-radius hairline-ring surfaces with 24px padding and
  no shadows; inputs/selects/textareas are 44px-tall, 12px-radius, white-filled; dialogs are 22px
  radius over a blurred backdrop; skeletons respect reduced motion.
- **Chrome** — sticky frosted headers (`bg/80 + backdrop-blur + saturate`), borderless sidebar with
  capsule nav items (white-pill active state) sitting directly on the parchment canvas.
- **Pages** — new Apple-style landing hero (oversized tight-tracked headline, capsule CTA, feature
  triplet on a white band); page titles bumped to `text-2xl`; every table moved onto white 18px
  card surfaces with wider cell padding and row hover; links underline on hover only; badges
  slightly larger pills; chart bars/tooltip rounded.
- **Known deviations from the master prompt's §16 visual notes, per explicit user instruction**:
  frosted-translucent headers (the prompt said no glassmorphism) and a softer, less "corporate CRM"
  look overall. Colour-semantics rules are preserved: one blue accent, green/amber/red still mean
  status only, labels never colour-alone.

- **Customer navigation (same follow-up)** — the customer area previously had no way back from
  sub-pages: added `components/shared/back-button.tsx` (uses real browser history, falls back to a
  sensible parent for deep links) to the requests list, new-request, request-detail, offer, and
  loan pages, plus persistent "Dashboard / My requests" links in the customer header.
- **Final palette pass (second follow-up)** — reverted the accent to blue and moved to a pure-white
  canvas; cards/tables are lifted by a single soft `--shadow-card` token (contact + wide ambient)
  instead of relying on a tinted background; the navbar and admin sidebar are now painted in the
  accent blue (white capsule = active nav item; `UserMenu` gained a `tone="accent"` variant).
- **Onboarding now captures the customer's legal name (same follow-up)** — `accounts.User` already
  had `first_name`/`last_name` columns (no migration needed); `CustomerProfileSerializer` now
  exposes them as required fields (`source="user.…"`, written to the User row on create/update),
  the onboarding form collects them (zod-required, `given-name`/`family-name` autocomplete), and
  every staff surface that renders `customer_name`/`get_full_name()` now shows a real name instead
  of falling back to the email. New tests: serializer requires/stores names (backend, 366 total
  passing), schema + form tests updated (frontend). Verified live: PUT with names → 200 and the
  User row updated; PUT without names → 400 naming both fields.

- **Customer "I've paid" claims (third follow-up)** — new `PaymentClaim` model in `apps/repayments`
  (migration `0002`): informational-only notices that never touch balances. Customer flow: clicking
  a schedule row on the customer loan page opens an installment-detail dialog (principal/interest/
  paid/left-to-pay) with an "I've paid" action (+ optional note) — POST
  `/customer/installments/{id}/claim-payment/` (ownership filtered into the lookup, one PENDING
  claim per installment via a partial unique constraint → 409 on duplicates, 409 on settled
  installments/closed loans; audited). Admin flow: `/admin/payment-claims` queue page
  (list + "Mark reviewed" for LOAN_OFFICER/FINANCE_OFFICER/SUPER_ADMIN; staff-wide read) and a
  "Payment claims" queue card on the dashboard (`pending_payment_claim_count` in the metrics
  endpoint). `record_payment()` auto-resolves pending claims whose installment becomes PAID, so the
  normal path needs no manual step. 10 new backend tests + 4 dialog tests.
- **Dashboard layout pass (same follow-up)** — SMS-delivery panel removed from the dashboard
  (counts remain on /admin/sms-activity; the `SmsStatusPanel` component was deleted); the
  expected-vs-collected chart and recent-transactions cards now stretch to equal height on their
  shared row (`items-stretch` + `h-full`, transactions list scrolls internally); queue cards sit in
  a fixed 2/4-column grid with uniform card heights; headers gained a small drop shadow so the
  accent navbar reads as its own layer above the same-colored sidebar.

- **Repayment collection account + /profile + /admin/settings (fourth follow-up)** — new
  `RepaymentAccount` singleton model in `apps/repayments` (migration `0003`): the company account
  customers pay repayments into (MoMo network/number/name, bank details, free-text instructions),
  deliberately unmasked since they're *receiving* details. `GET /repayment-account/` for any
  signed-in user; `GET/PUT /admin/repayment-account/` (staff read, SUPER_ADMIN-only write, audited
  as `repayment_account.update`). Managed on the new `/admin/settings` page (Settings joined the
  sidebar); shown in the customer installment-detail dialog as a "Pay to" panel with
  copy-to-clipboard buttons. The customer dashboard's compact schedule rows now open that same
  dialog (details + pay-to + "I've paid"), and `/profile` now exists as a proper customer page
  (reusing the onboarding `ProfileForm` in edit mode) with a Profile link in the customer header.
  6 new backend tests; dialog test extended with the pay-to assertion.

Verification: typecheck/lint clean; full vitest run had 15 timeouts across the 6 historically
flaky form-typing files, all confirmed non-regressive by isolated re-runs (18/18 pass); production
build clean; dev cache cleared + container restarted; live smoke confirmed the new landing hero and
the authenticated admin dashboard render. The claims feature was verified live end-to-end: claim →
201 PENDING, duplicate → 409, dashboard metric 1, admin queue row visible, recording the real
payment → claim auto-RESOLVED and metric back to 0. The repayment account was verified live: super
admin PUT → 200, customer GET returns the full details, loan officer PUT → 403. Backend suite: 382
passing.

---

## Requirement-to-Stage Traceability Matrix

Maps every numbered section of the master prompt to the stage(s) that implement it, so nothing is silently dropped as the build proceeds.

| Master prompt section | Topic | Primary build stage(s) |
|---|---|---|
| §1–2 | Role, stage-gated method | Governs every stage |
| §3 | Product summary / end-to-end flow | Stages 6–11 collectively |
| §4 | MVP scope assumptions | Documented Stage 0 (`PRODUCT_ASSUMPTIONS.md`); applied throughout |
| §5 | Explicit non-goals | Enforced throughout; re-checked Stage 14 |
| §6 | Technology stack | Stage 1 (init), used throughout |
| §7 | Repository structure | Stage 1 |
| §8 | High-level architecture | Documented Stage 0 (`ARCHITECTURE.md`); realised Stage 1+ |
| §9 | Authentication/session architecture | Stage 2 |
| §10 | Roles and permissions | Stage 3 (seeding, permission classes), enforced from Stage 4 onward |
| §11 | State machines | Documented Stage 0 (`STATUS_TRANSITIONS.md`); implemented Stage 4, exercised Stages 6–11 |
| §12 | Data model | Documented Stage 0 (`DATA_MODEL.md`); implemented Stage 4 |
| §13 | Money and amortization rules | Stage 5 |
| §14 | API design principles | Applied from Stage 2 onward as endpoints are built |
| §15 | Customer experience requirements | Stages 6, 8, 12 — complete |
| §16 | Admin experience and dashboard design | Stages 7, 9, 10, 12 — complete |
| §17 | Hubtel SMS integration | Stage 11 (placeholders/dry-run from Stage 7 onward per its task list) — complete |
| §18 | Digital acceptance and agreement PDF | Stage 8 |
| §19 | Repayment allocation and ledger rules | Stage 10 — complete |
| §20 | Audit and security requirements | Documented Stage 0 (`SECURITY.md`); implemented incrementally from Stage 2, full pass Stage 14 |
| §21 | Logging and observability | Stage 1 (health endpoints), Stage 11 (scheduler logs), Stage 14 (Sentry, full pass) |
| §22 | Testing strategy | Documented Stage 0 (`TEST_PLAN.md`); executed per-stage, full pass Stage 14 |
| §23 | Developer experience (Makefile, README, .env.example) | Stage 1, extended as needed |
| §24 Stage 0–15 | Sequential build stages | This document tracks each as it completes |
| §25 | Definition of done | Applied as the completion bar for every feature, every stage |
| §26 | Mandatory "DO NOT" rules | Enforced throughout; explicit review Stage 14 |
| §27 | SMS templates | Stage 11 |
| §28 | Environment variables | Stage 1 (`.env.example` skeleton), populated as each integration is built |
| §29 | Final end-to-end acceptance scenario | Release gate before/at Stage 15 |
| §30 | Official documentation references | Consulted as each relevant stage is implemented |

---

## Recommended next stage

**Stage 13 — Reports, CSV Exports, Audit Review, and Operational Tools**, exactly as scoped in
Section 24: loan and repayment CSV exports with permission checks and spreadsheet-formula-injection
protection, audit log filters, a reconciliation report screen (the `reconcile` service from Stage 10
already produces the data — it needs a screen), a failed-SMS operational queue view (a filtered view
over `SMSMessage`, no new infrastructure), an agreement email retry view (the retry endpoint from
Stage 8 already exists), read-only customer/loan support views, and export audit events. When those
pages exist, add Reports and Audit Log to the admin sidebar (`components/shared/admin-sidebar.tsx`
lists only real destinations by design — see Stage 12 design decision 4).

Carry-overs to keep in view: the two standing environment items (Hubtel delivery-status confirmation
endpoint unconfirmed; platform cron entry for `process_due_sms` documented at Stage 15) and the
pre-Stage-10 drift loan `LN-2026-000001` that `reconcile` correctly keeps flagging in dev data — the
Stage 13 reconciliation report screen is where that finding becomes visible to auditors.

Waiting for **CONTINUE** before starting Stage 13, per the mandatory stage-gated working method.
