# Architecture

Status: Locked for MVP (Stage 0). Revisit only through an explicit, documented decision.

## 1. Style

Modular monolith. One Django backend, one Next.js frontend, one PostgreSQL database. Business modules (Django apps) communicate through explicit service functions — never through direct, uncontrolled cross-module model mutation, and never through hidden signal chains for core workflow side effects (see `26. Mandatory "DO NOT" Rules` in the master prompt).

No microservices, no message queue, no Kubernetes. Scheduled work runs as a Django management command invoked by host/platform cron — not an in-process scheduler and not a queue worker.

## 2. High-level component diagram

```text
Customer or Admin Browser
          │
          ▼
Next.js Web Application (App Router, React, TypeScript)
          │ HTTPS, same trusted site where possible
          ▼
Django REST API (/api/v1/)
   ├── Authentication and permissions (django-allauth headless)
   ├── Loan request workflow
   ├── Amortization service (pure, deterministic)
   ├── Agreement and signature service (WeasyPrint)
   ├── Loan state machine
   ├── Disbursement recording
   ├── Repayment ledger
   ├── Dashboard queries
   ├── Audit logging
   └── SMS orchestration (provider-neutral interface)
          │
          ├── PostgreSQL (authoritative data store)
          ├── Hubtel SMS API (outbound only, server-side)
          ├── SMTP / transactional email provider
          └── File / object storage (local dev, S3-compatible in production)

Deployment scheduler or host cron
          │
          ▼
python manage.py process_due_sms   (idempotent, DB-lock protected)
          │
          ▼
Hubtel SMS API
```

## 3. Deployment topology (target production)

```text
https://loans.example.com          -> Next.js (same-site)
https://loans.example.com/api/     -> Django REST API
https://loans.example.com/accounts -> django-allauth provider callbacks
```

Same-site deployment is preferred so session cookies can be `Secure`, `HttpOnly`, `SameSite=Lax/Strict` without cross-site cookie complications. Nginx or Caddy sits in front in production to route `/`, `/api/`, and `/accounts/` to the correct upstream under one trusted domain.

## 4. Backend structure

Django project `config/` with split settings (`base.py`, `local.py`, `test.py`, `production.py`). Django apps under `apps/`, one per bounded business capability:

| App | Responsibility |
|---|---|
| `accounts` | Custom UUID user model, allauth integration glue, roles |
| `customers` | `CustomerProfile`, payout details, onboarding |
| `loan_requests` | `LoanRequest` lifecycle |
| `loan_offers` | `LoanOffer`, `OfferInstallment`, versioning/superseding |
| `agreements` | `Agreement`, signature capture, PDF generation, hashing |
| `loans` | `Loan`, `RepaymentInstallment`, `Disbursement`, loan state machine |
| `repayments` | `Payment`, `PaymentAllocation`, `LoanTransaction` ledger, reversal, reconciliation |
| `messaging` | `SMSMessage`, provider-neutral interface, Hubtel adapter, templates, scheduler command |
| `dashboards` | Read-optimised aggregate queries for admin/customer dashboards |
| `audit` | `AuditEvent`, redaction helpers |

Cross-cutting code lives in `common/` (api helpers, db helpers, money utilities, permission classes, shared test utilities) and `integrations/` (Hubtel client, email client, storage abstraction) — these are infrastructure, not business rules, and must stay thin.

Business rules live in **service functions**, not in views, serializers, `save()` overrides, signals, or Django admin actions. Views/serializers validate shape and call services; services own the rule and the transaction boundary.

## 5. Frontend structure

Next.js App Router with route groups separating concerns by audience:

- `(auth)` — login, signup, verification, password reset.
- `(customer)` — dashboard, request loan, my loans, payments, documents, profile.
- `(admin)` — dashboard, loan requests, offers, active loans, repayments, customers, SMS activity, reports, audit log, settings.

Financial calculations are never duplicated in React components. The frontend renders backend-provided numbers; any client-side preview is explicitly labelled as a preview and reconciled against the backend response before anything is persisted.

## 6. Authentication and session architecture

