# Claude Code Master Build Prompt: Loan Management Web Application

> Copy this entire document into Claude Code at the root of the project. Claude must build the application **one stage at a time**, validate each stage, update the project documentation, and stop for approval before starting the next stage.

---

## 1. Your Role

Act as a principal software architect, senior Django engineer, senior Next.js engineer, database designer, security-minded reviewer, test engineer, and product designer.

Build a production-minded but deliberately lean **Loan Management Web Application**. The application must be maintainable, auditable, secure, responsive, and easy for another developer to understand.

This is not a hackathon prototype. Do not create a visually impressive shell with weak business logic. Correct loan states, amortization calculations, permissions, transaction integrity, auditability, and reliable SMS handling are more important than decorative features.

---

## 2. Mandatory Stage-Gated Working Method

You must not build the full application in one pass.

For every stage:

1. Inspect the current repository and existing implementation before changing anything.
2. Read this master prompt and `docs/BUILD_PROGRESS.md`.
3. State the goal of the current stage in a short implementation plan.
4. Identify any assumptions required for that stage.
5. Implement only the current stage.
6. Add or update automated tests for the work completed.
7. Run the relevant formatters, linters, type checks, tests, migrations, and production builds.
8. Fix all errors introduced by the stage.
9. Update documentation and `docs/BUILD_PROGRESS.md`.
10. Show:
    - files created or changed;
    - commands run;
    - tests passed;
    - unresolved risks or decisions;
    - the recommended next stage.
11. Stop and wait for the exact instruction **CONTINUE** before proceeding.

Do not silently skip a failed check. Do not claim a command passed unless it was actually run successfully.

Do not create Git commits unless explicitly instructed. At the end of each stage, suggest a concise commit message.

---

## 3. Product Summary

Build a web application through which:

1. A customer creates an account using:
   - a verified email address and password; or
   - Google sign-in.
2. The customer completes a basic profile, including a mobile number and preferred disbursement account.
3. The customer submits a loan request to an administrator.
4. An administrator reviews the request and creates an amortization offer.
5. The customer reviews the offer and can:
   - accept and digitally sign it;
   - reject it; or
   - request a revision.
6. After acceptance, a signed agreement PDF is generated and emailed to a configurable action email address. The initial value is `isbaah@gmail.com` and `isbaahjnr@gmail.com`, but it must never be hard-coded.
7. An authorised administrator approves the accepted loan for disbursement.
8. No money is transferred through the application.
9. The application displays a disbursement modal containing the customer’s verified payout details so the administrator can manually transfer funds outside the application.
10. The administrator then records the disbursement and its external reference.
11. The system sends Hubtel SMS confirmations to the customer and the configured admin mobile number.
12. Repayments are also received outside the application.
13. An administrator records each repayment manually.
14. After a repayment is recorded, the system sends Hubtel SMS confirmations containing the balance and the next repayment details.
15. Scheduled Hubtel SMS reminders are sent automatically:
    - five days before repayment;
    - two days before repayment;
    - one day before repayment;
    - on the due date in the morning;
    - on the due date later in the day if the installment remains outstanding.
16. The administrator sees a detailed portfolio dashboard.
17. The customer sees a deliberately simple dashboard showing their loan request, offer, balance, amortization schedule, payment history, and next payment.

---

## 4. Scope Assumptions for the MVP

Unless the product owner explicitly changes them before the relevant stage, use these assumptions:

- The system serves one lending organisation. It is **not multi-tenant**.
- The application language is English.
- The currency is Ghana cedi, code `GHS`, displayed as `GHS` rather than relying only on a currency symbol.
- The operating timezone is `Africa/Accra`.
- The first version supports manually recorded disbursements and repayments only.
- No payment gateway is included.
- No automatic mobile-money disbursement is included.
- Hubtel is used for operational SMS notifications and reminders.
- Email is used for account verification, password reset, and sending the signed agreement to the action mailbox.
- The MVP does not include credit scoring, credit bureau integration, automated underwriting, KYC verification, collections workflow automation, accounting-system integration, or a native mobile application.
- The user may have more than one historical loan. The data model must support multiple loans, even if a business rule later limits the number of simultaneous active loans.
- A customer must not be able to view another customer’s data.
- Administrators may hold one or more operational roles.
- The MVP amortization method is **flat total-term interest**. The percentage entered by the administrator is the total interest percentage for the entire loan term, not a monthly or annual rate. The implementation must clearly label this assumption in the UI and code. Design the calculation service so another interest strategy can be added later without rewriting the entire loan module.
- The loan term is entered as a number plus a unit of `WEEK` or `MONTH`.
- The number of installments equals the term count for the MVP.
- Repayment frequency equals the selected term unit for the MVP.
- No fees or penalties are included in the first calculation unless the product owner explicitly adds them later.
- The admin action email, admin SMS number, Hubtel credentials, sender ID, reminder times, and application URLs must be configuration values.

Document these assumptions in `docs/PRODUCT_ASSUMPTIONS.md`.

---

## 5. Explicit Non-Goals

The following are not part of the MVP:

- loan payments within the web application;
- automatic bank or mobile-money transfers;
- Paystack, Hubtel payments, Stripe, or other payment checkout flows;
- mobile push notifications;
- Firebase Cloud Messaging;
- WhatsApp notifications;
- a native iOS or Android app;
- microservices;
- Kubernetes;
- Redis;
- Celery;
- RabbitMQ;
- Kafka;
- event sourcing;
- a data warehouse;
- AI credit decisions;
- facial recognition;
- document OCR;
- automatic debt collection;
- automated late fees;
- tax or accounting calculations;
- multi-currency support;
- multi-language support;
- public loan marketplace features.

Keep the architecture extensible, but do not build speculative features.

---

## 6. Required Technology Stack

Use a simple monorepo with a separate frontend and backend.

### Backend

- Python 3.13 or another currently supported stable Python version compatible with the selected dependencies.
- Django 5.2 LTS, pinned to the latest available compatible patch release.
- Django REST Framework.
- PostgreSQL.
- `django-allauth[headless]` for email/password authentication, verified email flows, account management, and Google OAuth.
- `django-cors-headers` only where required for local development or separated origins.
- `django-filter` for API filtering.
- `drf-spectacular` for an OpenAPI schema.
- `psycopg` version 3.
- `httpx` for Hubtel HTTP integration, with explicit connect and read timeouts.
- `python-dateutil` for month-aware due-date calculations.
- `phonenumbers` for E.164 phone validation and normalization.
- WeasyPrint for server-side agreement PDF generation.
- Pillow for signature image validation where required.
- Pytest and pytest-django.
- Factory Boy for test factories.
- Freezegun for date-sensitive tests.
- Ruff for Python formatting and linting.
- Gunicorn for production WSGI serving.

### Frontend

- Current stable Next.js using the App Router.
- React and TypeScript with strict mode enabled.
- Tailwind CSS.
- shadcn/ui.
- Lucide React icons.
- Recharts for dashboard charts.
- TanStack Table for admin tables.
- TanStack Query for authenticated API data, caching, invalidation, and mutations.
- React Hook Form and Zod for forms and client validation.
- `date-fns` for display formatting only. The backend remains authoritative for financial dates and calculations.
- Sonner for toast messages.
- `signature_pad` or a thin React wrapper around it for signature capture.
- Vitest and React Testing Library.
- Playwright for end-to-end tests.
- ESLint and Prettier, or the current Next.js-supported equivalent, with no disabled core safety rules merely to make checks pass.

### Infrastructure

- Docker and Docker Compose for local development.
- PostgreSQL as a container in local development.
- Separate frontend and backend containers.
- No Redis container.
- No Celery worker.
- Scheduled SMS processing through a Django management command invoked by the deployment platform’s scheduler or host cron.
- Nginx or Caddy may be used in production to place the frontend and API under one trusted domain.

Before pinning versions, consult current official documentation and use compatible stable releases. Do not use prerelease dependencies unless explicitly approved.

---

## 7. Target Repository Structure

Use this structure unless the existing repository requires a well-justified adaptation:

