# Data Model

Status: Locked shape for MVP (Stage 0). Implemented as Django models in Stage 4. All entities use UUID primary keys unless noted; all mutable records carry `created_at`/`updated_at` timezone-aware timestamps.

## 1. Entity relationship overview

```text
User (allauth) ──1:1── CustomerProfile
                              │
                              │ 1:N
                              ▼
                        LoanRequest ──1:N── LoanOffer ──1:N── OfferInstallment
                              │                  │ 1:1
                              │                  ▼
                              │              Agreement
                              │                  │ 1:1
                              │                  ▼
                              └──────────────► Loan
                                                 │
                       ┌─────────────┬───────────┼───────────────┬──────────────┐
                       ▼             ▼           ▼               ▼              ▼
              RepaymentInstallment Disbursement  Payment      LoanTransaction  (SMSMessage,
                       │                          │                            AuditEvent —
                       │                          ▼                            referenced by
                       │                    PaymentAllocation                  entity_type/ID)
                       └───────────────────────────┘
```

`SMSMessage` and `AuditEvent` reference other entities by `related` foreign keys / generic `entity_type` + `entity_id` rather than being embedded in the diagram above, since they attach to many entity types.

## 2. Entities

### 2.1 User
Custom Django user model, UUID PK. Fields: `id`, `email` (unique, case-insensitive), `first_name`, `last_name`, `is_active`, `is_staff`, `date_joined`, plus allauth-managed relationships (email addresses, social accounts). Email is the login identifier — no separate username.

### 2.2 CustomerProfile
One-to-one with `User`. Fields: `id`, `user`, `phone_number_e164`, `phone_country_code`, `address_line_1` (opt), `address_line_2` (opt), `city` (opt), `country` (default `GH`), `preferred_disbursement_method` (`MOBILE_MONEY` | `BANK`), mobile-money network + number (conditionally required), bank name + account name + account number (conditionally required), `profile_completed_at`, `created_at`, `updated_at`.

Validation: E.164 normalization via `phonenumbers`; conditional-required fields enforced by the selected payout method; full account details masked in all normal API responses/UI and only revealed through an explicit, audited staff workflow; never written to logs, SMS, analytics, or exception traces.

### 2.3 LoanRequest
Fields: `id`, `request_number` (human-readable, generated without race conditions), `customer` (FK → CustomerProfile/User), `requested_amount`, `purpose`, optional requested term count/unit, a payout-details snapshot (or reference to the profile version approved at submission time), `status`, `submitted_at`, `assigned_to` (opt, staff), customer notes, internal admin notes (never exposed to customers), `created_at`, `updated_at`.

### 2.4 LoanOffer
Fields: `id`, `loan_request` (FK), `version_number`, `status`, `principal`, `interest_method` (initially always `FLAT_TOTAL_TERM`), `interest_rate_percent`, `term_count`, `term_unit` (`WEEK` | `MONTH`), `first_due_date`, `total_interest`, `total_repayable`, `installment_count`, optional `offer_expiry_date`, customer-facing terms text, internal notes, `created_by`, `sent_by` (opt), `sent_at` (opt), `accepted_at` (opt), `created_at`, `updated_at`.

Constraints: unique `(loan_request, version_number)`; `principal > 0`; `interest_rate_percent >= 0`; `term_count > 0` and within a documented safe upper bound; once `status = ACCEPTED`, the offer's financial fields and computed totals are immutable at the application-service layer, backed by a database constraint or trigger-equivalent check where practical.

### 2.5 OfferInstallment
The immutable proposed schedule attached to an offer. Fields: `offer` (FK), `sequence_number`, `due_date`, `principal_due`, `interest_due`, `total_due`. Constraint: unique `(offer, sequence_number)`.

### 2.6 Agreement
Fields: `id`, `offer` (1:1), `customer`, typed legal name, acceptance checkbox text/version, signature image file path, signature image SHA-256 hash, generated agreement PDF path, PDF SHA-256 hash, accepted IP address, accepted user agent, accepted timestamp, email delivery status, email provider reference (opt), `created_at`.

Immutable after successful creation. Corrections require a new offer → new agreement, never an edit to an accepted record.

### 2.7 Loan
Fields: `id`, `loan_number` (human-readable), `customer`, `loan_request` (FK), `accepted_offer` (FK), `agreement` (FK), `status`, `principal`, `total_interest`, `total_repayable`, `amount_disbursed`, `amount_repaid`, `outstanding_balance`, `approved_by` (opt), `approved_at` (opt), `disbursed_at` (opt), `closed_at` (opt), `created_at`, `updated_at`.

