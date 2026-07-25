# Status Transitions

Status: Draft transition matrix for Stage 0, to be validated and encoded as service-layer guards in Stage 4. The master prompt (Section 11) defines the state *names*; this document defines the allowed *transitions*, the actor who may trigger each one, and flags genuine ambiguities left open by the spec.

General rule (Section 11 / Section 26): every transition below is implemented as an explicit domain service function, wrapped in `transaction.atomic()` with `select_for_update()` on the affected row(s) where concurrent access is plausible. Invalid transitions raise a domain-specific error and map to a clear API error response. No status field is ever writable through a generic CRUD `PATCH`.

**Resolved in Stage 6/7 — how a domain error becomes an API response**: `common/domain.py::InvalidTransitionError` now subclasses a new `DomainError` base, and `common/api/exceptions.py` registers a global DRF `EXCEPTION_HANDLER` that maps any `DomainError` to `409 Conflict` with `{"detail": ..., "code": "conflict"}`. Stage 4 built the transition guards with no API surface calling them yet; Stage 6/7 is the first time one can actually be triggered over HTTP, so this was the first stage that needed the mapping. Per-app business-rule violations that aren't literally a status transition (e.g. `apps/loan_offers/services.py`'s `OfferNotEditableError` — editing a non-DRAFT offer — and `LoanRequestNotReadyForOfferError` — creating an offer for a request that isn't open for one) subclass `DomainError` directly rather than `InvalidTransitionError`, and get the same 409 handling for free.

## 1. LoanRequest

States: `DRAFT`, `SUBMITTED`, `UNDER_REVIEW`, `OFFER_SENT`, `CUSTOMER_ACCEPTED`, `CUSTOMER_REJECTED`, `REVISION_REQUESTED`, `APPROVED`, `DECLINED`, `CANCELLED`, `CONVERTED_TO_LOAN`.

| From | To | Trigger | Actor |
|---|---|---|---|
| — | `SUBMITTED` | Request created and submitted (MVP creates directly in `SUBMITTED`; see note) | `CUSTOMER` |
| `DRAFT` | `SUBMITTED` | Draft submitted | `CUSTOMER` |
| `DRAFT` | `CANCELLED` | Draft discarded | `CUSTOMER` |
| `SUBMITTED` | `UNDER_REVIEW` | Officer assigns/starts review | `LOAN_OFFICER` |
| `SUBMITTED` | `CANCELLED` | Customer cancels before review starts | `CUSTOMER` |
| `SUBMITTED` | `DECLINED` | Officer declines without an offer | `LOAN_OFFICER` |
| `UNDER_REVIEW` | `OFFER_SENT` | Officer sends the first offer version | `LOAN_OFFICER` |
| `UNDER_REVIEW` | `DECLINED` | Officer declines after review | `LOAN_OFFICER` |
| `UNDER_REVIEW` | `CANCELLED` | Customer cancels while under review | `CUSTOMER` |
| `OFFER_SENT` | `CUSTOMER_ACCEPTED` | Customer accepts the current offer | `CUSTOMER` |
| `OFFER_SENT` | `CUSTOMER_REJECTED` | Customer rejects the current offer | `CUSTOMER` |
| `OFFER_SENT` | `REVISION_REQUESTED` | Customer requests a revision | `CUSTOMER` |
| `OFFER_SENT` | `OFFER_SENT` | Officer sends a corrected version before the customer has acted on the outstanding one (Stage 4 resolution, see note below the LoanOffer table) | `LOAN_OFFICER` |
| `REVISION_REQUESTED` | `UNDER_REVIEW` or `OFFER_SENT` | Officer reworks and (re)sends a new offer version | `LOAN_OFFICER` |
| `CUSTOMER_ACCEPTED` | `CONVERTED_TO_LOAN` | Agreement created successfully, `Loan` row created atomically (Stage 8) | System, on successful acceptance flow |
| `CUSTOMER_REJECTED` | — | Terminal for this request | — |
| `DECLINED` | — | Terminal | — |
| `CANCELLED` | — | Terminal | — |
| `CONVERTED_TO_LOAN` | — | Terminal for the request; the `Loan` entity now owns the lifecycle | — |

**Resolved in Stage 6/7 — `APPROVED` state stays reserved/unused**: confirmed while building the Stage 6/7 API surface — no customer or admin endpoint sets it, and the real request flow goes `UNDER_REVIEW → OFFER_SENT → CUSTOMER_ACCEPTED → CONVERTED_TO_LOAN` exactly as before. Left as previously recommended: reserved for a possible future internal "qualifies" gate, not built into any service function.

Only the current (`SENT`) offer version can drive an `OFFER_SENT`-sourced transition; a superseded offer cannot be accepted, rejected, or revised.