- `django-allauth[headless]` browser flows — no hand-rolled password reset, OAuth, or session handling.
- Custom Django user model with UUID primary key, created before the first migration.
- Email is the login identifier; unique via case-insensitive normalization enforced at the database level.
- Email verification mandatory for password-based accounts. Unverified users cannot submit loan requests or any other protected business action.
- Google OAuth via django-allauth's Google provider. A Google-authenticated user still must complete the required `CustomerProfile` fields before submitting a loan request.
- Secure, `HttpOnly`, `SameSite` cookies in production. No token of any kind in browser `localStorage`.
- CSRF protection enforced for all cookie-authenticated unsafe requests.
- Login throttling via DRF/allauth-supported rate limiting.
- Admin MFA is a Stage 14 hardening requirement (django-allauth MFA), not built in early stages.

## 7. Roles and permission enforcement

Logical roles: `CUSTOMER`, `LOAN_OFFICER`, `APPROVER`, `FINANCE_OFFICER`, `AUDITOR`, `SUPER_ADMIN`, implemented as Django Groups + permissions. A person may hold multiple roles.

Enforcement is layered and redundant by design:

1. **API permission layer** — DRF permission classes reject the request before it reaches business logic.
2. **Queryset filtering** — every list/detail queryset is filtered by role and ownership; object-level checks alone are not sufficient for list endpoints.
3. **Domain service layer** — critical actions (approve, disburse, post payment, reverse payment) re-check authorisation inside the service, independent of the view. This means the service function is safe to call from a management command or admin action without accidentally bypassing a rule.

Django `is_superuser` is reserved for controlled technical administration; it is not treated as a business authorisation mechanism. Frontend button visibility is never treated as authorisation.

## 8. Amortization service design (forward-compatible)

```text
AmortizationCalculator.calculate(input: AmortizationInput) -> AmortizationResult
```

- Pure function: no HTTP, no database I/O, deterministic given its input.
- `input.interest_method` selects a strategy. MVP ships exactly one strategy, `FLAT_TOTAL_TERM`, but the calculator is structured (e.g. a small strategy-per-method dispatch) so a second method can be added as a new, isolated implementation later without touching the persistence layer, the API contract, or existing accepted offers.
- A separate application service persists the `AmortizationResult` into `OfferInstallment` rows; the calculator itself never touches the database. The same service function backs both the admin "preview" endpoint (Stage 5) and the actual offer-creation path (Stage 7), so preview and persisted numbers can never drift apart.
- An accepted historical offer is never recalculated with a later version of the algorithm — the persisted `OfferInstallment`/`RepaymentInstallment` rows are the permanent record.

## 9. SMS / Hubtel integration design

```text
SMSProvider.send(message) -> SMSProviderResult
SMSProvider.get_status(provider_message_id) -> SMSDeliveryResult
```

`HubtelSMSProvider` implements this interface; a `DryRunSMSProvider` (or equivalent) implements it for local development and tests. Loan/repayment views and services never call Hubtel URLs directly — everything routes through the `messaging` app's service layer, which:

- Commits the financial transaction first, in its own short transaction.
- Creates the `SMSMessage` log row.
- Attempts delivery **outside** the financial transaction (e.g. via `transaction.on_commit()`), so a Hubtel failure can never roll back a valid disbursement or repayment.
- Uses explicit connect/read timeouts and redacts credentials from any log output.

Scheduled reminders run via `python manage.py process_due_sms`, protected by a PostgreSQL advisory lock (or equivalent DB-backed lock) against overlapping runs, and rely on a database uniqueness constraint (`installment + message_type + reminder_business_date + reminder_slot`) to make repeated scheduler invocations idempotent. No Redis, no Celery, no external queue.

## 10. Money handling

- `Decimal` and Django `DecimalField` everywhere money or rates are represented — `float` is never used.
- Two decimal places, `ROUND_HALF_UP`, quantized through one centralised money utility (`common/money`).
- Backend is the sole authority for financial calculations; any frontend number is a preview only.

## 11. Storage abstraction