```text
loan-management-system/
├── backend/
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── local.py
│   │   │   ├── test.py
│   │   │   └── production.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   ├── apps/
│   │   ├── accounts/
│   │   ├── customers/
│   │   ├── loan_requests/
│   │   ├── loan_offers/
│   │   ├── agreements/
│   │   ├── loans/
│   │   ├── repayments/
│   │   ├── messaging/
│   │   ├── dashboards/
│   │   └── audit/
│   ├── common/
│   │   ├── api/
│   │   ├── db/
│   │   ├── money/
│   │   ├── permissions/
│   │   └── tests/
│   ├── integrations/
│   │   ├── hubtel/
│   │   ├── email/
│   │   └── storage/
│   ├── templates/
│   │   └── agreements/
│   ├── tests/
│   ├── manage.py
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── (auth)/
│   │   │   ├── (customer)/
│   │   │   ├── (admin)/
│   │   │   └── api/
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   ├── auth/
│   │   │   ├── dashboard/
│   │   │   ├── loans/
│   │   │   ├── repayments/
│   │   │   └── shared/
│   │   ├── features/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── providers/
│   │   ├── schemas/
│   │   ├── types/
│   │   └── tests/
│   ├── public/
│   ├── package.json
│   ├── next.config.ts
│   └── Dockerfile
├── docs/
│   ├── BUILD_PROGRESS.md
│   ├── PRODUCT_ASSUMPTIONS.md
│   ├── ARCHITECTURE.md
│   ├── DATA_MODEL.md
│   ├── STATUS_TRANSITIONS.md
│   ├── API.md
│   ├── SECURITY.md
│   ├── SMS_TEMPLATES.md
│   ├── TEST_PLAN.md
│   ├── DEPLOYMENT.md
│   └── RUNBOOK.md
├── infra/
│   └── reverse-proxy/
├── scripts/
├── .github/
│   └── workflows/
├── .env.example
├── docker-compose.yml
├── Makefile
├── README.md
└── .gitignore
```

Keep modules cohesive. Avoid files that grow into unreviewable “god files.”

---

## 8. High-Level Architecture

```text
Customer or Admin Browser
          │
          ▼
Next.js Web Application
          │ HTTPS, same trusted site where possible
          ▼
Django REST API
   ├── Authentication and permissions
   ├── Loan request workflow
   ├── Amortization service
   ├── Agreement and signature service
   ├── Loan state machine
   ├── Disbursement recording
   ├── Repayment ledger
   ├── Dashboard queries
   ├── Audit logging
   └── SMS orchestration
          │
          ├── PostgreSQL
          ├── Hubtel SMS API
          ├── SMTP/transactional email provider
          └── File/object storage

Deployment scheduler or host cron
          │
          ▼
Django management command
`python manage.py process_due_sms`
          │
          ▼
Hubtel SMS API
```

Use a modular monolith. Business modules communicate through explicit service functions, not direct uncontrolled cross-module model mutations.

---

## 9. Authentication and Session Architecture

This is a browser-based web application.

Use django-allauth headless **browser** flows with secure server-side sessions and CSRF protection. Prefer same-site deployment, for example:

```text
https://loans.example.com          -> Next.js
https://loans.example.com/api/     -> Django
https://loans.example.com/accounts -> django-allauth provider callbacks
```

Requirements:

- Create a custom Django user model before the first migration.
- Use UUID primary keys.
- Email is the primary login identifier.
- Email addresses are unique using case-insensitive normalization and database enforcement.
- Email verification is mandatory for password-based accounts.
- Google OAuth is supported through django-allauth.
- A Google user must still complete any required customer profile fields after first login.
- Use secure, HTTP-only, same-site cookies in production.
- Enforce CSRF protection for cookie-authenticated unsafe requests.
- Do not store access tokens or session tokens in browser `localStorage`.
- Do not invent a custom password-reset or OAuth implementation.
- Add login throttling/rate limits using supported framework mechanisms.
- Admin accounts must be capable of MFA in a later hardening stage; prefer django-allauth MFA rather than a custom implementation.
- Unverified users must not submit loan requests.

The frontend should have:

```text
/auth/login
/auth/signup
/auth/verify-email
/auth/forgot-password
/auth/reset-password
/auth/google/callback or the appropriate provider callback flow
/onboarding/profile
```

---

## 10. Roles and Permissions

Use Django Groups and permissions, plus explicit DRF permission classes and queryset filtering.

Required logical roles:

- `CUSTOMER`
- `LOAN_OFFICER`
- `APPROVER`
- `FINANCE_OFFICER`
- `AUDITOR`
- `SUPER_ADMIN`

A person may hold more than one internal role.

### Permission principles

- Customers can access only their own profile, requests, offers, agreements, loans, schedules, and payments.
- Loan officers can review requests and draft/send offers.
- Approvers can approve accepted loans.
- Finance officers can record disbursements and repayments.
- Auditors have read-only access to operational and audit records.
- Super administrators can manage users, roles, settings, and all records.
- Django `is_superuser` is reserved for controlled technical administration and is not the only business authorisation mechanism.
- Every list queryset must be filtered by role and ownership; object-level permission checks alone are insufficient for list security.
- Critical actions must be checked in both the API permission layer and the domain service layer.
- Never rely on hiding a frontend button as authorisation.

Create an idempotent management command such as:

```bash
python manage.py seed_roles
```

It must create or update groups and permissions without duplicating data.

---

## 11. Core Workflow and State Machines

Do not use one overloaded status field for the whole product. Keep request, offer, loan, installment, payment, agreement, and SMS states distinct.

### Loan request status

```text
DRAFT
SUBMITTED
UNDER_REVIEW
OFFER_SENT
CUSTOMER_ACCEPTED
CUSTOMER_REJECTED
REVISION_REQUESTED
APPROVED
DECLINED
CANCELLED
CONVERTED_TO_LOAN
```

### Offer status

```text
DRAFT
SENT
SUPERSEDED
ACCEPTED
REJECTED
EXPIRED
```

Rules:

- A request may have multiple versioned offers.
- Only one offer version can be current at a time.
- Sending a revised offer supersedes the previous sent offer.
- An accepted offer becomes immutable.
- Only the current sent offer can be accepted.
- Acceptance must atomically mark the offer accepted and update the request.

### Loan status

```text
PENDING_APPROVAL
APPROVED_FOR_DISBURSEMENT
DISBURSED
ACTIVE
PAID_OFF
OVERDUE
RESTRUCTURED
DEFAULTED
CANCELLED
```

Rules:

- Customer acceptance does not equal approval.
- Approval does not equal disbursement.
- Disbursement does not equal repayment.
- Recording a repayment does not mean the loan is fully paid.
- A loan becomes active only after the disbursement is recorded.
- A loan is paid off only when the authoritative outstanding balance reaches zero.
- Overdue status is derived from unpaid installments past their due date, but status changes must still be recorded and auditable.

### Installment status

```text
UPCOMING
DUE
PARTIALLY_PAID
PAID
OVERDUE
WAIVED
```

### Payment status

```text
POSTED
REVERSED
```

### SMS status

```text
PENDING
PROCESSING
SENT
DELIVERED
FAILED
CANCELLED
```

Implement allowed transitions in service functions. Reject invalid transitions with a domain-specific error and an appropriate API response. Use `transaction.atomic()` and `select_for_update()` for critical state transitions.

Document the complete transition matrix in `docs/STATUS_TRANSITIONS.md`.

---

## 12. Data Model Requirements

Use UUID primary keys for externally referenced domain objects. Include `created_at` and `updated_at` timestamps on mutable records. Use timezone-aware datetimes.

### 12.1 User

Minimum fields:

- `id`
- `email`
- `first_name`
- `last_name`
- `is_active`
- `is_staff`
- `date_joined`
- allauth-related fields and relationships

### 12.2 CustomerProfile

Minimum fields:

- `id`
- `user`, one-to-one
- `phone_number_e164`
- `phone_country_code`
- `address_line_1`, optional
- `address_line_2`, optional
- `city`, optional
- `country`, default `GH`
- `preferred_disbursement_method`: `MOBILE_MONEY` or `BANK`
- mobile-money network, where applicable
- mobile-money number, where applicable
- bank name, where applicable
- bank account name, where applicable
- bank account number, where applicable
- `profile_completed_at`
- `created_at`
- `updated_at`

Validation:

- Normalize phone numbers to E.164.
- Require the correct fields for the selected payout method.
- Mask account details in normal API responses and UI displays.
- Expose full payout details only to appropriately authorised staff and only in the disbursement workflow.
- Never put full account details in logs, SMS messages, analytics, or exception traces.

### 12.3 LoanRequest

Minimum fields:

- `id`
- human-readable `request_number`
- `customer`
- `requested_amount`
- `purpose`
- optional requested term count and unit
- payout details snapshot or a reference to the approved profile version
- `status`
- `submitted_at`
- `assigned_to`, optional
- customer notes
- internal admin notes, never exposed to customers
- `created_at`
- `updated_at`

### 12.4 LoanOffer

Minimum fields:

