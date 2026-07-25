"""Explicit domain transition services for LoanOffer (master prompt Section
11 / docs/STATUS_TRANSITIONS.md Section 2).

Design decision (docs/BUILD_PROGRESS.md Stage 4 notes): the master prompt's
LoanOffer status list (DRAFT/SENT/SUPERSEDED/ACCEPTED/REJECTED/EXPIRED) has
no dedicated "revision requested" state, even though LoanRequest does. A
customer's revision request is modelled as the offer being REJECTED (with a
reason) — REJECTED's own documented semantics ("officer may still create a
new offer version in response") are exactly a revision request's meaning —
while the *request* moves to its own REVISION_REQUESTED state.
"""

from __future__ import annotations

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

import apps.loan_requests.services as loan_requests_services
import apps.messaging.services as messaging_services
from apps.audit.services import record_event
from apps.loan_offers.models import LoanOffer, OfferInstallment
from apps.loan_requests.models import LoanRequest
from common.domain import DomainError, apply_transition

Status = LoanOffer.Status

# An offer may only be created/sent while the parent request is actually
# open for review — not on a request that's already been declined,
# cancelled, converted, or otherwise decided (Section 26: business rules
# belong in the service layer, not inferred by the caller). OFFER_SENT is
# included so an officer can prepare a revised version while the previous
# one is still outstanding, matching send_offer()'s own supersede logic.
_REQUEST_STATUSES_OPEN_FOR_OFFERS = frozenset(
    {
        LoanRequest.Status.UNDER_REVIEW,
        LoanRequest.Status.REVISION_REQUESTED,
        LoanRequest.Status.OFFER_SENT,
    }
)


class OfferExpiredError(DomainError):
    pass


class OfferNotEditableError(DomainError):
    pass


class LoanRequestNotReadyForOfferError(DomainError):
    pass


def create_offer_with_schedule(
    loan_request: LoanRequest,
    *,
    officer,
    principal,
    interest_rate_percent,
    term_count: int,
    term_unit: str,
    first_due_date,
    total_interest,
    total_repayable,
    installment_count: int,
    installments: list[dict],
    offer_expiry_date=None,
    customer_terms: str = "",
    internal_notes: str = "",
) -> LoanOffer:
    """Creates a new DRAFT version and its installment schedule atomically.

    `installments` is a list of dicts with sequence_number/due_date/
    principal_due/interest_due/total_due — the same shape
    AmortizationResult.installments produces (Stage 5), so this is the one
    persistence path used by both a real offer-creation flow and (indirectly,
    via the same shape) anything that later needs to replay a schedule.
    """
    with transaction.atomic():
        # Lock the parent request row to serialize version_number allocation
        # — two concurrent "create draft offer" calls must not compute the
        # same next version_number.
        locked_request = LoanRequest.objects.select_for_update().get(pk=loan_request.pk)
        if locked_request.status not in _REQUEST_STATUSES_OPEN_FOR_OFFERS:
            raise LoanRequestNotReadyForOfferError(
                f"Cannot create an offer for a request in status {locked_request.status!r}."
            )
        next_version = (
            LoanOffer.objects.filter(loan_request=loan_request).aggregate(Max("version_number"))[
                "version_number__max"
            ]
            or 0
        ) + 1
        obj = LoanOffer.objects.create(
            loan_request=loan_request,
            version_number=next_version,
            status=Status.DRAFT,
            principal=principal,
            interest_method=LoanOffer.InterestMethod.FLAT_TOTAL_TERM,
            interest_rate_percent=interest_rate_percent,
            term_count=term_count,
            term_unit=term_unit,
            first_due_date=first_due_date,
            total_interest=total_interest,
            total_repayable=total_repayable,
            installment_count=installment_count,
            offer_expiry_date=offer_expiry_date,
            customer_terms=customer_terms,
            internal_notes=internal_notes,
            created_by=officer,
        )
        _replace_installments(obj, installments)
        record_event(
            actor=officer,
            action="loan_offer.create_draft",
            entity=obj,
            after={
                "version_number": obj.version_number,
                "principal": str(obj.principal),
                "installment_count": obj.installment_count,
            },
        )
        return obj


