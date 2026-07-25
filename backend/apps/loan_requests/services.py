"""Explicit domain transition services for LoanRequest (master prompt
Section 11 / docs/STATUS_TRANSITIONS.md Section 1). Every write to `status`
goes through one of these — never a generic serializer `PATCH` (Section 26).

Most of these aren't wired to an API endpoint yet: the actual customer
submission flow (with eligibility checks) is Stage 6, the admin
review/offer actions are Stage 7. This stage builds and proves the state
machine itself, since Stage 4's job is "the auditable domain foundation
before UI-heavy features."
"""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_event
from apps.loan_requests.models import LoanRequest
from common.db.sequences import next_reference_number
from common.domain import apply_transition

Status = LoanRequest.Status


def create_loan_request(
    *,
    customer,
    requested_amount,
    purpose: str,
    requested_term_count: int | None = None,
    requested_term_unit: str = "",
    payout_snapshot: dict | None = None,
    customer_notes: str = "",
) -> LoanRequest:
    """Creates directly in SUBMITTED — the MVP has no separate DRAFT-saving
    UI (STATUS_TRANSITIONS.md Section 1 note)."""
    with transaction.atomic():
        request_number = next_reference_number(
            "loan_request", prefix="REQ", period=str(timezone.now().year)
        )
        obj = LoanRequest.objects.create(
            request_number=request_number,
            customer=customer,
            requested_amount=requested_amount,
            purpose=purpose,
            requested_term_count=requested_term_count,
            requested_term_unit=requested_term_unit,
            payout_snapshot=payout_snapshot or {},
            status=Status.SUBMITTED,
            submitted_at=timezone.now(),
            customer_notes=customer_notes,
        )
        record_event(
            actor=customer,
            action="loan_request.submit",
            entity=obj,
            after={"status": obj.status, "requested_amount": str(obj.requested_amount)},
        )
        return obj


def _transition(
    loan_request: LoanRequest,
    *,
    to: str,
    allowed_from: set[str],
    actor,
    action: str,
    reason: str = "",
    extra_after: dict | None = None,
) -> LoanRequest:
    with transaction.atomic():
        obj = LoanRequest.objects.select_for_update().get(pk=loan_request.pk)
        before_status = obj.status
        apply_transition(obj, to=to, allowed_from=allowed_from)
        obj.save(update_fields=["status", "updated_at"])
        after = {"status": obj.status}
        if extra_after:
            after.update(extra_after)
        record_event(
            actor=actor,
            action=action,
            entity=obj,
            before={"status": before_status},
            after=after,
            reason=reason,
        )
        return obj


def start_review(loan_request: LoanRequest, *, officer) -> LoanRequest:
    with transaction.atomic():
        obj = LoanRequest.objects.select_for_update().get(pk=loan_request.pk)
        before_status = obj.status
        apply_transition(obj, to=Status.UNDER_REVIEW, allowed_from={Status.SUBMITTED})
        obj.assigned_to = officer
        obj.save(update_fields=["status", "assigned_to", "updated_at"])
        record_event(
            actor=officer,
            action="loan_request.start_review",
            entity=obj,
            before={"status": before_status},
            after={"status": obj.status, "assigned_to": str(officer.pk)},
        )
        return obj


def decline(loan_request: LoanRequest, *, actor, reason: str) -> LoanRequest:
    return _transition(
        loan_request,
        to=Status.DECLINED,
        allowed_from={Status.SUBMITTED, Status.UNDER_REVIEW},
        actor=actor,
        action="loan_request.decline",
        reason=reason,
    )


def cancel(loan_request: LoanRequest, *, actor) -> LoanRequest:
    return _transition(
        loan_request,
        to=Status.CANCELLED,
        allowed_from={Status.DRAFT, Status.SUBMITTED, Status.UNDER_REVIEW},
        actor=actor,
        action="loan_request.cancel",
    )


def mark_offer_sent(loan_request: LoanRequest) -> LoanRequest:
    """Called by apps.loan_offers.services when an officer sends an offer —
    system-attributed here since the officer is already the actor recorded
    against the LoanOffer's own AuditEvent.

    OFFER_SENT is included in allowed_from (a same-state "transition") so
    staff can correct and resend a new version while the previous one is
    still outstanding — Section 11: "Sending a revised offer supersedes the
    previous sent offer", which doesn't require the customer to have acted
    on the old one first. See docs/BUILD_PROGRESS.md's Stage 4 notes.
    """
    return _transition(
        loan_request,
        to=Status.OFFER_SENT,
        allowed_from={Status.UNDER_REVIEW, Status.REVISION_REQUESTED, Status.OFFER_SENT},
        actor=None,
        action="loan_request.offer_sent",
    )


def mark_customer_accepted(loan_request: LoanRequest, *, customer) -> LoanRequest:
    return _transition(
        loan_request,
        to=Status.CUSTOMER_ACCEPTED,
        allowed_from={Status.OFFER_SENT},
        actor=customer,
        action="loan_request.customer_accepted",
    )


def mark_customer_rejected(loan_request: LoanRequest, *, customer) -> LoanRequest:
    return _transition(
        loan_request,
        to=Status.CUSTOMER_REJECTED,
        allowed_from={Status.OFFER_SENT},
        actor=customer,
        action="loan_request.customer_rejected",
    )


def mark_revision_requested(loan_request: LoanRequest, *, customer) -> LoanRequest:
    return _transition(
        loan_request,
        to=Status.REVISION_REQUESTED,
        allowed_from={Status.OFFER_SENT},
        actor=customer,
        action="loan_request.revision_requested",
    )


def mark_back_under_review(loan_request: LoanRequest, *, officer) -> LoanRequest:
    return _transition(
        loan_request,
        to=Status.UNDER_REVIEW,
        allowed_from={Status.REVISION_REQUESTED},
        actor=officer,
        action="loan_request.back_under_review",
    )


def mark_converted_to_loan(loan_request: LoanRequest) -> LoanRequest:
    """Called atomically alongside Loan creation in the acceptance flow
    (Stage 8) — system-attributed since the customer's acceptance is already
    the recorded actor on the Agreement/LoanOffer AuditEvents."""
    return _transition(
        loan_request,
        to=Status.CONVERTED_TO_LOAN,
        allowed_from={Status.CUSTOMER_ACCEPTED},
        actor=None,
        action="loan_request.converted_to_loan",
    )