- `id`
- `loan_request`
- `version_number`
- `status`
- `principal`
- `interest_method`, initially `FLAT_TOTAL_TERM`
- `interest_rate_percent`
- `term_count`
- `term_unit`: `WEEK` or `MONTH`
- `first_due_date`
- `total_interest`
- `total_repayable`
- `installment_count`
- optional offer expiry date
- customer-facing terms
- internal notes
- `created_by`
- `sent_by`, optional
- `sent_at`, optional
- `accepted_at`, optional
- `created_at`
- `updated_at`

Constraints:

- Unique version per request.
- Principal greater than zero.
- Interest percentage not negative.
- Term count greater than zero and within documented safe bounds.
- Accepted fields and calculated totals cannot be edited after acceptance.

### 12.5 OfferInstallment

This is the immutable proposed schedule for an offer.

Fields:

- `offer`
- `sequence_number`
- `due_date`
- `principal_due`
- `interest_due`
- `total_due`

Constraint: unique `(offer, sequence_number)`.

### 12.6 Agreement

Minimum fields:

- `id`
- one-to-one `offer`
- `customer`
- typed legal name
- acceptance checkbox text/version
- signature image file path
- signature image SHA-256 hash
- generated agreement PDF path
- agreement PDF SHA-256 hash
- accepted IP address
- accepted user agent
- accepted timestamp
- email delivery status
- email provider reference, if available
- `created_at`

Agreement records are immutable after successful creation. Corrections require a new offer/agreement process, not editing the accepted record.

### 12.7 Loan

Minimum fields:

- `id`
- human-readable `loan_number`
- `customer`
- `loan_request`
- `accepted_offer`
- `agreement`
- `status`
- `principal`
- `total_interest`
- `total_repayable`
- `amount_disbursed`
- `amount_repaid`
- `outstanding_balance`
- `approved_by`, optional
- `approved_at`, optional
- `disbursed_at`, optional
- `closed_at`, optional
- `created_at`
- `updated_at`

Use authoritative ledger calculations and reconciliation checks. Do not trust a frontend balance.

### 12.8 RepaymentInstallment

This is the active servicing schedule copied from the accepted offer when the loan is created.

Fields:

- `loan`
- `sequence_number`
- `due_date`
- `principal_due`
- `interest_due`
- `total_due`
- `amount_paid`
- `outstanding_amount`
- `status`
- `paid_at`, optional
- `created_at`
- `updated_at`

Constraint: unique `(loan, sequence_number)`.

### 12.9 Disbursement

MVP supports one full disbursement per loan, but model it explicitly.

Fields:

- `id`
- `loan`
- `amount`
- `method`
- masked payout destination snapshot
- external transaction reference
- payment evidence file, optional
- notes
- `recorded_by`
- `recorded_at`
- `created_at`

Constraints:

- One active disbursement record per MVP loan.
- External reference must be unique when supplied.
- Amount must match the approved disbursement amount unless an authorised exception process is added later.

### 12.10 Payment

Fields:

- `id`
- human-readable `receipt_number`
- `loan`
- `amount`
- `payment_date`
- `payment_method`
- external transaction reference
- evidence file, optional
- notes
- `status`: `POSTED` or `REVERSED`
- `recorded_by`
- `recorded_at`
- reversal relationship and reason, where applicable
- `created_at`

Rules:

- Never edit a posted financial payment to “correct” it.
- Reverse the original and post a new correct payment.
- Enforce idempotency against accidental double submission.
- External reference should be unique when provided.

### 12.11 PaymentAllocation

Fields:

- `payment`
- `installment`
- `principal_amount`
- `interest_amount`
- `total_amount`

Allocations must add up exactly to the posted payment amount, subject to any explicitly defined unapplied amount rule.

### 12.12 LoanTransaction

Create an append-only ledger table.

Transaction types:

```text
DISBURSEMENT
REPAYMENT
REVERSAL
ADJUSTMENT
WRITE_OFF
```

Minimum fields:

- `loan`
- `transaction_type`
- signed amount or explicit debit/credit fields
- effective date
- source object type and ID
- balance after transaction
- `recorded_by`
- reason
- `created_at`

Do not expose update or delete API actions for ledger entries.

### 12.13 SMSMessage

Fields:

- `id`
- related customer, loan, and installment where applicable
- `message_type`
- `recipient_phone_e164`
- `message_body`
- `scheduled_for`
- reminder slot where applicable
- `status`
- `provider_message_id`
- provider response code
- attempt count
- `next_attempt_at`
- `sent_at`
- `delivered_at`
- `failed_at`
- last error summary
- `created_at`
- `updated_at`

Use uniqueness constraints for scheduled reminders so repeated scheduler runs cannot duplicate a reminder.

### 12.14 AuditEvent

Append-only fields:

- `actor`, nullable for system events
- actor role snapshot
- action code
- entity type
- entity ID
- before JSON, carefully redacted
- after JSON, carefully redacted
- request correlation ID
- IP address
- user agent
- reason, where required
- `created_at`

Never record passwords, session secrets, Hubtel credentials, full bank account details, full mobile-money details, or signature image bytes in audit JSON.

---

## 13. Money and Amortization Rules

### Decimal handling

- Never use binary floating-point values for money or rates.
- Use Python `Decimal` and Django `DecimalField`.
- Use two decimal places for GHS amounts.
- Use an explicit rounding mode, normally `ROUND_HALF_UP`.
- Centralise quantization in a money utility.
- Frontend calculations are previews only. The backend generates and persists the authoritative schedule.

### MVP flat total-term calculation

```text
principal = administrator-entered principal
rate = total-term interest percentage / 100
total_interest = principal × rate
total_repayable = principal + total_interest
installment_count = term_count
```

Split principal and interest across installments. Adjust the final installment by any rounding residue so that:

```text
sum(principal_due) == principal
sum(interest_due) == total_interest
sum(total_due) == total_repayable
```

### Due dates

- Admin enters a first due date.
- Weekly term: add exact seven-day increments.
- Monthly term: add calendar months using `relativedelta(months=1)`.
- For months lacking the same day number, use the valid end-of-month behavior and test it.
- Store dates as dates, not midnight datetimes.
- Display dates in an unambiguous format such as `24 Sep 2026`.

### Calculation service

Create a pure, deterministic domain service, for example:

```text
AmortizationCalculator.calculate(input) -> AmortizationResult
```

The service must not depend on HTTP requests or mutate database state. Persist the result in a separate application service.

Test at minimum:

- zero-interest loan;
- normal interest loan;
- principal that creates rounding residue;
- one installment;
- weekly schedule;
- monthly schedule;
- January 31 date progression;
- leap-year dates;
- invalid negative amount;
- invalid term;
- exact sum reconciliation.

---

## 14. API Design Principles

- Version the business API under `/api/v1/`.
- Use RESTful resources plus explicit action endpoints for state transitions.
- Generate and maintain OpenAPI documentation.
- Return consistent JSON error objects.
- Validate on both frontend and backend, with backend authoritative.
- Paginate administrative lists.
- Support filtering, search, and ordering on admin tables.
- Avoid exposing internal model fields automatically through broad `ModelSerializer(fields='__all__')` usage.
- Use separate serializers for customer views, admin list views, admin details, and write actions.
- Use idempotency keys or equivalent server-side duplicate protection for disbursement and payment posting.
- Use `select_related` and `prefetch_related` to prevent obvious N+1 queries.
- Do not expose sequential database IDs.

### Suggested customer endpoints

```text
GET    /api/v1/me/
PATCH  /api/v1/me/profile/
GET    /api/v1/customer/dashboard/
GET    /api/v1/customer/loan-requests/
POST   /api/v1/customer/loan-requests/
GET    /api/v1/customer/loan-requests/{id}/
GET    /api/v1/customer/offers/{id}/
POST   /api/v1/customer/offers/{id}/accept/
POST   /api/v1/customer/offers/{id}/reject/
POST   /api/v1/customer/offers/{id}/request-revision/
GET    /api/v1/customer/loans/
GET    /api/v1/customer/loans/{id}/
GET    /api/v1/customer/loans/{id}/schedule/
GET    /api/v1/customer/loans/{id}/payments/
GET    /api/v1/customer/agreements/{id}/download/
```

### Suggested admin endpoints