## 2. LoanOffer

States: `DRAFT`, `SENT`, `SUPERSEDED`, `ACCEPTED`, `REJECTED`, `EXPIRED`.

| From | To | Trigger | Actor |
|---|---|---|---|
| — | `DRAFT` | Officer starts building an offer for a request | `LOAN_OFFICER` |
| `DRAFT` | `SENT` | Officer sends the offer to the customer | `LOAN_OFFICER` |
| `SENT` | `ACCEPTED` | Customer completes signature/acceptance flow | `CUSTOMER` |
| `SENT` | `REJECTED` | Customer rejects | `CUSTOMER` |
| `SENT` | `SUPERSEDED` | A new offer version for the same request is sent | System, as part of sending the new version |
| `SENT` | `EXPIRED` | `offer_expiry_date` passes with no customer action | System (see open decision below) |
| `ACCEPTED` | — | Terminal, immutable | — |
| `REJECTED` | — | Terminal for this version (officer may still create a *new* offer version in response) | — |
| `SUPERSEDED` | — | Terminal for this version | — |
| `EXPIRED` | — | Terminal for this version | — |

Rules: unique `version_number` per request; only one `SENT` version may exist at a time; sending a new version supersedes the previous `SENT` version atomically (both writes in one transaction); fields and computed totals are frozen the moment `status = ACCEPTED`.

**Expiry enforcement mechanism**: implemented in Stage 4 as lazy enforcement (`apps/loan_offers/services.py::_reject_if_expired()`), called from `accept_offer`/`reject_offer`/`request_revision`. **Resolved in Stage 8**: all three are now wired to real API endpoints (`POST /api/v1/customer/offers/{id}/accept|reject|request-revision/`) — the lazy-check design needed no change; an expired offer now correctly surfaces as a `409` through the global `DomainError` handler.

**Resolved in Stage 4 — no dedicated "revision requested" LoanOffer state**: Section 11's LoanOffer status list has no state matching `LoanRequest.REVISION_REQUESTED`. A customer's revision request is modelled as the offer transitioning `SENT` → `REJECTED` (with a reason) — `REJECTED`'s own documented semantics above ("officer may still create a new offer version in response") are exactly a revision request's meaning — while the *request* moves to its own `REVISION_REQUESTED` state. See `apps/loan_offers/services.py::request_revision()`.

