"""Repayment posting, allocation, reversal, and reconciliation (master
prompt Section 19 / Section 24 Stage 10).

Allocation rule (Section 19), centralised here and nowhere else: a posted
payment is applied to the loan's outstanding installments oldest-due-first;
within a single installment, interest due is covered before principal due.
`_remaining_interest_and_principal()` derives how much of an installment's
interest/principal is still unpaid purely from its own active (POSTED)
`PaymentAllocation` rows — nothing is stored redundantly, so a reversal
only has to flip the payment's status and recompute, never manually
"undo" a running total.

`post_ledger_entry()` — proven in Stage 4 — is still the only place
`Loan.outstanding_balance` is mutated; this module adds the allocation
layer and `Loan.amount_repaid`/installment/status bookkeeping around it.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone

from apps.audit.services import record_event
from apps.loans.models import Loan, RepaymentInstallment
from apps.repayments.models import LoanTransaction, Payment, PaymentAllocation, PaymentClaim
from common.db.sequences import next_reference_number
from common.domain import DomainError, apply_transition

ZERO = Decimal("0.00")


class InvalidPaymentAmountError(DomainError):
    pass


class LoanNotOpenForRepaymentError(DomainError):
    pass


class OverpaymentError(DomainError):
    pass


class DuplicatePaymentSubmissionError(DomainError):
    pass


class DuplicatePaymentReferenceError(DomainError):
    pass


class ClaimNotAllowedError(DomainError):
    pass


class DuplicateClaimError(DomainError):
    pass


def post_ledger_entry(
    loan: Loan,
    *,
    transaction_type: str,
    amount: Decimal,
    effective_date,
    source_object,
    recorded_by,
    reason: str = "",
) -> LoanTransaction:
    """Signed `amount`: positive increases outstanding balance, negative
    decreases it (see LoanTransaction.amount's docstring). Locks the Loan
    row so `balance_after` is always computed from a consistent read."""
    with transaction.atomic():
        locked_loan = Loan.objects.select_for_update().get(pk=loan.pk)
        new_balance = locked_loan.outstanding_balance + amount
        entry = LoanTransaction.objects.create(
            loan=locked_loan,
            transaction_type=transaction_type,
            amount=amount,
            effective_date=effective_date,
            source_object_type=source_object.__class__.__name__,
            source_object_id=str(source_object.pk),
            balance_after=new_balance,
            recorded_by=recorded_by,
            reason=reason,
        )
        locked_loan.outstanding_balance = new_balance
        locked_loan.save(update_fields=["outstanding_balance", "updated_at"])
        return entry


def _remaining_interest_and_principal(installment: RepaymentInstallment) -> tuple[Decimal, Decimal]:
    """Derived purely from active (POSTED-payment) allocations, so a
    reversed payment's allocations automatically stop counting without any
    separate "undo" bookkeeping."""
    paid = PaymentAllocation.objects.filter(
        installment=installment, payment__status=Payment.Status.POSTED
    ).aggregate(interest=Sum("interest_amount"), principal=Sum("principal_amount"))
    interest_paid = paid["interest"] or ZERO
    principal_paid = paid["principal"] or ZERO
    return (
        max(installment.interest_due - interest_paid, ZERO),
        max(installment.principal_due - principal_paid, ZERO),
    )


def _recompute_installment(installment: RepaymentInstallment) -> RepaymentInstallment:
    """Recomputes amount_paid/outstanding_amount/status from active
    allocations alone (never incremented/decremented in place) — the same
    function runs after both a new payment and a reversal, so the two code
    paths can never drift apart. Never touches a WAIVED installment (a
    waiver is a deliberate, separate, terminal administrative action —
    docs/STATUS_TRANSITIONS.md Section 4).

    Status is a pure derived value here, not a guarded `apply_transition()`
    call — a reversal genuinely needs to move an installment *backward*
    (e.g. PAID -> PARTIALLY_PAID), which the forward-only transition table
    was never meant to describe; see docs/STATUS_TRANSITIONS.md Section 4.
    """
    if installment.status == RepaymentInstallment.Status.WAIVED:
        return installment

    interest_remaining, principal_remaining = _remaining_interest_and_principal(installment)
    outstanding = interest_remaining + principal_remaining
    amount_paid = installment.total_due - outstanding
    today = timezone.localdate()

    if outstanding <= ZERO:
        status = RepaymentInstallment.Status.PAID
    elif amount_paid > ZERO:
        status = RepaymentInstallment.Status.PARTIALLY_PAID
    elif installment.due_date < today:
        status = RepaymentInstallment.Status.OVERDUE
    elif installment.due_date == today:
        status = RepaymentInstallment.Status.DUE
    else:
        status = RepaymentInstallment.Status.UPCOMING

    installment.amount_paid = amount_paid
    installment.outstanding_amount = outstanding
    installment.status = status
    installment.paid_at = timezone.now() if status == RepaymentInstallment.Status.PAID else None
    installment.save(
        update_fields=["amount_paid", "outstanding_amount", "status", "paid_at", "updated_at"]
    )
    return installment


def record_payment(
    loan: Loan,
    *,
    amount: Decimal,
    payment_date,
    payment_method: str,
    recorded_by,
    external_transaction_reference: str = "",
    evidence_file_path: str = "",
    notes: str = "",
    idempotency_key: str = "",
) -> Payment:
    """The single Stage 10 entry point for posting a repayment: creates the
    Payment, allocates it oldest-installment-first (interest before
    principal within each), posts the ledger entry, recomputes every
    touched installment, updates `Loan.amount_repaid`/status, audits, and
    fires customer/admin confirmation SMS — all in one transaction."""
    if amount <= ZERO:
        raise InvalidPaymentAmountError("Payment amount must be greater than zero.")

    with transaction.atomic():
        locked_loan = Loan.objects.select_for_update().get(pk=loan.pk)
        if locked_loan.status not in {Loan.Status.ACTIVE, Loan.Status.OVERDUE}:
            raise LoanNotOpenForRepaymentError(
                f"Loan is in status {locked_loan.status!r}; repayments can only be recorded "
                f"against an {Loan.Status.ACTIVE!r} or {Loan.Status.OVERDUE!r} loan."
            )
        if amount > locked_loan.outstanding_balance:
            raise OverpaymentError(
                f"Payment amount {amount} exceeds the loan's outstanding balance "
                f"{locked_loan.outstanding_balance}."
            )

        receipt_number = next_reference_number(
            "payment_receipt", prefix="RCT", period=str(timezone.now().year)
        )
        try:
            # A nested atomic() (savepoint) — without it, the IntegrityError
            # below would poison the whole outer transaction, and the
            # .exists() lookups in the except block would themselves fail
            # with "current transaction is aborted" instead of running.
            with transaction.atomic():
                payment = Payment.objects.create(
                    receipt_number=receipt_number,
                    loan=locked_loan,
                    amount=amount,
                    payment_date=payment_date,
                    payment_method=payment_method,
                    external_transaction_reference=external_transaction_reference,
                    evidence_file_path=evidence_file_path,
                    notes=notes,
                    status=Payment.Status.POSTED,
                    recorded_by=recorded_by,
                    recorded_at=timezone.now(),
                    idempotency_key=idempotency_key,
                )
        except IntegrityError as exc:
            if idempotency_key and Payment.objects.filter(idempotency_key=idempotency_key).exists():
                raise DuplicatePaymentSubmissionError(
                    "This payment has already been submitted."
                ) from exc
            if (
                external_transaction_reference
                and Payment.objects.filter(
                    external_transaction_reference=external_transaction_reference
                ).exists()
            ):
                raise DuplicatePaymentReferenceError(
                    "This external transaction reference has already been used."
                ) from exc
            raise

        outstanding_installments = list(
            RepaymentInstallment.objects.select_for_update()
            .filter(loan=locked_loan)
            .exclude(status=RepaymentInstallment.Status.WAIVED)
            .exclude(status=RepaymentInstallment.Status.PAID)
            .order_by("sequence_number")
        )
        remaining = amount
        touched_installments = []
        for installment in outstanding_installments:
            if remaining <= ZERO:
                break
            if installment.outstanding_amount <= ZERO:
                continue
            interest_remaining, principal_remaining = _remaining_interest_and_principal(installment)
            take = min(remaining, installment.outstanding_amount)
            interest_portion = min(take, interest_remaining)
            principal_portion = min(take - interest_portion, principal_remaining)
            actual_take = interest_portion + principal_portion
            if actual_take <= ZERO:
                continue
            PaymentAllocation.objects.create(
                payment=payment,
                installment=installment,
                principal_amount=principal_portion,
                interest_amount=interest_portion,
                total_amount=actual_take,
            )
            remaining -= actual_take
            touched_installments.append(installment)

        for installment in touched_installments:
            _recompute_installment(installment)

        # A customer's "I've paid" claim is answered the moment its
        # installment is genuinely settled — no manual review step left.
        PaymentClaim.objects.filter(
            loan=locked_loan,
            status=PaymentClaim.Status.PENDING,
            installment__status=RepaymentInstallment.Status.PAID,
        ).update(
            status=PaymentClaim.Status.RESOLVED,
            resolved_by=recorded_by,
            resolved_at=timezone.now(),
        )

        post_ledger_entry(
            locked_loan,
            transaction_type=LoanTransaction.TransactionType.REPAYMENT,
            amount=-amount,
            effective_date=payment_date,
            source_object=payment,
            recorded_by=recorded_by,
        )
        locked_loan.refresh_from_db(fields=["outstanding_balance"])
        locked_loan.amount_repaid = locked_loan.amount_repaid + amount
        update_fields = ["amount_repaid", "updated_at"]
        if locked_loan.outstanding_balance <= ZERO:
            apply_transition(
                locked_loan,
                to=Loan.Status.PAID_OFF,
                allowed_from={Loan.Status.ACTIVE, Loan.Status.OVERDUE},
            )
            locked_loan.closed_at = timezone.now()
            update_fields += ["status", "closed_at"]
        elif (
            locked_loan.status == Loan.Status.OVERDUE
            and not locked_loan.installments.filter(
                status=RepaymentInstallment.Status.OVERDUE
            ).exists()
        ):
            apply_transition(locked_loan, to=Loan.Status.ACTIVE, allowed_from={Loan.Status.OVERDUE})
            update_fields += ["status"]
        locked_loan.save(update_fields=update_fields)

        record_event(
            actor=recorded_by,
            action="payment.record",
            entity=payment,
            after={
                "amount": str(amount),
                "status": payment.status,
                "receipt_number": receipt_number,
            },
        )

    import apps.messaging.services as messaging_services

    messaging_services.record_payment_sms(loan=locked_loan, payment=payment)
    return payment


def reverse_payment(payment: Payment, *, actor, reason: str) -> Payment:
    with transaction.atomic():
        obj = Payment.objects.select_for_update().get(pk=payment.pk)
        locked_loan = Loan.objects.select_for_update().get(pk=obj.loan_id)
        before_status = obj.status
        apply_transition(obj, to=Payment.Status.REVERSED, allowed_from={Payment.Status.POSTED})
        obj.reversal_reason = reason
        obj.save(update_fields=["status", "reversal_reason", "updated_at"])

        post_ledger_entry(
            locked_loan,
            transaction_type=LoanTransaction.TransactionType.REVERSAL,
            amount=obj.amount,
            effective_date=timezone.localdate(),
            source_object=obj,
            recorded_by=actor,
            reason=reason,
        )

        # Two-step so the locking query never combines FOR UPDATE with
        # DISTINCT (join through `allocations` can repeat rows) — Postgres
        # rejects that combination outright.
        affected_installment_ids = list(
            RepaymentInstallment.objects.filter(allocations__payment=obj)
            .values_list("id", flat=True)
            .distinct()
        )
        affected_installments = list(
            RepaymentInstallment.objects.select_for_update()
            .filter(pk__in=affected_installment_ids)
            .order_by("sequence_number")
        )
        for installment in affected_installments:
            _recompute_installment(installment)

        locked_loan.refresh_from_db(fields=["outstanding_balance"])
        locked_loan.amount_repaid = locked_loan.amount_repaid - obj.amount
        update_fields = ["amount_repaid", "updated_at"]
        # PAID_OFF -> ACTIVE/OVERDUE is a deliberate exception to the
        # forward-only Loan transition table (docs/STATUS_TRANSITIONS.md
        # Section 3) — reversing the payment that paid a loan off must be
        # able to reopen it.
        if locked_loan.status == Loan.Status.PAID_OFF and locked_loan.outstanding_balance > ZERO:
            locked_loan.status = (
                Loan.Status.OVERDUE
                if locked_loan.installments.filter(
                    status=RepaymentInstallment.Status.OVERDUE
                ).exists()
                else Loan.Status.ACTIVE
            )
            locked_loan.closed_at = None
            update_fields += ["status", "closed_at"]
        locked_loan.save(update_fields=update_fields)

        record_event(
            actor=actor,
            action="payment.reverse",
            entity=obj,
            before={"status": before_status},
            after={"status": obj.status},
            reason=reason,
        )
        return obj


def reconcile_loan(loan: Loan) -> list[str]:
    """Read-only check of the three Section 19 invariants for one loan.
    Returns a list of human-readable difference descriptions — empty means
    fully reconciled. Never mutates anything (`manage.py reconcile`: "report
    reconciliation differences without changing records automatically")."""
    differences: list[str] = []

    active_payments_total = (
        Payment.objects.filter(loan=loan, status=Payment.Status.POSTED).aggregate(
            total=Sum("amount")
        )["total"]
        or ZERO
    )
    if active_payments_total != loan.amount_repaid:
        differences.append(
            f"amount_repaid={loan.amount_repaid} but sum(active posted payments)="
            f"{active_payments_total}"
        )

    expected_outstanding = loan.total_repayable - loan.amount_repaid
    if expected_outstanding != loan.outstanding_balance:
        differences.append(
            f"outstanding_balance={loan.outstanding_balance} but total_repayable-amount_repaid="
            f"{expected_outstanding}"
        )

    for installment in loan.installments.all():
        allocated = (
            PaymentAllocation.objects.filter(
                installment=installment, payment__status=Payment.Status.POSTED
            ).aggregate(total=Sum("total_amount"))["total"]
            or ZERO
        )
        expected_installment_outstanding = installment.total_due - allocated
        if (
            installment.status != RepaymentInstallment.Status.WAIVED
            and expected_installment_outstanding != installment.outstanding_amount
        ):
            differences.append(
                f"installment #{installment.sequence_number} outstanding_amount="
                f"{installment.outstanding_amount} but total_due-allocated="
                f"{expected_installment_outstanding}"
            )

    return differences


def reconcile_all_loans() -> dict:
    """Runs reconcile_loan() across every loan that has moved money
    (DISBURSED/ACTIVE/OVERDUE/PAID_OFF) — pending/cancelled loans have
    nothing to reconcile yet. Returns a summary dict consumed by
    `manage.py reconcile`."""
    relevant_statuses = {
        Loan.Status.DISBURSED,
        Loan.Status.ACTIVE,
        Loan.Status.OVERDUE,
        Loan.Status.PAID_OFF,
    }
    results = {}
    for loan in Loan.objects.filter(status__in=relevant_statuses).order_by("loan_number"):
        differences = reconcile_loan(loan)
        if differences:
            results[loan.loan_number] = differences
    return results


def claim_payment(installment: RepaymentInstallment, *, customer, note: str = "") -> PaymentClaim:
    """Customer-side "I've paid this installment" notice. Informational only:
    it creates a PENDING PaymentClaim for staff to act on and never touches
    balances — record_payment() remains the only money path (and it
    auto-resolves the claim once the installment is genuinely PAID)."""
    if installment.status in (
        RepaymentInstallment.Status.PAID,
        RepaymentInstallment.Status.WAIVED,
    ):
        raise ClaimNotAllowedError("This installment is already settled.")
    if installment.loan.status not in (Loan.Status.ACTIVE, Loan.Status.OVERDUE):
        raise ClaimNotAllowedError("This loan is not currently open for repayment.")

    try:
        with transaction.atomic():
            claim = PaymentClaim.objects.create(
                loan=installment.loan,
                installment=installment,
                customer=customer,
                note=note,
            )
    except IntegrityError as exc:
        raise DuplicateClaimError(
            "You've already told us about this payment — the team is reviewing it."
        ) from exc

    record_event(
        actor=customer,
        action="payment_claim.create",
        entity=claim,
        after={
            "loan_number": installment.loan.loan_number,
            "sequence_number": installment.sequence_number,
        },
    )
    return claim


def resolve_payment_claim(claim: PaymentClaim, *, actor) -> PaymentClaim:
    """Manual staff resolution, for claims where no matching payment ever
    arrives (mistaken/duplicate claims). Recording the actual payment
    auto-resolves instead — see record_payment()."""
    apply_transition(
        claim, to=PaymentClaim.Status.RESOLVED, allowed_from={PaymentClaim.Status.PENDING}
    )
    claim.resolved_by = actor
    claim.resolved_at = timezone.now()
    claim.save(update_fields=["status", "resolved_by", "resolved_at", "updated_at"])
    record_event(actor=actor, action="payment_claim.resolve", entity=claim)
    return claim