```text
GET    /api/v1/admin/dashboard/overview/
GET    /api/v1/admin/dashboard/monthly-collections/
GET    /api/v1/admin/loan-requests/
GET    /api/v1/admin/loan-requests/{id}/
POST   /api/v1/admin/loan-requests/{id}/assign/
POST   /api/v1/admin/loan-requests/{id}/mark-under-review/
POST   /api/v1/admin/loan-requests/{id}/offers/
POST   /api/v1/admin/offers/{id}/send/
POST   /api/v1/admin/loan-requests/{id}/decline/
GET    /api/v1/admin/loans/
GET    /api/v1/admin/loans/{id}/
POST   /api/v1/admin/loans/{id}/approve/
POST   /api/v1/admin/loans/{id}/record-disbursement/
POST   /api/v1/admin/loans/{id}/record-payment/
POST   /api/v1/admin/payments/{id}/reverse/
GET    /api/v1/admin/repayments/upcoming/
GET    /api/v1/admin/repayments/overdue/
POST   /api/v1/admin/installments/{id}/send-sms/
GET    /api/v1/admin/sms-messages/
POST   /api/v1/admin/sms-messages/{id}/retry/
GET    /api/v1/admin/audit-events/
GET    /api/v1/admin/exports/loans.csv
GET    /api/v1/admin/exports/repayments.csv
```

Use exact endpoint names appropriate to the final implementation, but keep transition actions explicit and auditable.

---

## 15. Customer Experience Requirements

The customer interface must be simple and calm.

### Customer navigation

- Dashboard
- Request Loan
- My Loans
- Payments
- Documents
- Profile
- Sign Out

### Customer dashboard

Show only the most important information:

1. Primary action: **Request a Loan**.
2. Current request status.
3. Current offer card when an offer is awaiting review.
4. Active loan summary:
   - original principal;
   - amount repaid;
   - outstanding balance;
   - next payment amount;
   - next payment date;
   - status.
5. Compact repayment schedule.
6. Recent payment history.
7. Agreement download.

### Loan request form

Suggested fields:

- requested amount;
- loan purpose;
- preferred term count;
- preferred term unit;
- payout method and destination confirmation;
- declaration that information is accurate.

The request form must clearly state that the administrator determines final terms.

### Offer review page

Display:

- principal;
- total-term interest rate and clear explanation;
- total interest amount;
- total repayable;
- number of installments;
- first due date;
- final due date;
- complete amortization schedule;
- customer-facing terms;
- accept, reject, and request-revision actions.

Do not bury total repayable or repayment dates.

### Signature experience

The acceptance flow must require:

- a visible final offer summary;
- confirmation checkbox with versioned acceptance text;
- typed full legal name;
- drawn signature;
- final confirmation dialog;
- successful PDF generation before showing completion.

After acceptance, show that the offer is locked and available as a downloadable agreement.

---

## 16. Admin Experience and Dashboard Design

The admin dashboard should resemble a modern CRM dashboard: white content surfaces, subtle grey borders, generous whitespace, rounded cards, restrained shadows, a light neutral page background, a compact left sidebar, and a single primary blue accent.

It should feel corporate and operational, not decorative or like generic “AI-generated” software.

### Visual rules

- Desktop-first dashboard with fully responsive tablet/mobile behavior.
- White cards on a very light grey or cool neutral background.
- Card radius approximately 12–16px.
- Thin neutral borders.
- Small, consistent shadows only where useful.
- Clear hierarchy and strong spacing.
- Use green for positive/current states.
- Use amber for upcoming attention.
- Use red for overdue or failed states.
- Never rely on colour alone; include labels or icons.
- Use Lucide icons consistently.
- Avoid gradients except subtle chart fills.
- No oversized hero headings in the authenticated application.
- No glassmorphism.
- No neon colours.
- No excessive animation.
- Respect reduced-motion preferences.

### Admin sidebar

Suggested navigation:

- Dashboard
- Loan Requests
- Offers
- Active Loans
- Repayments
- Customers
- SMS Activity
- Reports
- Audit Log
- Settings

### Top metric cards

Show at least:

- Outstanding portfolio balance
- Amount due this month
- Amount collected this month
- Overdue amount
- Active loans

Each metric definition must be documented and tested.

### Main dashboard chart

Create an expected-versus-collected monthly chart with:

- expected repayments;
- actual posted repayments;
- six-month and twelve-month views;
- meaningful empty states;
- accessible tooltip labels;
- values formatted in GHS.

### New loan requests table

Columns:

- Request number
- Customer
- Requested amount
- Submission date
- Purpose
- Status
- Assigned officer
- Action

### Upcoming repayments table

Show installments due in fewer than seven days.

Columns:

- Customer
- Loan number
- Amount due
- Outstanding amount
- Due date
- Days remaining
- Last SMS status
- Actions

Actions:

- View loan
- Send SMS now
- Record payment
- View SMS history

Do not add a generic email-reminder action. Operational reminders are through Hubtel SMS. Email is reserved for account and agreement workflows.

### Overdue table

Show overdue age buckets:

- 1–7 days
- 8–30 days
- 31–60 days
- 61+ days

### Disbursement modal

Before an admin records disbursement, show:

- customer name;
- loan number;
- approved amount;
- payout method;
- mobile-money network or bank;
- masked account detail with an authorised reveal action;
- account name;
- copy buttons;
- a warning to independently verify the destination;
- external transaction reference field;
- disbursement date;
- optional evidence upload;
- confirmation checkbox;
- final **Record Disbursement** button.

Do not label this action merely “Paid.” Use precise financial language.

### Payment modal

Show:

- customer and loan;
- current outstanding balance;
- due installment;
- amount received;
- payment date;
- payment method;
- external reference;
- optional evidence;
- resulting allocation preview;
- resulting balance and next payment preview;
- final confirmation.

The backend recalculates the authoritative result.

---

## 17. Hubtel SMS Integration

All Hubtel credentials and sender information are backend-only secrets.

### Configuration

Use environment variables such as:

```text
HUBTEL_ENABLED=false
HUBTEL_BASE_URL=
HUBTEL_CLIENT_ID=
HUBTEL_CLIENT_SECRET=
HUBTEL_SENDER_ID=
HUBTEL_ADMIN_PHONE_E164=
HUBTEL_CONNECT_TIMEOUT_SECONDS=5
HUBTEL_READ_TIMEOUT_SECONDS=10
HUBTEL_MAX_REQUESTS_PER_MINUTE=
SMS_DRY_RUN=true
SMS_DUE_MORNING_TIME=08:00
SMS_DUE_AFTERNOON_TIME=16:00
APP_TIME_ZONE=Africa/Accra
```

Do not put real credentials in `.env.example`.

### Integration design

Create a provider-neutral interface, for example:

```text
SMSProvider.send(message) -> SMSProviderResult
SMSProvider.get_status(provider_message_id) -> SMSDeliveryResult
```

Implement `HubtelSMSProvider` behind that interface.

Use Hubtel’s authenticated SMS endpoint, E.164 recipient format, approved sender ID, message ID, and final status query according to current official documentation.

Do not let loan views call raw Hubtel URLs. Route SMS through the messaging application service.

### Required SMS types

```text
LOAN_OFFER_READY
OFFER_ACCEPTED_CUSTOMER
OFFER_ACCEPTED_ADMIN
LOAN_APPROVED
LOAN_DISBURSED_CUSTOMER
LOAN_DISBURSED_ADMIN
PAYMENT_RECEIVED_CUSTOMER
PAYMENT_RECEIVED_ADMIN
REPAYMENT_DUE_5_DAYS
REPAYMENT_DUE_3_DAYS
REPAYMENT_DUE_2_DAYS
REPAYMENT_DUE_1_DAY
REPAYMENT_DUE_TODAY_MORNING
REPAYMENT_DUE_TODAY_AFTERNOON
REPAYMENT_OVERDUE
LOAN_PAID_OFF_CUSTOMER
LOAN_PAID_OFF_ADMIN
MANUAL_REMINDER
```

### Message rules

- Keep normal messages concise and preferably within one SMS segment where practical.
- Include the lender name, customer first name, amount, loan reference, and due date where relevant.
- Do not include full bank account numbers, full mobile-money numbers, identity numbers, passwords, signature information, or sensitive internal comments.
- Include a support contact where configured.
- Store the exact rendered message sent for audit purposes.
- Customer and admin messages may use different templates.

### Immediate event SMS

For events such as disbursement and repayment:

1. Validate and commit the financial transaction first.
2. Create the SMS log record.
3. Attempt Hubtel delivery outside the critical financial database transaction.
4. Catch network and provider failures.
5. Never roll back a valid disbursement or repayment because SMS failed.
6. Mark the message failed or pending retry.
7. Show the admin the financial action succeeded even if the SMS did not.

Use explicit HTTP timeouts and redact credentials from logs.

### Scheduled reminders without a queue

Do not add Redis or Celery.

Create an idempotent management command:

```bash
python manage.py process_due_sms
```

Optional safe flags:

```bash
python manage.py process_due_sms --dry-run
python manage.py process_due_sms --now "2026-09-15T08:00:00+00:00"
python manage.py process_due_sms --limit 50
```

