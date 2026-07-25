"""Explicit domain transition services for Loan/RepaymentInstallment
(master prompt Section 11 / docs/STATUS_TRANSITIONS.md Sections 3-4).

`create_loan()` is the only way a Loan row comes into existence — called
atomically alongside LoanRequest's CONVERTED_TO_LOAN transition (Stage 8's
acceptance flow owns calling it; this stage just builds and proves it).
`activate_after_disbursement()` is the pure state-machine half of "record a
disbursement" — the full orchestration (creating the Disbursement row,
reconciling the amount, creating the ledger entry, SMS intents) is Stage 9;
this function is what Stage 9 calls once a Disbursement row already exists.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

import apps.loan_requests.services as loan_requests_services
from apps.audit.services import record_event
from apps.loan_offers.models import LoanOffer
from apps.loan_requests.models import LoanRequest
from apps.loans.models import Disbursement, Loan, RepaymentInstallment
from common.db.sequences import next_reference_number
from common.domain import DomainError, apply_transition

Status = Loan.Status
ZERO = Decimal("0.00")


class LoanNotReadyForDisbursementError(DomainError):
    pass


class DisbursementAmountMismatchError(DomainError):
    pass


class DuplicateDisbursementError(DomainError):
    pass


class DuplicateDisbursementReferenceError(DomainError):
    pass


def create_loan(loan_request: LoanRequest, offer: LoanOffer, agreement) -> Loan:
    with transaction.atomic():
        loan_number = next_reference_number("loan", prefix="LN", period=str(timezone.now().year))
        loan = Loan.objects.create(
            loan_number=loan_number,
            customer=loan_request.customer,
            loan_request=loan_request,
            accepted_offer=offer,
            agreement=agreement,
            status=Status.PENDING_APPROVAL,
            principal=offer.principal,
            total_interest=offer.total_interest,
            total_repayable=offer.total_repayable,
            amount_disbursed=ZERO,
            amount_repaid=ZERO,
            outstanding_balance=offer.total_repayable,
        )
        loan_requests_services.mark_converted_to_loan(loan_request)
        record_event(
            actor=None,
            action="loan.create",
            entity=loan,
            after={"status": loan.status, "loan_number": loan.loan_number},
        )
        return loan


def _transition(
    loan: Loan,
    *,
    to: str,
    allowed_from: set[str],
    actor,
    action: str,
    reason: str = "",
    extra_fields: dict | None = None,
) -> Loan:
    with transaction.atomic():
        obj = Loan.objects.select_for_update().get(pk=loan.pk)
        before_status = obj.status
        apply_transition(obj, to=to, allowed_from=allowed_from)
        update_fields = ["status", "updated_at"]
        if extra_fields:
            for field, value in extra_fields.items():
                setattr(obj, field, value)
                update_fields.append(field)
        obj.save(update_fields=update_fields)
        record_event(
            actor=actor,
            action=action,
            entity=obj,
            before={"status": before_status},
            after={"status": obj.status},
            reason=reason,
        )
        return obj


def approve_loan(loan: Loan, *, approver) -> Loan:
    obj = _transition(
        loan,
        to=Status.APPROVED_FOR_DISBURSEMENT,
        allowed_from={Status.PENDING_APPROVAL},
        actor=approver,
        action="loan.approve",
        extra_fields={"approved_by": approver, "approved_at": timezone.now()},
    )

    import apps.messaging.services as messaging_services

    messaging_services.record_loan_approved_sms(loan=obj)
    return obj


def cancel_loan(loan: Loan, *, actor, reason: str = "") -> Loan:
    return _transition(
        loan,
        to=Status.CANCELLED,
        allowed_from={Status.PENDING_APPROVAL, Status.APPROVED_FOR_DISBURSEMENT},
        actor=actor,
        action="loan.cancel",
        reason=reason,
        extra_fields={"closed_at": timezone.now()},
    )


def activate_after_disbursement(loan: Loan, *, disbursement: Disbursement) -> Loan:
    """APPROVED_FOR_DISBURSEMENT -> DISBURSED -> ACTIVE in one atomic
    operation (docs/STATUS_TRANSITIONS.md Section 3: both moves happen
    together, never leaving the loan sitting in DISBURSED)."""
    with transaction.atomic():
        obj = Loan.objects.select_for_update().get(pk=loan.pk)
        before_status = obj.status
        apply_transition(obj, to=Status.DISBURSED, allowed_from={Status.APPROVED_FOR_DISBURSEMENT})
        apply_transition(obj, to=Status.ACTIVE, allowed_from={Status.DISBURSED})
        obj.amount_disbursed = disbursement.amount
        obj.disbursed_at = disbursement.recorded_at
        obj.save(update_fields=["status", "amount_disbursed", "disbursed_at", "updated_at"])
        record_event(
            actor=disbursement.recorded_by,
            action="loan.activate",
            entity=obj,
            before={"status": before_status},
            after={"status": obj.status, "amount_disbursed": str(obj.amount_disbursed)},
        )
        return obj


def mark_overdue(loan: Loan) -> Loan:
    return _transition(
        loan,
        to=Status.OVERDUE,
        allowed_from={Status.ACTIVE},
        actor=None,
        action="loan.mark_overdue",
    )


def mark_current(loan: Loan) -> Loan:
    return _transition(
        loan,
        to=Status.ACTIVE,
        allowed_from={Status.OVERDUE},
        actor=None,
        action="loan.mark_current",
    )


def mark_paid_off(loan: Loan) -> Loan:
    return _transition(
        loan,
        to=Status.PAID_OFF,
        allowed_from={Status.ACTIVE, Status.OVERDUE},
        actor=None,
        action="loan.paid_off",
        extra_fields={"closed_at": timezone.now()},
    )


def copy_schedule_from_offer(loan: Loan, offer: LoanOffer) -> list[RepaymentInstallment]:
    """Populates RepaymentInstallment from the accepted offer's
    OfferInstallment rows — called once, at loan-activation time (Stage 9)."""
    with transaction.atomic():
        rows = [
            RepaymentInstallment(
                loan=loan,
                sequence_number=installment.sequence_number,
                due_date=installment.due_date,
                principal_due=installment.principal_due,
                interest_due=installment.interest_due,
                total_due=installment.total_due,
                amount_paid=ZERO,
                outstanding_amount=installment.total_due,
                status=RepaymentInstallment.Status.UPCOMING,
            )
            for installment in offer.installments.order_by("sequence_number")
        ]
        return RepaymentInstallment.objects.bulk_create(rows)


def waive_installment(
    installment: RepaymentInstallment, *, actor, reason: str
) -> RepaymentInstallment:
    """Implemented per docs/STATUS_TRANSITIONS.md's open decision: the state
    and service function exist so the schema/ledger handle it correctly,
    but no dedicated UI action is built in the MVP."""
    with transaction.atomic():
        obj = RepaymentInstallment.objects.select_for_update().get(pk=installment.pk)
        before_status = obj.status
        apply_transition(
            obj,
            to=RepaymentInstallment.Status.WAIVED,
            allowed_from={
                RepaymentInstallment.Status.UPCOMING,
                RepaymentInstallment.Status.DUE,
                RepaymentInstallment.Status.PARTIALLY_PAID,
                RepaymentInstallment.Status.OVERDUE,
            },
        )
        obj.save(update_fields=["status", "updated_at"])
        record_event(
            actor=actor,
            action="repayment_installment.waive",
            entity=obj,
            before={"status": before_status},
            after={"status": obj.status},
            reason=reason,
        )
        return obj


def _post_disbursement_ledger_entry(loan: Loan, *, disbursement: Disbursement, recorded_by) -> None:
    """A pure audit-trail row — unlike apps/repayments/services.py::
    post_ledger_entry() (used for REPAYMENT/REVERSAL), this never mutates
    `Loan.outstanding_balance`. Section 19's reconciliation formula
    (`outstanding == total_repayable - amount_repaid`) is defined purely in
    terms of repayment, not disbursement — `create_loan()` already sets
    `outstanding_balance = total_repayable` at PENDING_APPROVAL time, before
    any money has moved, so disbursement must leave it unchanged."""
    from apps.repayments.models import LoanTransaction

    LoanTransaction.objects.create(
        loan=loan,
        transaction_type=LoanTransaction.TransactionType.DISBURSEMENT,
        amount=disbursement.amount,
        effective_date=disbursement.recorded_at.date(),
        source_object_type=disbursement.__class__.__name__,
        source_object_id=str(disbursement.pk),
        balance_after=loan.outstanding_balance,
        recorded_by=recorded_by,
    )


def record_disbursement(
    loan: Loan,
    *,
    recorded_by,
    amount: Decimal,
    method: str,
    external_transaction_reference: str = "",
    evidence_file_path: str = "",
    notes: str = "",
) -> Disbursement:
    """Stage 9's single orchestration point for "record a manual
    disbursement": validates the loan is actually ready, that the amount
    matches what was approved (Section 12.9: "Amount must match the
    approved disbursement amount"), creates the Disbursement row, activates
    the loan (APPROVED_FOR_DISBURSEMENT -> DISBURSED -> ACTIVE), copies the
    accepted offer's schedule into RepaymentInstallment rows, and posts the
    ledger entry — all in one transaction, so a partial disbursement can
    never exist.
    """
    with transaction.atomic():
        locked_loan = Loan.objects.select_for_update().get(pk=loan.pk)
        if locked_loan.status != Status.APPROVED_FOR_DISBURSEMENT:
            raise LoanNotReadyForDisbursementError(
                f"Loan is in status {locked_loan.status!r}; it must be "
                f"{Status.APPROVED_FOR_DISBURSEMENT!r} before a disbursement can be recorded."
            )
        if amount != locked_loan.principal:
            raise DisbursementAmountMismatchError(
                "Disbursement amount must exactly match the loan's approved principal."
            )
        if Disbursement.objects.filter(loan=locked_loan).exists():
            raise DuplicateDisbursementError(
                "A disbursement has already been recorded for this loan."
            )
        if (
            external_transaction_reference
            and Disbursement.objects.filter(
                external_transaction_reference=external_transaction_reference
            ).exists()
        ):
            raise DuplicateDisbursementReferenceError(
                "This external transaction reference has already been used."
            )

        payout_snapshot = locked_loan.loan_request.payout_snapshot
        try:
            disbursement = Disbursement.objects.create(
                loan=locked_loan,
                amount=amount,
                method=method,
                masked_payout_snapshot=payout_snapshot,
                external_transaction_reference=external_transaction_reference,
                evidence_file_path=evidence_file_path,
                notes=notes,
                recorded_by=recorded_by,
                recorded_at=timezone.now(),
            )
        except IntegrityError as exc:
            # Second, DB-level safety net behind the pre-checks above — a
            # concurrent request racing between the .exists() checks and
            # this INSERT is still caught by the UniqueConstraints
            # themselves, just surfaced as the same domain error instead of
            # a raw 500 (Section 24 Stage 9: "double-submit and duplicate-
            # reference protection").
            if external_transaction_reference:
                raise DuplicateDisbursementReferenceError(
                    "This external transaction reference has already been used."
                ) from exc
            raise DuplicateDisbursementError(
                "A disbursement has already been recorded for this loan."
            ) from exc

        activate_after_disbursement(locked_loan, disbursement=disbursement)
        copy_schedule_from_offer(locked_loan, locked_loan.accepted_offer)
        _post_disbursement_ledger_entry(
            locked_loan, disbursement=disbursement, recorded_by=recorded_by
        )
        record_event(
            actor=recorded_by,
            action="disbursement.record",
            entity=disbursement,
            after={"amount": str(amount), "method": method},
        )

    # Stage 11: closes the Stage 9 "customer/admin disbursement SMS
    # intents" gap flagged in docs/BUILD_PROGRESS.md. Recorded/dispatched
    # after the disbursement transaction above has closed (committed, if no
    # outer transaction), per Section 17.
    import apps.messaging.services as messaging_services

    messaging_services.record_disbursement_sms(loan=locked_loan, disbursement=disbursement)
    return disbursement