def _replace_installments(offer: LoanOffer, installments: list[dict]) -> None:
    """Shared by create_offer_with_schedule() and update_draft_offer() — the
    installment rows are always fully replaced as a set, never
    row-by-row-diffed, since a schedule is only ever meaningful as a whole
    (Section 12.5: OfferInstallment is the immutable *proposed* schedule for
    one offer version, not something patched field-by-field).
    """
    offer.installments.all().delete()
    OfferInstallment.objects.bulk_create(
        [
            OfferInstallment(
                offer=offer,
                sequence_number=row["sequence_number"],
                due_date=row["due_date"],
                principal_due=row["principal_due"],
                interest_due=row["interest_due"],
                total_due=row["total_due"],
            )
            for row in installments
        ]
    )


def update_draft_offer(
    offer: LoanOffer,
    *,
    officer,
    principal,
    interest_rate_percent,
    term_count: int,
    term_unit: str,
    first_due_date,
    total_interest,
    total_repayable,
    installment_count: int,
    installments: list[dict],
    offer_expiry_date=None,
    customer_terms: str = "",
    internal_notes: str = "",
) -> LoanOffer:
    """Stage 7: "Allow draft editing before send." Edits the DRAFT offer in
    place — unlike create_offer_with_schedule(), this never allocates a new
    version_number, since nothing has been shown to the customer yet
    (versions are for what's actually been sent, per
    docs/STATUS_TRANSITIONS.md Section 2). Only reachable while
    status == DRAFT; raises OfferNotEditableError otherwise.
    """
    with transaction.atomic():
        obj = LoanOffer.objects.select_for_update().get(pk=offer.pk)
        if obj.status != Status.DRAFT:
            raise OfferNotEditableError("Only a draft offer can be edited.")
        before = {"principal": str(obj.principal), "total_repayable": str(obj.total_repayable)}
        obj.principal = principal
        obj.interest_rate_percent = interest_rate_percent
        obj.term_count = term_count
        obj.term_unit = term_unit
        obj.first_due_date = first_due_date
        obj.total_interest = total_interest
        obj.total_repayable = total_repayable
        obj.installment_count = installment_count
        obj.offer_expiry_date = offer_expiry_date
        obj.customer_terms = customer_terms
        obj.internal_notes = internal_notes
        obj.save()
        _replace_installments(obj, installments)
        record_event(
            actor=officer,
            action="loan_offer.update_draft",
            entity=obj,
            before=before,
            after={"principal": str(obj.principal), "total_repayable": str(obj.total_repayable)},
        )
        return obj


def send_offer(offer: LoanOffer, *, officer) -> LoanOffer:
    with transaction.atomic():
        obj = LoanOffer.objects.select_for_update().get(pk=offer.pk)
        before_status = obj.status
        apply_transition(obj, to=Status.SENT, allowed_from={Status.DRAFT})
        obj.sent_by = officer
        obj.sent_at = timezone.now()
        obj.save(update_fields=["status", "sent_by", "sent_at", "updated_at"])
        record_event(
            actor=officer,
            action="loan_offer.send",
            entity=obj,
            before={"status": before_status},
            after={"status": obj.status},
        )

        # Only one SENT version may exist at a time — supersede whichever
        # previous version is currently SENT for the same request.
        previously_sent = (
            LoanOffer.objects.select_for_update()
            .filter(loan_request=obj.loan_request, status=Status.SENT)
            .exclude(pk=obj.pk)
        )
        for prev in previously_sent:
            prev_before = prev.status
            prev.status = Status.SUPERSEDED
            prev.save(update_fields=["status", "updated_at"])
            record_event(
                actor=None,
                action="loan_offer.superseded",
                entity=prev,
                before={"status": prev_before},
                after={"status": prev.status},
            )

        loan_requests_services.mark_offer_sent(obj.loan_request)

        # Stage 7: "Create LOAN_OFFER_READY SMS record ... do not send real
        # SMS before the messaging integration stage." The Hubtel adapter
        # itself is Stage 11 — this only records intent (PENDING), which is
        # the full boundary placeholder this stage is scoped to build.
        customer = obj.loan_request.customer
        profile = getattr(customer, "customer_profile", None)
        if profile is not None:
            messaging_services.record_offer_ready_sms(offer=obj, customer=customer, profile=profile)

        return obj