The command must:

1. Acquire a database-backed lock or PostgreSQL advisory lock to avoid overlapping runs.
2. Determine the current Accra date and reminder slot.
3. Find outstanding installments matching the reminder windows.
4. Create missing scheduled SMS records using database uniqueness constraints.
5. Skip fully paid installments.
6. Use the remaining installment amount for partially paid installments.
7. Send due records in a controlled batch.
8. Respect configurable Hubtel rate limits.
9. Retry eligible failed messages according to configurable attempt limits and `next_attempt_at`.
10. Store provider message IDs and response summaries.
11. Exit non-zero only for genuine command-level failure, not one individual SMS failure.
12. Produce useful structured logs without exposing sensitive data.

Schedule it every 15 minutes or hourly, depending on deployment capability. The command itself decides whether a reminder slot is due.

Create a second command or optional mode to query final Hubtel delivery status for messages that have a provider ID but are not yet final.

### Duplicate prevention

Use a uniqueness rule similar to:

```text
installment + message_type + reminder_business_date + reminder_slot
```

A manual reminder is a separate explicit message and may be sent more than once, but it must record the admin actor and reason.

---

## 18. Digital Acceptance and Agreement PDF

The system must not treat a signature image alone as the entire acceptance record.

Capture and persist:

- accepted offer ID and version;
- exact customer-facing terms version;
- typed legal name;
- drawn signature image;
- authenticated customer ID;
- timestamp;
- IP address;
- user agent;
- SHA-256 hash of the signature file;
- SHA-256 hash of the generated agreement PDF.

Generate a professional PDF containing:

- lender identity placeholders;
- customer details;
- loan request and offer references;
- principal;
- interest method and percentage;
- total interest;
- total repayable;
- term;
- amortization table;
- customer-facing terms;
- acceptance statement;
- typed name;
- signature image;
- acceptance timestamp;
- document reference and hash.

Store PDFs using a storage abstraction:

- local media storage in development;
- S3-compatible object storage or another managed object store in production.

After successful generation, email the PDF to:

```text
AGREEMENT_ACTION_EMAIL=isbaah@gmail.com
```

This value is configurable and must not be embedded in source code.

If email fails:

- do not undo the customer’s valid acceptance;
- mark agreement email delivery failed;
- expose a controlled admin retry action;
- retain the generated agreement in the portal.

Do not claim that the implementation has legal validity or regulatory approval. Add a production launch checklist item requiring legal review of the agreement text and acceptance process.

---

## 19. Repayment Allocation and Ledger Rules

For the MVP, allocate payments to the oldest outstanding installment first.

Within an installment, allocate in this order:

1. interest due;
2. principal due.

Document the rule clearly and centralise it in one service.

Support:

- exact installment payments;
- partial payments;
- payments covering multiple installments;
- final payoff;
- controlled overpayment rejection or an explicit unapplied-credit rule. For the MVP, reject amounts greater than the loan outstanding balance unless an authorised override workflow is explicitly added.

Use database transactions and row locking when posting or reversing payments.

After posting a payment:

- create the payment;
- create allocation rows;
- create ledger transaction;
- update installment balances and statuses;
- reconcile the loan balance;
- update the loan status if paid off or no longer overdue;
- record audit events;
- create customer and admin SMS messages;
- calculate the next unpaid installment.

After reversal:

- create an explicit reversal record and ledger transaction;
- reverse allocations safely;
- recalculate balances and statuses;
- preserve the original record;
- require a reason;
- audit the action.

Create reconciliation checks that assert:

```text
loan amount repaid == sum(active posted payments)
loan outstanding == total repayable - amount repaid
installment outstanding == installment total due - allocated active payments
```

Add a management command to report reconciliation differences without changing records automatically.

---

## 20. Audit and Security Requirements

Use OWASP ASVS as a security verification reference. Do not claim certification.

Mandatory controls:

- secure session cookies in production;
- CSRF protection;
- strict allowed hosts;
- explicit CORS origins, never wildcard with credentials;
- Content Security Policy where practical;
- HTTPS-only production configuration;
- secure proxy header configuration;
- password validation;
- authentication throttling;
- role and object permissions;
- input validation;
- safe file upload type and size validation;
- random file names;
- no user-controlled storage paths;
- database constraints for critical invariants;
- short database transactions;
- `transaction.on_commit()` where post-commit side effects are appropriate;
- audit events for all financial and approval actions;
- sensitive value redaction in logs;
- no stack traces returned to users in production;
- structured application logging;
- dependency vulnerability checks in CI;
- daily encrypted backups in production;
- documented restoration test process;
- admin session timeout;
- MFA support for internal users before production launch;
- protection against double clicks and repeated requests on financial actions;
- file access authorisation for agreements and evidence;
- customer agreement downloads through authorised endpoints or short-lived signed URLs.

Use secure defaults in production settings and fail startup when mandatory secrets are missing.

---

## 21. Logging and Observability

- Use structured logs with correlation/request IDs.
- Log important state transitions without logging sensitive payloads.
- Integrate Sentry or a comparable error-monitoring service behind environment configuration in the hardening stage.
- Provide health endpoints:
  - liveness;
  - readiness with database connectivity.
- Record scheduler run summaries.
- Admin dashboard should show SMS sent, delivered, failed, and pending counts.
- Do not expose operational health details to unauthenticated public users beyond a minimal status response.

---

## 22. Testing Strategy

### Backend tests

Include:

- model constraint tests;
- service-layer unit tests;
- amortization tests;
- state-transition tests;
- permission tests;
- customer data isolation tests;
- API contract tests;
- payment allocation tests;
- reversal tests;
- reconciliation tests;
- SMS template tests;
- SMS duplicate-prevention tests;
- scheduler time-window tests;
- Hubtel success, timeout, 4xx, 5xx, and malformed-response tests using mocked HTTP;
- agreement hash and immutability tests;
- email failure handling tests;
- file access tests;
- dashboard metric tests.

### Frontend tests

Include:

- form validation tests;
- auth-route protection tests;
- role-based navigation tests;
- money and date display tests;
- offer review tests;
- signature validation tests;
- admin modal tests;
- table empty/loading/error states;
- accessibility checks for key pages where practical.

### End-to-end tests

At minimum:

1. Email signup, verification, profile completion, and loan request.
2. Google sign-in path using an appropriate test strategy or mocked provider boundary.
3. Admin reviews request and sends offer.
4. Customer reviews and signs offer.
5. Agreement is generated.
6. Approver approves loan.
7. Finance officer records manual disbursement.
8. Customer sees active loan.
9. Finance officer records partial payment.
10. Balance and next payment update correctly.
11. Finance officer records final payment.
12. Loan becomes paid off.
13. Customer cannot access another customer’s loan.
14. Loan officer cannot perform finance-only actions.

No stage is complete if its relevant tests are missing or failing.

---

## 23. Developer Experience Requirements

Create a `Makefile` or equivalent commands:

```text
make setup
make dev
make stop
make logs
make migrate
make makemigrations
make seed
make test
make test-backend
make test-frontend
make lint
make format
make typecheck
make build
make sms-dry-run
make reconcile
```

Create `.env.example` with descriptions and safe placeholder values.

Create a root README with:

- prerequisites;
- setup instructions;
- Docker workflow;
- authentication setup;
- Google OAuth setup;
- Hubtel setup;
- email setup;
- running the scheduler;
- tests;
- production notes;
- troubleshooting.

Use migrations for every schema change. Never instruct a developer to manually edit the database to make the application work.

---

# 24. Sequential Build Stages

## Stage 0 — Repository Assessment and Architecture Lock

### Objective

Understand the current repository, lock MVP assumptions, and create the documentation skeleton before implementation.

### Tasks

- Inspect files, Git status, package manifests, and any existing code.
- Do not overwrite existing useful work.
- Create or update:
  - `docs/PRODUCT_ASSUMPTIONS.md`
  - `docs/ARCHITECTURE.md`
  - `docs/DATA_MODEL.md`
  - `docs/STATUS_TRANSITIONS.md`
  - `docs/SECURITY.md`
  - `docs/TEST_PLAN.md`
  - `docs/BUILD_PROGRESS.md`
- Add concise architecture decision records if useful.
- Document unresolved product decisions.
- Produce an implementation map linking each requirement to a build stage.

### Acceptance criteria

- Architecture, scope, state machines, and assumptions are documented.
- No application feature code is implemented unless needed to preserve existing work.
- The next stage has a precise plan.

Stop and wait for **CONTINUE**.

---

## Stage 1 — Project Foundation and Local Development

