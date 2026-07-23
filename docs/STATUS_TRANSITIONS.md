# Status Transitions

Status: Draft transition matrix for Stage 0, to be validated and encoded as service-layer guards in Stage 4. The master prompt (Section 11) defines the state *names*; this document defines the allowed *transitions*, the actor who may trigger each one, and flags genuine ambiguities left open by the spec.

General rule (Section 11 / Section 26): every transition below is implemented as an explicit domain service function, wrapped in `transaction.atomic()` with `select_for_update()` on the affected row(s) where concurrent access is plausible. Invalid transitions raise a domain-specific error and map to a clear API error response. No status field is ever writable through a generic CRUD `PATCH`.

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
| `REVISION_REQUESTED` | `UNDER_REVIEW` or `OFFER_SENT` | Officer reworks and (re)sends a new offer version | `LOAN_OFFICER` |
| `CUSTOMER_ACCEPTED` | `CONVERTED_TO_LOAN` | Agreement created successfully, `Loan` row created atomically (Stage 8) | System, on successful acceptance flow |
| `CUSTOMER_REJECTED` | — | Terminal for this request | — |
| `DECLINED` | — | Terminal | — |
| `CANCELLED` | — | Terminal | — |
| `CONVERTED_TO_LOAN` | — | Terminal for the request; the `Loan` entity now owns the lifecycle | — |

**Open decision — `APPROVED` state**: the master prompt lists `APPROVED` as a `LoanRequest` status (Section 11) but no admin endpoint (Section 14) or stage task (Stages 6–8) references setting it, and the narrative flow moves `CUSTOMER_ACCEPTED` straight to `CONVERTED_TO_LOAN`. Default resolution for Stage 6/7 unless the product owner says otherwise: treat `APPROVED` as **reserved/unused** in the MVP request flow — do not build a transition into it. If a future requirement needs an explicit internal "this request qualifies" gate distinct from offer acceptance, it can be inserted between `UNDER_REVIEW` and `OFFER_SENT` without a schema change. Not blocking Stage 0; must be confirmed before Stage 6 implementation.

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

**Open decision — expiry enforcement mechanism**: the spec includes `offer_expiry_date` and `EXPIRED` but does not specify whether expiry is enforced lazily (checked when the customer opens/acts on the offer, or when staff view it) or by a scheduled sweep. Recommendation: enforce lazily at the point of any accept/reject/revision-request action (reject the action with a domain error if `offer_expiry_date` has passed, and flip status to `EXPIRED` at that moment) rather than adding a new scheduled job — this avoids introducing another cron responsibility beyond `process_due_sms`. To confirm before Stage 7.

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

**Open decision — when `OVERDUE` recomputation runs**: candidates are (a) as part of `process_due_sms`'s daily pass, since it already walks due installments, or (b) a lightweight read-time computed property with a periodic reconciliation job writing the audited status change. Recommendation: piggyback on `process_due_sms` (or a small sibling command run on the same schedule) so no new scheduler entry is needed, and audit the status flip when it happens. To confirm before Stage 10/11.

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

**Open decision — waiver UI**: `WAIVED` is a defined state but no stage task explicitly builds a "waive installment" UI action, and waiving is adjacent to the explicitly out-of-scope "fees/penalties" territory. Recommendation: implement the state and a service function (so the schema and ledger handle it correctly if used), but do not build a dedicated UI button in the MVP unless the product owner requests it — a documented Django-admin-only or management-command path is sufficient until then. To confirm before Stage 10.

## 5. Payment

States: `POSTED`, `REVERSED`.

| From | To | Trigger | Actor |
|---|---|---|---|
| — | `POSTED` | Payment recorded | `FINANCE_OFFICER` |
| `POSTED` | `REVERSED` | Explicit reversal, reason required | `FINANCE_OFFICER` / `SUPER_ADMIN` |
| `REVERSED` | — | Terminal | — |

A reversal never mutates the original `POSTED` row; it creates a `REVERSED`-marked link plus a new `LoanTransaction` reversal entry. A corrected payment is posted as a brand-new `Payment` record.

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

## 7. Traceability

This matrix is enforced in domain services built in Stage 4 (skeleton + guards), exercised in full by Stages 6–11 as each workflow is implemented, and re-verified in Stage 14's permission/workflow review. See `BUILD_PROGRESS.md` for the open decisions summary and stage mapping.
