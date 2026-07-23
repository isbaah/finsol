# Test Plan

Status: Strategy locked at Stage 0 (from Section 22 of the master prompt). Each stage adds its own tests as it is built — no stage is considered complete if its relevant tests are missing or failing (Section 2, Section 25).

## 1. Principles

- Every feature needs tests for both the success path and the realistic failure paths (validation error, permission denial, invalid state transition, provider failure) — not just the happy path.
- Financial logic is tested with exact-value assertions (`Decimal` equality), never approximate/float comparisons.
- Tests never silently skip on missing configuration; SMS/email tests use dry-run/mock providers, not real Hubtel/SMTP calls.
- A command is not reported as "passed" unless it was actually run in this environment and its output was observed.

## 2. Backend tests (Pytest + pytest-django)

- **Model constraint tests** — uniqueness, check constraints, required-field-by-payout-method logic.
- **Service-layer unit tests** — one test module per domain service (request, offer, agreement, loan, disbursement, repayment, SMS orchestration).
- **Amortization tests** — all cases enumerated in Section 13 of the master prompt: zero-interest loan; normal interest loan; principal that creates a rounding residue; single installment; weekly schedule; monthly schedule; January 31 monthly progression; leap-year dates; invalid negative amount; invalid term; exact sum reconciliation (`sum(principal_due) == principal`, `sum(interest_due) == total_interest`, `sum(total_due) == total_repayable`).
- **State-transition tests** — one test per allowed transition in `STATUS_TRANSITIONS.md`, plus at least one test per row proving the *disallowed* transitions are rejected with a domain-specific error.
- **Permission tests** — full role matrix (`CUSTOMER`, `LOAN_OFFICER`, `APPROVER`, `FINANCE_OFFICER`, `AUDITOR`, `SUPER_ADMIN`) against every protected endpoint and service function.
- **Customer data isolation tests** — a second customer fixture must never be able to read/act on the first customer's requests, offers, loans, schedules, or payments via any endpoint.
- **API contract tests** — status codes, error object shape, pagination, filtering/search/ordering on admin lists.
- **Payment allocation tests** — exact payment, partial payment, multi-installment payment, final payoff, overpayment rejection.
- **Reversal tests** — reversal preserves the original record, requires a reason, recalculates balances correctly.
- **Reconciliation tests** — the three identities in Section 19 hold after every scenario:
  ```
  loan amount repaid == sum(active posted payments)
  loan outstanding == total repayable - amount repaid
  installment outstanding == installment total due - allocated active payments
  ```
- **SMS template tests** — every message type in Section 17 renders correctly, including graceful handling when there is no next installment after final payment.
- **SMS duplicate-prevention tests** — the `(installment, message_type, reminder_business_date, reminder_slot)` uniqueness constraint actually prevents duplicate reminders across repeated scheduler runs.
- **Scheduler time-window tests** — `process_due_sms` correctly identifies 5/2/1-day and both due-date slots, using Freezegun to control "now."
- **Hubtel integration tests** (mocked HTTP via `httpx` mock transport) — success, timeout, authentication/4xx failure, rate-limit response, 5xx server error, malformed response.
- **Agreement tests** — SHA-256 hash correctness, PDF content smoke test, immutability after creation.
- **Email failure handling tests** — agreement email failure does not undo acceptance; failure is recorded and retryable.
- **File access tests** — unauthorised users cannot fetch another customer's agreement PDF or evidence file, including by guessing a URL.
- **Dashboard metric tests** — each KPI/chart metric definition (Section 16) is computed correctly against known fixture data.

## 3. Frontend tests (Vitest + React Testing Library)

- Form validation (Zod schemas + React Hook Form error states).
- Auth-route protection (unauthenticated users redirected; wrong-role users blocked from admin routes).
- Role-based navigation (sidebar/menu items match the signed-in user's roles).
- Money and date display formatting (GHS code always shown; dates in the unambiguous `24 Sep 2026`-style format).
- Offer review page rendering (schedule, totals, accept/reject/revision actions).
- Signature capture validation (empty signature rejected, checkbox + typed name required).
- Admin modal tests (disbursement modal, payment modal) — required fields, confirmation step, preview values.
- Table empty/loading/error states for all admin tables.
- Key accessibility checks (focus management on dialogs, keyboard navigation) on primary flows.

## 4. End-to-end tests (Playwright)

Minimum scenarios (Section 22 / Section 29), each runnable against a seeded test database:

1. Email signup → verification → profile completion → loan request.
2. Google sign-in path, using an appropriate test double / mocked provider boundary.
3. Admin reviews request and sends an offer.
4. Customer reviews and signs the offer.
5. Agreement is generated.
6. Approver approves the loan.
7. Finance officer records manual disbursement.
8. Customer sees the active loan.
9. Finance officer records a partial payment.
10. Balance and next-payment figures update correctly on the customer dashboard.
11. Finance officer records the final payment.
12. Loan becomes paid off.
13. A second customer cannot access the first customer's loan (isolation).
14. A `LOAN_OFFICER` cannot perform a finance-only action (disbursement/payment posting).

## 5. Full end-to-end acceptance scenario (release gate)

The scripted scenario in Section 29 of the master prompt (GHS 10,000 / 6-month / 12% flat total-term example, reconciling to GHS 11,200 total repayable across 6 installments) is the release-readiness scenario, executed manually and/or via Playwright before Stage 15 sign-off. It exercises every module in one continuous path, including reversal and cross-customer isolation checks.

## 6. What "tests pass" means in this project

For every stage's report, "tests passed" means the relevant `pytest` / `vitest` / `playwright` command was actually executed in this environment for this change and its output is shown, not inferred. Commands run and their results are listed in each stage's section of `BUILD_PROGRESS.md`.

## 7. Traceability

No backend/frontend code exists yet (Stage 0), so no tests have been run yet. Test tooling itself (Pytest/pytest-django config, Vitest/Playwright config) is set up in Stage 1. Each subsequent stage in Sections 6–15 of the master prompt adds the tests listed in its own "Tests" subsection; this file is the consolidated reference so coverage gaps are visible across the whole project rather than only within one stage's task list.