### Objective

Create a reproducible, healthy monorepo foundation.

### Backend tasks

- Initialise Django with split settings.
- Create custom UUID user model before migrations.
- Configure PostgreSQL.
- Install DRF and OpenAPI tooling.
- Add `/health/live/` and `/health/ready/` endpoints.
- Configure Ruff and Pytest.

### Frontend tasks

- Initialise Next.js App Router with TypeScript strict mode.
- Configure Tailwind and shadcn/ui.
- Add base fonts, design tokens, responsive shell, and placeholder route groups.
- Configure frontend lint, format, typecheck, Vitest, and Playwright skeleton.

### Infrastructure tasks

- Create Dockerfiles and `docker-compose.yml` for frontend, backend, and PostgreSQL only.
- Add root `.env.example`.
- Add `Makefile`.
- Add CI for backend checks, frontend checks, tests, and production builds.
- Add root README setup instructions.

### Acceptance criteria

- `docker compose up --build` starts the stack.
- Frontend loads.
- Backend health endpoints work.
- Database migrations apply from a clean database.
- Backend tests pass.
- Frontend tests, lint, typecheck, and production build pass.

Stop and wait for **CONTINUE**.

---

## Stage 2 — Authentication, Email Verification, and Google Login

### Objective

Implement secure browser authentication.

### Tasks

- Configure django-allauth headless browser flows.
- Configure mandatory email verification.
- Implement signup, login, logout, forgot-password, reset-password, and email-verification pages.
- Configure Google OAuth from environment values.
- Implement authenticated session discovery in the frontend.
- Protect customer and admin route groups.
- Add CSRF-safe API utilities.
- Create user-menu and session-expired handling.
- Add development email backend and production email configuration.
- Document Google callback URLs and setup.

### Tests

- Signup and verification.
- Login and logout.
- Password reset.
- Unverified user restrictions.
- Protected API access.
- Google provider boundary configuration.
- CSRF failure behavior.

### Acceptance criteria

- Verified email users can sign in.
- Google sign-in flow is correctly wired from configuration.
- Unverified password users cannot submit protected business actions.
- No auth token is stored in localStorage.

Stop and wait for **CONTINUE**.

---

## Stage 3 — Customer Profile, Staff Roles, and Permissions

### Objective

Create secure user profiles and business roles.

### Tasks

- Implement `CustomerProfile` with E.164 phone validation and payout details.
- Create onboarding flow for first-time customers.
- Seed groups and permissions.
- Create reusable DRF role and ownership permission classes.
- Add admin user/role management for super administrators or controlled Django admin support.
- Add masked serializers for payout details.
- Build profile pages and validation.

### Tests

- Profile validation by payout method.
- Phone normalization.
- Ownership isolation.
- Role matrix tests.
- Masking tests.
- Unauthorised reveal attempts.

### Acceptance criteria

- A customer can complete a valid profile.
- Staff roles enforce the documented matrix.
- Sensitive payout data is masked outside authorised workflows.

Stop and wait for **CONTINUE**.

---

## Stage 4 — Core Domain Models and State Transition Services

### Objective

Build the auditable domain foundation before UI-heavy features.

### Tasks

- Implement models for requests, offers, offer installments, agreements, loans, active installments, disbursements, payments, allocations, ledger transactions, SMS messages, and audit events.
- Add database constraints and indexes.
- Implement number generators for request, loan, and receipt references without race conditions.
- Implement explicit domain transition services.
- Add audit-event helpers with redaction.
- Register read-safe Django admin views for technical support.
- Update data-model and transition documentation.

### Tests

- Model constraints.
- Reference uniqueness.
- Allowed and forbidden transitions.
- Accepted offer immutability.
- Ledger update/delete prevention.
- Concurrent transition protection where practical.

### Acceptance criteria

- Migrations apply cleanly.
- Invalid state transitions are rejected.
- Core records have database-enforced invariants.
- No financial UI is built on an unstable model.

Stop and wait for **CONTINUE**.

---

## Stage 5 — Amortization Engine

### Objective

Implement and prove the authoritative financial calculation engine.

### Tasks

- Create money utilities using Decimal.
- Create typed amortization input/output objects.
- Implement flat total-term interest calculation.
- Implement weekly and monthly due-date generation.
- Implement exact residue correction in final installment.
- Create an API preview endpoint for authorised admins.
- Do not persist an offer from the preview endpoint.
- Add formatted schedule preview components in the admin UI.
- Document formulas and examples.

### Tests

Implement all cases in Section 13, including exact reconciliation.

### Acceptance criteria

- Schedule totals reconcile exactly.
- Date edge cases pass.
- Backend is authoritative.
- Preview and persisted calculations use the same service.

Stop and wait for **CONTINUE**.

---

## Stage 6 — Customer Loan Request Workflow

### Objective

Allow eligible customers to submit and track requests.

### Tasks

- Implement customer request create/list/detail APIs.
- Require verified email and completed profile.
- Snapshot payout information safely for the request.
- Build request form and confirmation page.
- Build customer request-status timeline.
- Prevent editing after submission except through an explicit cancellation or future revision feature.
- Add admin notification indicator inside the dashboard, not a separate external notification service.

### Tests

- Eligibility.
- Validation.
- Ownership.
- Status timeline.
- Duplicate-submit protection.

### Acceptance criteria

- Customer submits a valid request.
- Customer sees only their requests.
- Staff can see the new request in a secured admin list.

Stop and wait for **CONTINUE**.

---

## Stage 7 — Admin Review and Versioned Loan Offers

### Objective

Allow loan officers to review a request and send a versioned amortization offer.

### Tasks

- Build admin request queue, filters, search, and detail page.
- Implement assignment and under-review transition.
- Build offer form using the amortization preview service.
- Persist offer and offer installments atomically.
- Allow draft editing before send.
- Send offer to customer through an explicit transition.
- Supersede previous sent offer when a revision is sent.
- Build customer offer-review page.
- Create `LOAN_OFFER_READY` SMS record and Hubtel boundary placeholder if Stage 11 is not yet implemented.
- Do not send real SMS before the messaging integration stage; safely record pending intent or use dry-run behavior.

### Tests

- Role restrictions.
- Version numbering.
- Superseding.
- Immutability after send/acceptance as designed.
- Correct customer visibility.

### Acceptance criteria

- Loan officer can send a correct offer.
- Customer can see the current offer and full schedule.
- Previous versions are retained for audit.

Stop and wait for **CONTINUE**.

---

## Stage 8 — Customer Decision, Signature, PDF, and Agreement Email

### Objective

Implement robust offer acceptance and formal document generation.

### Tasks

- Implement reject and request-revision actions.
- Implement final acceptance flow.
- Validate typed name, checkbox, and signature image.
- Capture acceptance evidence.
- Generate agreement PDF through WeasyPrint.
- Hash signature and PDF.
- Create immutable agreement.
- Email PDF to `AGREEMENT_ACTION_EMAIL`.
- Add admin retry for failed agreement email.
- Add customer agreement download with permission checks.
- Create loan in `PENDING_APPROVAL` only after successful acceptance and agreement creation.

### Tests

- Invalid signature.
- Non-current offer acceptance.
- Double acceptance.
- Hash generation.
- PDF content smoke test.
- Email success and failure.
- Customer download authorisation.

### Acceptance criteria

- Customer can make one valid, auditable acceptance.
- Signed PDF is generated and stored.
- Email failure does not destroy acceptance.
- Accepted offer cannot be edited.

Stop and wait for **CONTINUE**.

---

## Stage 9 — Approval and Manual Disbursement Recording

### Objective

Separate approval from manual disbursement and record both safely.

### Tasks

- Build approval action for authorised approvers.
- Build disbursement modal for finance officers.
- Implement authorised payout-detail reveal and audit event.
- Record one external disbursement reference and optional evidence.
- Create ledger disbursement entry.
- Copy accepted offer schedule into active repayment installments.
- Move loan through approved, disbursed, and active states correctly.
- Create customer/admin disbursement SMS intents.
- Add double-submit and duplicate-reference protection.

### Tests

- Role separation.
- Invalid status actions.
- Amount mismatch.
- Duplicate disbursement.
- Duplicate reference.
- Schedule copy accuracy.
- Ledger balance.

### Acceptance criteria

- Approval is distinct from disbursement.
- Manual transfer details are displayed securely.
- Recorded disbursement activates the loan and schedule exactly once.

Stop and wait for **CONTINUE**.

---

## Stage 10 — Repayment Posting, Allocation, Reversal, and Reconciliation

### Objective

Implement correct manual repayment servicing.

### Tasks