`amount_repaid`/`outstanding_balance` are authoritative ledger-derived values, reconciled by service logic — never trusted from a frontend-submitted value.

### 2.8 RepaymentInstallment
The active servicing schedule, copied from the accepted offer's `OfferInstallment` rows at loan-activation time (Stage 9). Fields: `loan`, `sequence_number`, `due_date`, `principal_due`, `interest_due`, `total_due`, `amount_paid`, `outstanding_amount`, `status`, `paid_at` (opt), `created_at`, `updated_at`. Constraint: unique `(loan, sequence_number)`.

### 2.9 Disbursement
MVP supports exactly one full disbursement per loan, modelled explicitly (not inferred) so a future partial/staged disbursement feature doesn't require a schema rewrite. Fields: `id`, `loan`, `amount`, `method`, masked payout-destination snapshot, external transaction reference (unique when supplied), payment evidence file (opt), notes, `recorded_by`, `recorded_at`, `created_at`.

Constraints: one active disbursement per loan; amount must match the approved disbursement amount unless an explicit, authorised exception process is added later.

### 2.10 Payment
Fields: `id`, `receipt_number` (human-readable), `loan`, `amount`, `payment_date`, `payment_method`, external transaction reference (unique when provided), evidence file (opt), notes, `status` (`POSTED` | `REVERSED`), `recorded_by`, `recorded_at`, reversal relationship + reason (where applicable), `created_at`.

Never edited to "correct" a mistake — corrections are a reversal of the original plus a new correct payment. Idempotency protection against accidental double submission is mandatory.

### 2.11 PaymentAllocation
Fields: `payment` (FK), `installment` (FK), `principal_amount`, `interest_amount`, `total_amount`. Allocation rows for a payment must sum exactly to the posted payment amount, subject to any explicitly defined unapplied-amount rule (none defined for MVP — overpayment beyond outstanding balance is rejected, see `PRODUCT_ASSUMPTIONS.md`/Section 19 of the master prompt).

### 2.12 LoanTransaction
Append-only ledger. Transaction types: `DISBURSEMENT`, `REPAYMENT`, `REVERSAL`, `ADJUSTMENT`, `WRITE_OFF`. Fields: `loan`, `transaction_type`, signed amount or explicit debit/credit fields, effective date, source object type + ID, balance after transaction, `recorded_by`, reason, `created_at`. No update/delete API surface is ever exposed for this table.

### 2.13 SMSMessage
Fields: `id`, related customer/loan/installment (where applicable), `message_type`, `recipient_phone_e164`, `message_body` (exact rendered text sent, for audit), `scheduled_for`, reminder slot (where applicable), `status`, `provider_message_id`, provider response code, attempt count, `next_attempt_at`, `sent_at`, `delivered_at`, `failed_at`, last error summary, `created_at`, `updated_at`.

Uniqueness constraint for scheduled reminders: `(installment, message_type, reminder_business_date, reminder_slot)` — prevents duplicate reminders across repeated scheduler runs. Manual reminders are a distinct, explicitly-actioned message type and may repeat, but always record the admin actor and reason.

### 2.14 AuditEvent
Append-only. Fields: `actor` (nullable for system events), actor role snapshot, action code, entity type, entity ID, before-JSON (redacted), after-JSON (redacted), request correlation ID, IP address, user agent, reason (where required), `created_at`.

Never contains: passwords, session secrets, Hubtel credentials, full bank/mobile-money account details, or signature image bytes.

## 3. Cross-cutting rules

- UUID primary keys for all externally referenced domain objects — no sequential database IDs are exposed via the API.
- Timezone-aware datetimes throughout; dates (e.g. `due_date`) are stored as dates, not midnight datetimes, to avoid timezone-shift bugs on due-date boundaries.
- Human-readable reference numbers (`request_number`, `loan_number`, `receipt_number`) are generated by a race-condition-safe generator (Stage 4), independent of the UUID primary key.
- Database constraints protect invariants wherever the ORM can express them (uniqueness, check constraints on amounts/rates, foreign-key integrity) — application-level validation is a second layer, not a replacement.

## 4. Traceability

This shape is implemented in Stage 4 ("Core Domain Models and State Transition Services"). The amortization-specific fields (`OfferInstallment`, `RepaymentInstallment`, offer totals) are exercised against the calculation engine in Stage 5. See `BUILD_PROGRESS.md` for the full requirement-to-stage matrix.