A thin storage interface backs agreement PDFs, signature images, and payment evidence uploads: local filesystem (`MEDIA_ROOT`) in development, S3-compatible object storage in production, selected by `STORAGE_BACKEND`. Uploaded files get randomised names; user input never becomes part of a storage path. Agreement downloads go through an authorised endpoint or short-lived signed URL — never a public, guessable path.

## 12. Architecture Decision Records

Short-form ADRs for decisions locked at Stage 0. Format: Decision / Rationale / Alternatives considered / Status.

### ADR-001: Modular monolith, not microservices
- **Decision**: Single Django backend, single Next.js frontend, single PostgreSQL database.
- **Rationale**: Team size, MVP scope, and the master prompt's explicit non-goals rule out the operational cost of microservices for a system of this size.
- **Alternatives considered**: Service-per-domain split — rejected as premature.
- **Status**: Locked.

### ADR-002: No queue/broker (Redis, Celery, RabbitMQ, Kafka) for the MVP
- **Decision**: Scheduled SMS processing runs as an idempotent Django management command invoked by host/platform cron, not a queue worker.
- **Rationale**: Explicit master-prompt requirement; SMS volume at MVP scale does not need a broker, and a DB-backed lock plus uniqueness constraints give sufficient idempotency.
- **Alternatives considered**: Celery beat + worker — rejected as infrastructure the MVP does not need and the spec explicitly forbids.
- **Status**: Locked. Revisit only if SMS volume or latency requirements change materially post-MVP.

### ADR-003: Flat total-term interest as the only MVP amortization strategy, behind a strategy-shaped service
- **Decision**: Implement one interest method now; shape the calculator so a second method is an additive change.
- **Rationale**: Product scope specifies flat total-term interest only; over-building multiple strategies now would be speculative. Under-building (hard-coding the formula inline everywhere) would make a future reducing-balance method a rewrite.
- **Status**: Locked.

### ADR-004: Same-site deployment for Next.js + Django
- **Decision**: Prefer routing frontend and API under one trusted domain (`/`, `/api/`, `/accounts/`) rather than fully separate origins.
- **Rationale**: Enables `HttpOnly`/`SameSite` session cookies without cross-site cookie exceptions, avoids storing any token in `localStorage`, and simplifies CSRF handling.
- **Alternatives considered**: Fully separate origins with CORS + credentialed cookies — kept as a fallback option, documented in `DEPLOYMENT.md` when written in Stage 15, but not the default.
- **Status**: Locked as the default target; final domain routing confirmed in Stage 15.

### ADR-005: Repository root
- **Decision**: Treat `d:\Projects\Finsol_LMS` itself as the monorepo root (i.e. `backend/`, `frontend/`, `docs/`, etc. are created directly under it), rather than nesting everything inside an additional `loan-management-system/` wrapper folder as literally shown in the master prompt's example tree.
- **Rationale**: The existing repository root is already the intended project root; adding another nested wrapper folder would be redundant. The master prompt's tree is a shape reference, not a literal path requirement.
- **Status**: Locked for Stage 0 documentation placement. Open item for Stage 1: relocate or fold in `claude/CLAUDE_LOAN_MANAGEMENT_SYSTEM_MASTER_PROMPT.md` — left untouched for now per "do not overwrite existing work."

## 13. Environment reality check (Stage 0)

Local machine tooling observed during Stage 0 inspection (informational only, not a blocker — Docker supplies the authoritative runtime versions):

- Git 2.46.2 — available.
- Docker 29.6.1 / Docker Compose v5.3.0 — available; this is what Stage 1's `docker compose up --build` will rely on.
- Local Python: 3.10.11 — older than the master prompt's target (3.13). Not a blocker since the backend will run inside a Python 3.13 Docker image; flagged so a contributor running Django tooling outside Docker knows to use a matching virtualenv.
- Node.js / npm: not installed on this machine's PATH. Not a blocker since the frontend will run inside its own Docker image; flagged for the same reason.
- PostgreSQL client (`psql`): not installed locally — acceptable, since PostgreSQL runs as a Docker service per the spec (no local Postgres install required).

No repository-level lint/test/build checks were run in Stage 0 because no application code exists yet.