- Build repayment entry modal and API.
- Implement oldest-outstanding-installment allocation.
- Implement partial and multi-installment payment handling.
- Update balances and statuses atomically.
- Create ledger entries.
- Create receipt numbers.
- Implement payment reversal with reason and role protection.
- Implement reconciliation service and command.
- Create payment confirmation SMS intents.
- Build payment history and customer schedule updates.

### Tests

- Exact payment.
- Partial payment.
- Multi-installment payment.
- Final payoff.
- Overpayment rejection.
- Duplicate submission.
- Reversal.
- Reconciliation.
- Concurrency protection.

### Acceptance criteria

- Financial totals reconcile after every test scenario.
- No posted payment is edited or deleted.
- Customer dashboard updates accurately.

Stop and wait for **CONTINUE**.

---

## Stage 11 — Hubtel SMS and Scheduled Reminder Processing

### Objective

Integrate Hubtel without adding a queue.

### Tasks

- Implement provider interface and Hubtel adapter.
- Implement dry-run provider for development and tests.
- Implement templates for all required message types.
- Send immediate event SMS after financial commit.
- Implement `process_due_sms` management command.
- Add overlapping-run protection.
- Add reminder uniqueness constraints.
- Add retry scheduling and attempt limits.
- Add provider status-query command or mode.
- Add manual admin reminder and retry actions.
- Build SMS history and summary UI.
- Document platform cron/scheduler setup.

### Tests

- Hubtel mocked success.
- Timeout.
- Authentication failure.
- Rate-limit response.
- Server error.
- Malformed response.
- Duplicate scheduler run.
- Five-, three-, two-, one-day reminders.
- Two due-date slots.
- Paid installment skipped.
- Partial-payment amount.
- Retry limit.
- Manual resend audit.

### Acceptance criteria

- No Redis or Celery exists.
- Scheduled reminders work idempotently through the management command.
- SMS failure never reverses financial records.
- Real sending is impossible unless explicit environment configuration enables it.

Stop and wait for **CONTINUE**.

---

## Stage 12 — Production-Quality Dashboards and UI Refinement

### Objective

Complete the corporate CRM-style experience after the business logic is stable.

### Tasks

- Build admin KPI cards.
- Build expected-versus-collected chart.
- Build new request table.
- Build upcoming repayments table.
- Build overdue table.
- Build recent transactions and SMS status panels.
- Build customer dashboard.
- Add loading skeletons, empty states, errors, and responsive layouts.
- Add accessible keyboard interactions and focus management for dialogs.
- Add consistent badge and status mappings.
- Add filters and date-range controls.
- Optimise dashboard queries.

### Tests

- Metric accuracy.
- Filters.
- Loading/error/empty states.
- Responsive smoke tests.
- Key accessibility checks.
- Role navigation.

### Acceptance criteria

- UI resembles a clean, restrained CRM dashboard.
- Metrics are defined and tested.
- Customer experience remains simpler than admin experience.
- No business logic is duplicated in frontend components.

Stop and wait for **CONTINUE**.

---

## Stage 13 — Reports, CSV Exports, Audit Review, and Operational Tools

### Objective

Provide controlled administrative reporting and support tools.

### Tasks

- Add loan and repayment CSV exports with permission checks.
- Add audit log filters.
- Add reconciliation report screen.
- Add failed SMS operational queue view, which is a database view of records, not a new message-queue infrastructure.
- Add agreement email retry view.
- Add read-only customer and loan support views.
- Prevent spreadsheet formula injection in CSV exports.
- Add export audit events.

### Acceptance criteria

- Auditors can inspect but not mutate records.
- CSV exports are authorised and safe.
- Operational failures can be diagnosed without database access.

Stop and wait for **CONTINUE**.

---

## Stage 14 — Security Hardening, Performance, and Full Test Pass

### Objective

Prepare the system for controlled user acceptance testing.

### Tasks

- Review against OWASP ASVS-relevant controls.
- Enable production cookie and HTTPS settings.
- Add CSP and security headers.
- Add admin MFA support.
- Add request throttles.
- Add upload limits and validation.
- Add dependency scanning.
- Add Sentry integration behind configuration.
- Analyse N+1 queries and dashboard query counts.
- Add database indexes based on real queries.
- Run full backend, frontend, E2E, lint, typecheck, and production-build suites.
- Conduct permission matrix review.
- Conduct data-leakage review.
- Add backup and restore procedures.
- Add threat model and launch risks to documentation.

### Acceptance criteria

- All automated checks pass.
- No known critical or high-severity security issue remains unaddressed.
- Critical workflows pass end-to-end.
- Production configuration fails safely when secrets are missing.

Stop and wait for **CONTINUE**.

---

## Stage 15 — Deployment, Runbook, and User Acceptance Release

### Objective

Produce a deployable release and clear operating instructions.

### Tasks

- Create production Docker builds.
- Document reverse proxy and same-site auth routing.
- Document managed PostgreSQL requirements.
- Document object storage.
- Document email and Hubtel configuration.
- Document deployment scheduler command and cadence.
- Document migrations and rollback strategy.
- Document backup and restore.
- Document admin-user creation and role seeding.
- Create smoke-test checklist.
- Create user acceptance test script.
- Create incident runbook for:
  - Hubtel outage;
  - email outage;
  - failed scheduler;
  - duplicate payment concern;
  - incorrect disbursement record;
  - account compromise;
  - database restore.
- Add legal and regulatory review gates before public launch.

### Acceptance criteria

- A new environment can be deployed from documentation.
- Scheduler execution is verified.
- Health checks and smoke tests pass.
- UAT script covers the full loan lifecycle.
- Remaining launch risks are explicit, not hidden.

Stop and request final product-owner review.

---

# 25. Definition of Done for Every Feature

A feature is not complete unless:

- business rules are implemented in backend services;
- permissions are enforced server-side;
- database constraints protect critical invariants;
- API input and output are explicitly validated;
- loading, empty, success, and error UI states exist;
- relevant audit events exist;
- financial changes are atomic;
- tests cover success and failure paths;
- documentation is updated;
- lint, tests, typecheck, and build pass;
- no secrets or sensitive data are exposed;
- the implementation works from a clean database and fresh setup.

---

# 26. Mandatory “DO NOT” Rules

These rules are binding.

## Architecture

- **DO NOT** introduce microservices.
- **DO NOT** add Redis, Celery, RabbitMQ, Kafka, or another queue for the MVP.
- **DO NOT** put cron inside the web application request process.
- **DO NOT** run multiple schedulers without a database-backed overlap lock.
- **DO NOT** create speculative abstractions with no current use.
- **DO NOT** split the application into separate repositories.
- **DO NOT** add Kubernetes.
- **DO NOT** use SQLite outside isolated unit tests; PostgreSQL is the authoritative database.

## Authentication and security

- **DO NOT** build custom password hashing, password reset, OAuth, or session systems.
- **DO NOT** store tokens in browser localStorage.
- **DO NOT** disable CSRF to make requests work.
- **DO NOT** use wildcard CORS with credentials.
- **DO NOT** trust frontend role checks.
- **DO NOT** expose another customer’s records through list or detail endpoints.
- **DO NOT** return sensitive payout details in normal serializers.
- **DO NOT** log passwords, API secrets, session identifiers, full account numbers, signature images, or private document contents.
- **DO NOT** hard-code secret keys, Hubtel credentials, Google credentials, admin phone numbers, email credentials, or action email addresses.
- **DO NOT** commit `.env` files or production credentials.
- **DO NOT** expose Django debug mode in production.

## Financial integrity

- **DO NOT** use `float` for money or interest.
- **DO NOT** calculate authoritative amortization in the browser.
- **DO NOT** allow direct status editing from a generic CRUD endpoint.
- **DO NOT** equate customer acceptance with loan approval.
- **DO NOT** equate approval with disbursement.
- **DO NOT** equate one repayment with full payoff.
- **DO NOT** update or delete posted payments or ledger entries to correct mistakes.
- **DO NOT** delete accepted offers, agreements, disbursements, payments, allocations, or audit events.
- **DO NOT** let SMS or email failure roll back a valid financial transaction.
- **DO NOT** post a payment without duplicate-submit protection.
- **DO NOT** post a disbursement twice.
- **DO NOT** rely only on application validation where a database constraint can protect the invariant.
- **DO NOT** recalculate an accepted historical offer using a later algorithm version.

## Hubtel and messaging