**Resolved in Stage 4 — `mark_offer_sent` also accepts `OFFER_SENT` as a source** on the *LoanRequest* side (Section 1's table below): Section 11 states "Sending a revised offer supersedes the previous sent offer" without requiring the customer to have acted on the outstanding one first (e.g. an officer catching their own mistake minutes after sending). The request's own status stays `OFFER_SENT` across this — only the offer versions change (old → `SUPERSEDED`, new → `SENT`).

## 3. Loan

States: `PENDING_APPROVAL`, `APPROVED_FOR_DISBURSEMENT`, `DISBURSED`, `ACTIVE`, `PAID_OFF`, `OVERDUE`, `RESTRUCTURED`, `DEFAULTED`, `CANCELLED`.

| From | To | Trigger | Actor |
|---|---|---|---|
| — | `PENDING_APPROVAL` | Created atomically with the `Agreement`, immediately after customer acceptance (Stage 8) | System |
| `PENDING_APPROVAL` | `APPROVED_FOR_DISBURSEMENT` | Approver approves | `APPROVER` |
| `PENDING_APPROVAL` | `CANCELLED` | Approver/admin declines to approve | `APPROVER` / `SUPER_ADMIN` |
| `APPROVED_FOR_DISBURSEMENT` | `DISBURSED` → `ACTIVE` | Finance officer records the disbursement; the service moves the loan through `DISBURSED` and immediately to `ACTIVE` within one atomic operation, copying the accepted offer's schedule into `RepaymentInstallment` rows in the same transaction | `FINANCE_OFFICER` |
| `APPROVED_FOR_DISBURSEMENT` | `CANCELLED` | Exceptional case before funds are sent | `SUPER_ADMIN` |
| `ACTIVE` | `OVERDUE` | Derived: an installment is unpaid past its due date; the status change itself is recorded and audited, not silently inferred at read time only | System (recomputed on a defined trigger — see open decision) |
| `OVERDUE` | `ACTIVE` | The overdue installment(s) are brought current | System, following a posted payment |
| `ACTIVE` or `OVERDUE` | `PAID_OFF` | Authoritative outstanding balance reaches zero | System, following a posted payment |
| `PAID_OFF` | — | Terminal | — |
| `CANCELLED` | — | Terminal | — |
| `ACTIVE`/`OVERDUE` | `RESTRUCTURED` | **Reserved — not implemented in MVP.** No restructuring workflow is built; explicit non-goal. | — |
| `ACTIVE`/`OVERDUE` | `DEFAULTED` | **Reserved — not implemented in MVP.** No automated default rule is defined; explicit non-goal (no automated collections). | — |

Hard rules restated from Section 11: customer acceptance ≠ approval; approval ≠ disbursement; disbursement ≠ repayment; one repayment ≠ full payoff. A loan can only reach `CANCELLED` before `DISBURSED` — once money has moved, the only corrective mechanisms are ledger `ADJUSTMENT`/`WRITE_OFF` entries and payment reversal, never a loan-level cancel.

**Resolved in Stage 8/9 — all transitions above are now live and proven end-to-end** (both by API
tests and a real `curl` walk against the running stack): acceptance → `PENDING_APPROVAL` →
`APPROVED_FOR_DISBURSEMENT` → `ACTIVE`, with role separation enforced (`APPROVER` cannot disburse,
`FINANCE_OFFICER` cannot approve — both proven as live `403`s, not just documented intent). One
clarification surfaced while building `record_disbursement()`: `Loan.outstanding_balance` is **not**
mutated by the `DISBURSED`/`ACTIVE` transition — it was already set to `total_repayable` at
`PENDING_APPROVAL` creation time (Stage 4), and Section 19's reconciliation formula
(`outstanding == total_repayable - amount_repaid`) never mentions disbursement. The `DISBURSEMENT`
`LoanTransaction` row is still posted (a real, positive-amount ledger entry for the audit trail), but
with `balance_after` equal to the unchanged `outstanding_balance` — see
`apps/loans/services.py::_post_disbursement_ledger_entry()` and `docs/BUILD_PROGRESS.md`'s Stage 8/9
Design decision 1 for the full reasoning; this corrects a Stage 4 docstring comment on
`LoanTransaction.amount` that had assumed the opposite.

**Resolved in Stage 11 — `OVERDUE` recomputation piggybacks on `process_due_sms`**: exactly the recommended option. Every run of `apps/messaging/management/commands/process_due_sms.py` first walks every non-`PAID`/`WAIVED` installment and flips `UPCOMING`→`DUE`/`DUE`|`PARTIALLY_PAID`→`OVERDUE` as needed (pure due-date arithmetic, no SMS involved), then recomputes each touched loan's `ACTIVE`↔`OVERDUE` status via the existing `apps/loans/services.py::mark_overdue()`/`mark_current()` (built and tested since Stage 4, wired up for the first time here). No separate scheduler entry — one idempotent command run covers both the reminder sweep and this recomputation. Proven live: a single-installment loan whose due date had passed correctly flipped to `OVERDUE` (installment and loan both), and reverted to `ACTIVE` once the installment was paid.

A second, narrower exception to the "forward-only" transition table above is `PAID_OFF` → `ACTIVE`/`OVERDUE` on payment reversal (Stage 10) — reversing the payment that paid a loan off must be able to reopen it, which the table (a description of forward business triggers) was never meant to cover. See `apps/repayments/services.py::reverse_payment()` and its docstring.

## 4. RepaymentInstallment

States: `UPCOMING`, `DUE`, `PARTIALLY_PAID`, `PAID`, `OVERDUE`, `WAIVED`.

| From | To | Trigger |
|---|---|---|
| `UPCOMING` | `DUE` | Due date reached, no payment yet |
| `DUE` | `PARTIALLY_PAID` | Partial payment allocated |
| `DUE` | `PAID` | Full payment allocated |
| `DUE` | `OVERDUE` | Due date passed, still unpaid |
| `PARTIALLY_PAID` | `PAID` | Remaining balance paid |
| `PARTIALLY_PAID` | `OVERDUE` | Due date passed while still partially paid |
| `OVERDUE` | `PARTIALLY_PAID` | Partial payment received after due date |
| `OVERDUE` | `PAID` | Full payment received after due date |
| `UPCOMING`/`DUE`/`PARTIALLY_PAID`/`OVERDUE` | `WAIVED` | Explicit administrative waiver, reason required | `SUPER_ADMIN` (recommended restriction) |
| `PAID` / `WAIVED` | — | Terminal |

**Resolved in Stage 10 — no dedicated waiver UI built**, per the standing recommendation: `apps/loans/services.py::waive_installment()` (built and tested since Stage 4) remains the only path, reachable via the Django admin or a one-off shell command. Not revisited because no stage task asked for it and it borders the explicitly out-of-scope "fees/penalties" territory — worth reconsidering only if the product owner asks.

**Resolved in Stage 10 — status here is a pure derived recomputation, not a guarded transition**: `apps/repayments/services.py::_recompute_installment()` recalculates `amount_paid`/`outstanding_amount`/`status` from scratch from the installment's own active (`POSTED`-payment) `PaymentAllocation` rows every time a payment posts *or* reverses, rather than incrementally applying "the" transition above. This is deliberate — a reversal genuinely needs to move an installment backward (e.g. `PAID` → `PARTIALLY_PAID`), which this forward-only table was never meant to describe, and recomputing from the source rows means the post-payment and post-reversal code paths can never drift apart.

## 5. Payment

States: `POSTED`, `REVERSED`.

| From | To | Trigger | Actor |
|---|---|---|---|
| — | `POSTED` | Payment recorded | `FINANCE_OFFICER` |
| `POSTED` | `REVERSED` | Explicit reversal, reason required | `FINANCE_OFFICER` / `SUPER_ADMIN` |
| `REVERSED` | — | Terminal | — |

A reversal never mutates the original `POSTED` row; it creates a `REVERSED`-marked link plus a new `LoanTransaction` reversal entry. A corrected payment is posted as a brand-new `Payment` record.

**Resolved in Stage 10 — both transitions are now live and proven end-to-end**, including allocation (oldest-installment-first, interest before principal — `apps/repayments/services.py::record_payment()`), overpayment rejection, duplicate-submission/duplicate-reference protection, and reversal correctly restoring the ledger, installment statuses, `Loan.amount_repaid`, and (where applicable) reopening a `PAID_OFF` loan. Verified live: a 4-installment GHS 1,200 loan taken through a partial payment, a final payoff (multi-installment allocation spanning 3 installments in one payment), and a full reversal of that payoff — each step's resulting balances matched hand-calculated expectations exactly, and `manage.py reconcile` confirmed the loan clean after every step.

## 6. SMSMessage

States: `PENDING`, `PROCESSING`, `SENT`, `DELIVERED`, `FAILED`, `CANCELLED`.

| From | To | Trigger |
|---|---|---|
| — | `PENDING` | Message record created (immediate event or scheduled reminder) |
| `PENDING` | `PROCESSING` | Scheduler/immediate-send picks the message up |
| `PROCESSING` | `SENT` | Hubtel accepts the request, returns a provider message ID |
| `PROCESSING` | `FAILED` | Send attempt fails (timeout, 4xx, 5xx, malformed response) |
| `SENT` | `DELIVERED` | Status-query confirms delivery |
| `SENT` | `FAILED` | Status-query reports failure |
| `FAILED` | `PENDING` | Retry scheduled (`attempt_count < max`, `next_attempt_at` reached) |
| `FAILED` | `CANCELLED` | Attempt limit reached, or admin cancels (e.g. installment paid before reminder went out) |
| `PENDING` | `CANCELLED` | Admin cancels before send |
| `DELIVERED` / `CANCELLED` | — | Terminal |

A financial action (disbursement, repayment) is never rolled back because of any state on this table — see `SECURITY.md` and Section 17 of the master prompt.

**Resolved in Stage 11 — the full catalog is live**, superseding the Stage 4/7 provisional `MessageType` set. Immediate-event messages (`LOAN_OFFER_READY`, `OFFER_ACCEPTED_CUSTOMER`/`ADMIN`, `LOAN_APPROVED`, `LOAN_DISBURSED_CUSTOMER`/`ADMIN`, `PAYMENT_RECEIVED_CUSTOMER`/`ADMIN`, `LOAN_PAID_OFF_CUSTOMER`/`ADMIN`) are recorded `PENDING` inside the same transaction as the state change they describe, then dispatched via `transaction.on_commit()` (`apps/messaging/services.py::dispatch_after_commit()`) — no queue needed, and a send failure can never affect the already-committed financial/state row, satisfying Section 17's ordering requirement without Celery/Redis. Scheduled reminders (`REPAYMENT_DUE_5_DAYS` through `REPAYMENT_OVERDUE`) are created and dispatched by `manage.py process_due_sms`, proven idempotent (a second run the same business date creates zero duplicates) and correctly using an installment's *remaining* outstanding amount after a partial payment.

**Known limitation — `SENT` → `DELIVERED` is not currently reachable** (see `integrations/hubtel/hubtel.py`'s module docstring): Hubtel's public SMS product confirms delivery via an account-level callback webhook, not a documented pull/status-query endpoint, so `HubtelSMSProvider.get_status()` returns `UNKNOWN` and `manage.py query_sms_status` is best-effort only. Flagged, not silently worked around — revisit if/when a confirmed status endpoint or a callback receiver is added.

## 7. Traceability

This matrix is enforced in domain services built in Stage 4 (skeleton + guards), exercised in full by Stages 6–11 as each workflow is implemented, and re-verified in Stage 14's permission/workflow review. See `BUILD_PROGRESS.md` for the open decisions summary and stage mapping.