def _reject_if_expired(offer_pk) -> None:
    """Lazy expiry check (docs/STATUS_TRANSITIONS.md's open decision:
    enforce at the point of any accept/reject/revision action rather than
    adding a scheduled sweep).

    Runs in its own atomic block, separate from the caller's, so the
    EXPIRED flip actually commits before OfferExpiredError is raised —
    raising from inside the *same* atomic block the caller is using would
    roll the flip back along with everything else, since Django rolls back
    the whole block on any exception escaping it.
    """
    expired = False
    with transaction.atomic():
        offer = LoanOffer.objects.select_for_update().get(pk=offer_pk)
        today = timezone.localdate()
        if (
            offer.status == Status.SENT
            and offer.offer_expiry_date
            and offer.offer_expiry_date < today
        ):
            offer.status = Status.EXPIRED
            offer.save(update_fields=["status", "updated_at"])
            record_event(
                actor=None,
                action="loan_offer.expire",
                entity=offer,
                before={"status": Status.SENT},
                after={"status": Status.EXPIRED},
            )
            expired = True
    if expired:
        raise OfferExpiredError("This offer has expired.")


def accept_offer(offer: LoanOffer, *, customer) -> LoanOffer:
    _reject_if_expired(offer.pk)
    with transaction.atomic():
        obj = LoanOffer.objects.select_for_update().get(pk=offer.pk)
        before_status = obj.status
        apply_transition(obj, to=Status.ACCEPTED, allowed_from={Status.SENT})
        obj.accepted_at = timezone.now()
        obj.save(update_fields=["status", "accepted_at", "updated_at"])
        loan_requests_services.mark_customer_accepted(obj.loan_request, customer=customer)
        record_event(
            actor=customer,
            action="loan_offer.accept",
            entity=obj,
            before={"status": before_status},
            after={"status": obj.status},
        )
        return obj


def reject_offer(offer: LoanOffer, *, customer, reason: str = "") -> LoanOffer:
    _reject_if_expired(offer.pk)
    with transaction.atomic():
        obj = LoanOffer.objects.select_for_update().get(pk=offer.pk)
        before_status = obj.status
        apply_transition(obj, to=Status.REJECTED, allowed_from={Status.SENT})
        obj.save(update_fields=["status", "updated_at"])
        loan_requests_services.mark_customer_rejected(obj.loan_request, customer=customer)
        record_event(
            actor=customer,
            action="loan_offer.reject",
            entity=obj,
            before={"status": before_status},
            after={"status": obj.status},
            reason=reason,
        )
        return obj


def request_revision(offer: LoanOffer, *, customer, reason: str = "") -> LoanOffer:
    _reject_if_expired(offer.pk)
    with transaction.atomic():
        obj = LoanOffer.objects.select_for_update().get(pk=offer.pk)
        before_status = obj.status
        apply_transition(obj, to=Status.REJECTED, allowed_from={Status.SENT})
        obj.save(update_fields=["status", "updated_at"])
        loan_requests_services.mark_revision_requested(obj.loan_request, customer=customer)
        record_event(
            actor=customer,
            action="loan_offer.revision_requested",
            entity=obj,
            before={"status": before_status},
            after={"status": obj.status},
            reason=reason,
        )
        return obj