- **DO NOT** call Hubtel directly from the browser.
- **DO NOT** expose Hubtel credentials to Next.js public environment variables.
- **DO NOT** assume a successful HTTP request means final SMS delivery.
- **DO NOT** send repeated scheduled reminders without uniqueness protection.
- **DO NOT** send reminders for fully paid installments.
- **DO NOT** include sensitive financial account details in SMS.
- **DO NOT** enable real SMS sending by default in development or test environments.
- **DO NOT** ignore provider timeouts, rate limits, or malformed responses.
- **DO NOT** create a browser push-notification system.

## Backend code quality

- **DO NOT** put core business logic in views, serializers, model `save()` methods, signals, or admin actions when it belongs in an explicit service.
- **DO NOT** hide major workflow side effects in Django signals.
- **DO NOT** use `fields = '__all__'` for sensitive API serializers.
- **DO NOT** write raw SQL unless the ORM cannot safely express the requirement and the reason is documented and tested.
- **DO NOT** keep database transactions open while calling Hubtel, sending email, generating large files, or performing other slow network work.
- **DO NOT** swallow exceptions silently.
- **DO NOT** catch broad exceptions without recording a safe diagnostic and handling the state deliberately.
- **DO NOT** create migrations that destroy production data without explicit product-owner approval and a rollback plan.

## Frontend code quality

- **DO NOT** duplicate financial formulas in React components.
- **DO NOT** trust client-side validation as sufficient.
- **DO NOT** create one enormous dashboard component.
- **DO NOT** use arbitrary inconsistent spacing, colours, radii, or typography.
- **DO NOT** add decorative gradients, glassmorphism, neon colours, or excessive animation.
- **DO NOT** use colour as the only status indicator.
- **DO NOT** omit keyboard support and focus management from dialogs.
- **DO NOT** hide failed requests; show actionable error states.
- **DO NOT** display fake production metrics when the database is empty.

## Scope discipline

- **DO NOT** add a payment gateway.
- **DO NOT** add automated loan disbursement.
- **DO NOT** add credit scoring or AI underwriting.
- **DO NOT** add KYC, OCR, biometric checks, credit bureau calls, or collections automation unless explicitly requested later.
- **DO NOT** add a native mobile app.
- **DO NOT** add multi-tenancy.
- **DO NOT** implement fees, penalties, compound interest, reducing-balance interest, or restructuring in the MVP without an approved scope change.
- **DO NOT** claim the system is legally or regulatorily compliant. Record legal review as a launch gate.

## AI coding behaviour

- **DO NOT** generate placeholder code and call the stage complete.
- **DO NOT** leave `TODO` comments for requirements that belong to the current stage.
- **DO NOT** claim tests passed without running them.
- **DO NOT** replace large sections of working code without explaining why.
- **DO NOT** invent credentials, domains, sender IDs, legal text, or production configuration.
- **DO NOT** proceed to a later stage without the product owner’s **CONTINUE** instruction.
- **DO NOT** ask broad questions that can be resolved safely from this specification. Ask only a focused question when a decision genuinely blocks the current stage.

---

# 27. Suggested SMS Templates

Keep all templates configurable and test rendering.

### Offer ready

```text
{lender}: Dear {first_name}, your loan offer for {principal_gHS} is ready for review. Sign in to view the terms. Ref: {request_number}.
```

### Disbursement confirmation — customer

```text
{lender}: {amount_gHS} has been recorded as disbursed for loan {loan_number}. First repayment: {next_amount_gHS} due {next_due_date}.
```

### Disbursement confirmation — admin

```text
{lender}: Disbursement recorded for {customer_name}, loan {loan_number}, amount {amount_gHS}. Next due: {next_amount_gHS} on {next_due_date}.
```

### Payment confirmation — customer

```text
{lender}: We received {payment_amount_gHS} for loan {loan_number}. Balance: {balance_gHS}. Next payment: {next_amount_gHS} due {next_due_date}.
```

### Final payment — customer

```text
{lender}: We received {payment_amount_gHS}. Loan {loan_number} is now fully repaid. Thank you.
```

### Reminder

```text
{lender}: Dear {first_name}, {outstanding_gHS} is due on {due_date} for loan {loan_number}. Please pay using the agreed channel.
```

### Partial-payment reminder

```text
{lender}: Dear {first_name}, {outstanding_gHS} remains due on loan {loan_number}. Due date: {due_date}.
```

Templates must gracefully handle the absence of a next installment after final payment.

---

# 28. Suggested Environment Variables

```text
# General
APP_ENV=local
APP_NAME=
APP_BASE_URL=http://localhost:3000
API_BASE_URL=http://localhost:8000
APP_TIME_ZONE=Africa/Accra
DJANGO_SECRET_KEY=
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://postgres:postgres@db:5432/loan_management

# Cookies and security
SESSION_COOKIE_SECURE=false
CSRF_COOKIE_SECURE=false
CSRF_TRUSTED_ORIGINS=http://localhost:3000,http://localhost:8000
CORS_ALLOWED_ORIGINS=http://localhost:3000

# Google OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Email
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=
AGREEMENT_ACTION_EMAIL=isbaah@gmail.com

# Hubtel
HUBTEL_ENABLED=false
HUBTEL_BASE_URL=
HUBTEL_CLIENT_ID=
HUBTEL_CLIENT_SECRET=
HUBTEL_SENDER_ID=
HUBTEL_ADMIN_PHONE_E164=
HUBTEL_CONNECT_TIMEOUT_SECONDS=5
HUBTEL_READ_TIMEOUT_SECONDS=10
HUBTEL_MAX_REQUESTS_PER_MINUTE=
SMS_DRY_RUN=true
SMS_MAX_ATTEMPTS=3
SMS_DUE_MORNING_TIME=08:00
SMS_DUE_AFTERNOON_TIME=16:00

# Storage
STORAGE_BACKEND=local
MEDIA_ROOT=/app/media
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=
AWS_S3_REGION_NAME=

# Monitoring
SENTRY_DSN=
```

Validate configuration at startup. Production must fail clearly when required values are absent.

---

# 29. Final End-to-End Acceptance Scenario

The finished system must demonstrate this complete path:

1. A new customer signs up with email.
2. The customer verifies the email.
3. The customer completes a mobile number and payout profile.
4. The customer requests a GHS 10,000 loan for six months.
5. A loan officer reviews the request.
6. The loan officer creates a six-month offer at a 12% flat total-term interest rate.
7. The system calculates total interest of GHS 1,200 and total repayable of GHS 11,200.
8. The schedule contains six installments and reconciles exactly to GHS 11,200 after rounding.
9. The officer sends the offer.
10. The customer reviews the full schedule.
11. The customer types their name, signs, and accepts.
12. The agreement PDF is generated, hashed, stored, and emailed to the configured action address.
13. An approver approves the loan.
14. A finance officer opens the secure disbursement modal and manually transfers funds outside the system.
15. The finance officer records the disbursement reference.
16. The loan becomes active exactly once.
17. Customer and admin SMS messages are created and sent or safely logged in dry-run mode.
18. The scheduler identifies the five-day reminder window without duplicate messages.
19. A finance officer records a partial repayment.
20. The payment allocates correctly, balance updates, and the next-payment SMS is rendered correctly.
21. A later payment covers more than one installment and allocates oldest first.
22. Final repayment moves the loan to paid off.
23. A reversal test restores the correct balance without deleting the original payment.
24. Another customer cannot access any of these records.
25. A loan officer cannot record a disbursement or payment without the finance permission.
26. An auditor can review the history but cannot mutate it.
27. All relevant automated checks and production builds pass.

---

# 30. Official Documentation References to Consult

Before implementation, consult the latest stable official documentation for:

- Django 5.2 release and security documentation: `https://docs.djangoproject.com/en/5.2/`
- Django database transactions: `https://docs.djangoproject.com/en/5.2/topics/db/transactions/`
- Django REST Framework permissions: `https://www.django-rest-framework.org/api-guide/permissions/`
- django-allauth headless browser flows: `https://docs.allauth.org/en/latest/headless/`
- django-allauth Google provider: `https://docs.allauth.org/en/latest/socialaccount/providers/google.html`
- Next.js App Router: `https://nextjs.org/docs/app`
- shadcn/ui: `https://ui.shadcn.com/`
- Hubtel API documentation: `https://docs-developers.hubtel.com/`
- OWASP ASVS: `https://owasp.org/www-project-application-security-verification-standard/`

Do not copy outdated examples blindly. Adapt them to the currently installed stable versions and verify behavior with tests.

---

## Start Instruction

Begin with **Stage 0 only**.

Inspect the repository, report what currently exists, create the Stage 0 documentation, identify any genuinely blocking decision, run any relevant documentation or repository checks, update `docs/BUILD_PROGRESS.md`, and stop.

Do not begin Stage 1 until the product owner says **CONTINUE**.
