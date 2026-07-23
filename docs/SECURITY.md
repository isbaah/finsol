# Security

Status: Requirements locked at Stage 0 (from Section 20–21 and Section 26 of the master prompt). Implemented incrementally from Stage 2 onward, verified fully in Stage 14. This document is a checklist and reference, not a certification — see "Disclaimers" at the end.

Reference standard: OWASP ASVS (used as a verification checklist reference only; no certification is claimed).

## 1. Authentication and session security

- `django-allauth[headless]` browser flows only — no custom password hashing, password reset, OAuth, or session implementation (Stage 2).
- Custom UUID-PK user model, created before the first migration (Stage 1).
- Email is the login identifier, unique via case-insensitive normalization enforced at the database level.
- Mandatory email verification for password-based accounts; unverified users are blocked from all protected business actions, not just gently discouraged.
- Google OAuth via django-allauth's Google provider, configured entirely from environment values — no hard-coded client ID/secret.
- Secure, `HttpOnly`, `SameSite` cookies in production. **No token of any kind in browser `localStorage`.**
- CSRF protection enforced on every cookie-authenticated unsafe request; CSRF is never disabled to make a request "work."
- Authentication throttling via supported framework mechanisms (Stage 2).
- Admin MFA support (django-allauth MFA) added in the Stage 14 hardening pass, before production launch.
- Admin session timeout configured in production settings.

## 2. Authorization

- Django Groups + permissions for the six logical roles (`CUSTOMER`, `LOAN_OFFICER`, `APPROVER`, `FINANCE_OFFICER`, `AUDITOR`, `SUPER_ADMIN`); a person may hold multiple roles.
- `is_superuser` is reserved for controlled technical administration — never the sole business authorisation mechanism.
- Every list queryset is filtered by role and ownership; object-level permission checks alone are not treated as sufficient for list endpoints.
- Critical actions (approve, disburse, post/reverse payment) are checked in **both** the DRF permission layer and the domain service layer, so a service is safe to call from anywhere (including a management command) without silently bypassing authorisation.
- Frontend button visibility is never treated as authorisation — every restricted action is enforced server-side regardless of what the UI shows.
- A customer can never retrieve another customer's data through any list or detail endpoint. This is treated as the single highest-priority data-isolation invariant in the system and is covered by dedicated tests at every relevant stage (see `TEST_PLAN.md`).

## 3. Transport, headers, and platform hardening

- Strict `ALLOWED_HOSTS`.
- Explicit CORS origins — never a wildcard combined with credentials.
- Content Security Policy where practical.
- HTTPS-only production configuration; secure proxy header configuration (`SECURE_PROXY_SSL_HEADER` etc. behind the reverse proxy).
- Django `DEBUG` is never enabled in production; no stack traces are ever returned to end users in production.
- Production settings fail startup loudly when a mandatory secret/config value is missing, rather than falling back to an insecure default.

## 4. Input handling and file uploads

- Backend validation is authoritative everywhere; frontend (Zod/React Hook Form) validation is a UX convenience only.
- Safe file-upload type and size validation (signature images, payment/disbursement evidence, agreement PDFs).
- Random file names on upload — user input never becomes part of a storage path.
- No user-controlled storage paths.
- CSV exports (Stage 13) are sanitised against spreadsheet formula injection.

## 5. Data protection specifics for this domain

- Payout details (bank account number, mobile-money number) are masked in all normal API responses and UI displays; full details are exposed only through an explicitly authorised, audited reveal workflow (disbursement modal, Stage 9).
- Full account details, passwords, session secrets, Hubtel credentials, and signature image bytes are never written to logs, SMS content, analytics events, or exception traces/stack traces.
- `AuditEvent.before`/`after` JSON is redacted before storage — the redaction rule is centralised in one helper, not reimplemented per call site.
- SMS templates never include full bank/mobile-money account numbers, identity numbers, passwords, signature information, or sensitive internal notes.
- Agreement PDF and payment-evidence file downloads go through an authorised endpoint or short-lived signed URL — never a public, guessable path.

## 6. Financial integrity as a security property

These are correctness rules, but are treated as security-relevant because they protect against fraud and accidental loss, and are restated here for completeness (full detail in `DATA_MODEL.md` / `STATUS_TRANSITIONS.md`):

- `Decimal` only for money/rates — `float` is never used.
- Authoritative amortization calculation happens only on the backend.
- No generic CRUD endpoint can edit a status field directly — every transition goes through an explicit, guarded service function.
- Posted payments, ledger entries, accepted offers, agreements, disbursements, and audit events are never updated or deleted — corrections are additive (reversal + new record).
- Disbursement and payment posting use idempotency protection against duplicate submission (double-click, retried request).
- Database constraints back critical invariants wherever the ORM can express them, rather than relying on application code alone.
- SMS or email failure never rolls back a valid financial transaction (Section 17).

## 7. Infrastructure and operations

- Database transactions stay short; slow work (Hubtel calls, email sending, PDF generation) happens outside the financial transaction, typically via `transaction.on_commit()`.
- Dependency vulnerability scanning in CI (Stage 14).
- Structured application logging with correlation/request IDs; sensitive values redacted (Section 21).
- Sentry (or comparable) error monitoring, added behind environment configuration in the hardening stage — never mandatory for local dev.
- Health endpoints: liveness and a readiness check that verifies database connectivity (Stage 1). No operational health detail is exposed to unauthenticated public users beyond a minimal status response.
- Daily encrypted backups in production, with a documented and tested restoration process (Stage 15).
- No secrets committed to the repository; `.env` files are gitignored; `.env.example` ships only safe placeholders, never real credentials.

## 8. CI and dependency hygiene

- Backend: Ruff (lint/format), Pytest, dependency scanning.
- Frontend: ESLint/Prettier (no disabled core safety rules merely to pass checks), Vitest, Playwright, `tsc` strict-mode typecheck.
- CI runs lint, typecheck, tests, and production builds for both sides before a change is considered done (Section 25, "Definition of Done").

## 9. Threat model notes (expanded in Stage 14)

Preliminary areas of concern to track, refine, and re-review at Stage 14 with the full application surface in place:

- **Insider misuse of the payout-reveal workflow** — mitigated by role restriction + mandatory audit event on every reveal.
- **Duplicate financial submission** (double-click, retried network request, or two staff acting on the same record concurrently) — mitigated by idempotency keys plus `select_for_update()` on critical rows.
- **SMS/email provider outage used to mask a financial dispute** — mitigated by the rule that SMS/email failure never blocks or reverses a financial transaction, and by making delivery status visible/queryable to staff.
- **Session fixation / CSRF on state-changing admin actions** — mitigated by allauth session handling + CSRF protection; explicitly re-tested at Stage 14.
- **Over-broad serializer exposure** — mitigated by never using `fields = '__all__'` on sensitive serializers and by maintaining separate serializers per audience (customer / admin-list / admin-detail / write).

## 10. Disclaimers

- OWASP ASVS is used as a reference checklist; no formal certification is claimed anywhere in documentation, UI copy, or communications.
- This system does **not** claim legal or regulatory compliance. Legal review of the loan agreement text and the digital-acceptance process is a mandatory launch gate (Stage 15), tracked as an explicit, non-hidden launch risk.

## 11. Traceability

Authentication/session controls: Stage 2. Roles/permissions: Stage 3. Financial-integrity controls: Stages 4, 8, 9, 10. Messaging-specific controls: Stage 11. Full hardening pass, CSP, MFA, throttles, dependency scanning, N+1/index review, and the complete ASVS-referenced sweep: Stage 14. See `BUILD_PROGRESS.md` for the full matrix.
