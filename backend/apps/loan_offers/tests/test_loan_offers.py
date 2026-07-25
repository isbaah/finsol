from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.loan_offers import services
from apps.loan_offers.models import MAX_TERM_COUNT, LoanOffer
from apps.loan_requests.models import LoanRequest
from common.domain import InvalidTransitionError
from tests.factories import make_agreement, make_loan_request, make_offer, make_staff_user

Status = LoanOffer.Status


@pytest.mark.django_db
class TestLoanOfferConstraints:
    def test_principal_must_be_positive(self):
        with transaction.atomic(), pytest.raises(IntegrityError):
            make_offer(principal=Decimal("0.00"))

    def test_term_count_cannot_exceed_the_documented_safe_bound(self):
        with transaction.atomic(), pytest.raises(IntegrityError):
            make_offer(term_count=MAX_TERM_COUNT + 1, installment_count=MAX_TERM_COUNT + 1)

    def test_version_number_is_unique_per_request(self):
        loan_request = make_loan_request()
        make_offer(loan_request, version_number=1)

        with transaction.atomic(), pytest.raises(IntegrityError):
            make_offer(loan_request, version_number=1)


@pytest.mark.django_db
class TestAcceptedOfferImmutability:
    def test_financial_fields_are_frozen_once_accepted(self):
        offer = make_offer()
        offer.status = Status.SENT
        offer.save(update_fields=["status"])
        offer.status = Status.ACCEPTED
        offer.save(update_fields=["status"])

        offer.principal = Decimal("9999.00")
        with pytest.raises(ValueError):
            offer.save()

    def test_non_financial_fields_remain_editable_after_acceptance(self):
        offer = make_offer()
        offer.status = Status.ACCEPTED
        offer.save(update_fields=["status"])

        offer.internal_notes = "reviewed twice"
        offer.save()  # must not raise

        offer.refresh_from_db()
        assert offer.internal_notes == "reviewed twice"


@pytest.mark.django_db
class TestCreateOfferWithSchedule:
    def test_first_offer_is_version_one(self):
        loan_request = make_loan_request(status=LoanRequest.Status.UNDER_REVIEW)
        officer = make_staff_user("LOAN_OFFICER")

        offer = services.create_offer_with_schedule(
            loan_request,
            officer=officer,
            principal=Decimal("1000.00"),
            interest_rate_percent=Decimal("10.00"),
            term_count=2,
            term_unit=LoanOffer.TermUnit.MONTH,
            first_due_date=date(2026, 9, 1),
            total_interest=Decimal("100.00"),
            total_repayable=Decimal("1100.00"),
            installment_count=2,
            installments=[
                {
                    "sequence_number": 1,
                    "due_date": date(2026, 9, 1),
                    "principal_due": Decimal("500.00"),
                    "interest_due": Decimal("50.00"),
                    "total_due": Decimal("550.00"),
                },
                {
                    "sequence_number": 2,
                    "due_date": date(2026, 10, 1),
                    "principal_due": Decimal("500.00"),
                    "interest_due": Decimal("50.00"),
                    "total_due": Decimal("550.00"),
                },
            ],
        )

        assert offer.version_number == 1
        assert offer.installments.count() == 2

    def test_second_offer_for_same_request_is_version_two(self):
        loan_request = make_loan_request()
        make_offer(loan_request, version_number=1)

        offer = services.create_offer_with_schedule(
            loan_request,
            officer=make_staff_user("LOAN_OFFICER"),
            principal=Decimal("1000.00"),
            interest_rate_percent=Decimal("10.00"),
            term_count=1,
            term_unit=LoanOffer.TermUnit.MONTH,
            first_due_date=date(2026, 9, 1),
            total_interest=Decimal("100.00"),
            total_repayable=Decimal("1100.00"),
            installment_count=1,
            installments=[
                {
                    "sequence_number": 1,
                    "due_date": date(2026, 9, 1),
                    "principal_due": Decimal("1000.00"),
                    "interest_due": Decimal("100.00"),
                    "total_due": Decimal("1100.00"),
                }
            ],
        )

        assert offer.version_number == 2


