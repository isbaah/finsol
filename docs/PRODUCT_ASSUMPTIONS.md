# Product Assumptions

Status: Locked for MVP unless the product owner explicitly changes an item below before the relevant build stage.
Source of truth: `claude/CLAUDE_LOAN_MANAGEMENT_SYSTEM_MASTER_PROMPT.md`, Section 4 and Section 5.
Last reviewed: 2026-07-23 (Stage 0).

## 1. Tenancy and locale

- Single lending organisation. **Not** multi-tenant.
- Application language: English only.
- Currency: Ghana cedi. Stored and coded as `GHS`. Always displayed with the `GHS` code, never a bare symbol.
- Timezone: `Africa/Accra` for all business dates, due-date logic, and SMS scheduling windows. UTC is used for stored timestamps; conversion to Accra time happens at the presentation/business-rule layer.

## 2. Money movement

- No payment gateway is integrated (no Paystack, Stripe, Hubtel Payments, etc.).
- No automatic mobile-money or bank disbursement.
- Disbursements and repayments happen **outside** the application (manual bank/mobile-money transfer) and are only **recorded** inside it, by staff, after the fact.
- The application never initiates a transfer of funds.

## 3. Notifications

- Hubtel is the SMS provider for all operational notifications and reminders (offer ready, disbursement, repayment, reminders, payoff).
- Email is used only for: account verification, password reset, and delivering the signed agreement PDF to the configured action mailbox. Email is explicitly **not** used for repayment reminders.
- No push notifications, no WhatsApp, no in-app real-time channel.

## 4. Out of scope for MVP (explicit non-goals)

Restated from Section 5 of the master prompt — these must not be built without an approved scope change:

- In-app loan payments or checkout flows of any kind.
- Automatic bank/mobile-money transfers.
- Native iOS/Android apps.
- Microservices, Kubernetes, Redis, Celery, RabbitMQ, Kafka, event sourcing, a data warehouse.
- AI credit decisions, facial recognition, document OCR, automated debt collection.
- Automated late fees, tax/accounting calculations.
- Multi-currency support, multi-language support.
- Public loan marketplace features.
- Credit scoring, credit bureau integration, automated underwriting, KYC verification, collections workflow automation, accounting-system integration.

## 5. Loan data model assumptions

- A customer may have multiple historical loans over time. The schema supports many loans per customer even though a business rule may later cap simultaneous active loans (no such cap is enforced in the MVP unless specified).
- A customer must never be able to view another customer's data, under any endpoint.
- Administrators may hold more than one operational role simultaneously (e.g. `LOAN_OFFICER` + `FINANCE_OFFICER`).

## 6. Amortization method (MVP)

- **Flat total-term interest** only. The interest percentage entered by an administrator is the total interest for the *entire* loan term, not an annual or monthly rate.
  ```
  total_interest = principal × (interest_rate_percent / 100)
  total_repayable = principal + total_interest
  ```
- This must be labelled clearly and unambiguously in both the UI (offer creation and offer review screens) and in code (`interest_method = "FLAT_TOTAL_TERM"`), so nobody mistakes it for an APR.
- The calculation service (`AmortizationCalculator`, built in Stage 5) must be structured so that a second interest strategy (e.g. reducing balance) could be added later as a new strategy implementation, without rewriting the loan module. This is a design constraint, not a Stage 0 deliverable — see `ARCHITECTURE.md`.
- Loan term = a number + a unit (`WEEK` or `MONTH`), entered by the admin when creating the offer.
- `installment_count == term_count` for the MVP (i.e. no separate "number of installments" concept independent of term length).
- Repayment frequency equals the selected term unit (weekly term → weekly installments; monthly term → monthly installments). There is no mixed-frequency schedule in the MVP.
- No fees or penalties are included in any calculation unless the product owner explicitly adds them in a later, approved scope change.

## 7. Configuration, not code

The following must be environment/database configuration values, never hard-coded:

- `AGREEMENT_ACTION_EMAIL` (initial value `isbaah@gmail.com` and `isbaahjnr@gmail.com` — see open decision in `BUILD_PROGRESS.md` about single vs. multiple recipients).
- Admin SMS notification number (`HUBTEL_ADMIN_PHONE_E164`).
- All Hubtel credentials, base URL, sender ID.
- Reminder time-of-day slots (`SMS_DUE_MORNING_TIME`, `SMS_DUE_AFTERNOON_TIME`).
- Application base URLs (`APP_BASE_URL`, `API_BASE_URL`).

## 8. Traceability

Every assumption above maps to specific build stages in `BUILD_PROGRESS.md` → "Requirement-to-Stage Traceability Matrix". If an assumption needs to change, it must be updated here first, then reflected in the relevant stage's plan before that stage starts.