@pytest.mark.django_db
class TestOfferTransitions:
    def test_send_offer_from_draft(self):
        offer = make_offer()

        result = services.send_offer(offer, officer=make_staff_user("LOAN_OFFICER"))

        assert result.status == Status.SENT
        assert result.sent_at is not None
        result.loan_request.refresh_from_db()
        assert result.loan_request.status == LoanRequest.Status.OFFER_SENT

    def test_send_offer_forbidden_when_not_draft(self):
        offer = make_offer(status=Status.SENT)

        with pytest.raises(InvalidTransitionError):
            services.send_offer(offer, officer=make_staff_user("LOAN_OFFICER"))

    def test_sending_a_new_version_supersedes_the_previously_sent_one(self):
        loan_request = make_loan_request(status=LoanRequest.Status.UNDER_REVIEW)
        officer = make_staff_user("LOAN_OFFICER")
        v1 = make_offer(loan_request, version_number=1)
        services.send_offer(v1, officer=officer)

        v2 = make_offer(loan_request, version_number=2)
        services.send_offer(v2, officer=officer)

        v1.refresh_from_db()
        v2.refresh_from_db()
        assert v1.status == Status.SUPERSEDED
        assert v2.status == Status.SENT

    def test_accept_offer_marks_request_customer_accepted(self):
        offer = make_offer(status=Status.SENT)

        result = services.accept_offer(offer, customer=offer.loan_request.customer)

        assert result.status == Status.ACCEPTED
        assert result.accepted_at is not None
        result.loan_request.refresh_from_db()
        assert result.loan_request.status == LoanRequest.Status.CUSTOMER_ACCEPTED

    def test_reject_offer_marks_request_customer_rejected(self):
        offer = make_offer(status=Status.SENT)

        result = services.reject_offer(
            offer, customer=offer.loan_request.customer, reason="Too high"
        )

        assert result.status == Status.REJECTED
        result.loan_request.refresh_from_db()
        assert result.loan_request.status == LoanRequest.Status.CUSTOMER_REJECTED

    def test_request_revision_marks_offer_rejected_and_request_revision_requested(self):
        offer = make_offer(status=Status.SENT)

        result = services.request_revision(
            offer, customer=offer.loan_request.customer, reason="Lower rate"
        )

        assert result.status == Status.REJECTED
        result.loan_request.refresh_from_db()
        assert result.loan_request.status == LoanRequest.Status.REVISION_REQUESTED

    def test_accept_forbidden_on_non_current_offer(self):
        loan_request = make_loan_request(status=LoanRequest.Status.UNDER_REVIEW)
        officer = make_staff_user("LOAN_OFFICER")
        v1 = make_offer(loan_request, version_number=1)
        services.send_offer(v1, officer=officer)
        v2 = make_offer(loan_request, version_number=2)
        services.send_offer(v2, officer=officer)
        v1.refresh_from_db()

        with pytest.raises(InvalidTransitionError):
            services.accept_offer(v1, customer=loan_request.customer)

    def test_expired_offer_cannot_be_accepted(self):
        offer = make_offer(
            status=Status.SENT, offer_expiry_date=timezone.localdate() - timedelta(days=1)
        )

        with pytest.raises(services.OfferExpiredError):
            services.accept_offer(offer, customer=offer.loan_request.customer)

        offer.refresh_from_db()
        assert offer.status == Status.EXPIRED

    def test_double_acceptance_is_rejected(self):
        offer = make_offer(status=Status.SENT)
        services.accept_offer(offer, customer=offer.loan_request.customer)
        offer.refresh_from_db()

        with pytest.raises(InvalidTransitionError):
            services.accept_offer(offer, customer=offer.loan_request.customer)


@pytest.mark.django_db
def test_agreement_can_be_attached_to_an_accepted_offer():
    offer = make_offer(status=Status.SENT)
    services.accept_offer(offer, customer=offer.loan_request.customer)
    offer.refresh_from_db()

    agreement = make_agreement(offer)

    assert agreement.offer == offer
