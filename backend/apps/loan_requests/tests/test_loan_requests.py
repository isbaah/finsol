from decimal import Decimal

import pytest

from apps.loan_requests import services
from apps.loan_requests.models import LoanRequest
from common.domain import InvalidTransitionError
from tests.factories import make_loan_request, make_staff_user, make_user

Status = LoanRequest.Status


@pytest.mark.django_db
class TestCreateLoanRequest:
    def test_creates_directly_in_submitted_with_a_request_number(self):
        customer = make_user()

        obj = services.create_loan_request(
            customer=customer, requested_amount=Decimal("2500.00"), purpose="School fees"
        )

        assert obj.status == Status.SUBMITTED
        assert obj.request_number.startswith("REQ-")
        assert obj.submitted_at is not None

    def test_request_numbers_are_unique_across_requests(self):
        customer = make_user()

        first = services.create_loan_request(
            customer=customer, requested_amount=Decimal("100.00"), purpose="A"
        )
        second = services.create_loan_request(
            customer=customer, requested_amount=Decimal("100.00"), purpose="B"
        )

        assert first.request_number != second.request_number


@pytest.mark.django_db
class TestLoanRequestTransitions:
    def test_start_review_from_submitted_sets_assignee(self):
        loan_request = make_loan_request(status=Status.SUBMITTED)
        officer = make_staff_user("LOAN_OFFICER")

        result = services.start_review(loan_request, officer=officer)

        assert result.status == Status.UNDER_REVIEW
        assert result.assigned_to == officer

    def test_start_review_from_under_review_is_rejected(self):
        loan_request = make_loan_request(status=Status.UNDER_REVIEW)
        officer = make_staff_user("LOAN_OFFICER")

        with pytest.raises(InvalidTransitionError):
            services.start_review(loan_request, officer=officer)

    def test_decline_allowed_from_submitted_and_under_review(self):
        for start_status in (Status.SUBMITTED, Status.UNDER_REVIEW):
            loan_request = make_loan_request(status=start_status)
            result = services.decline(
                loan_request, actor=make_staff_user("LOAN_OFFICER"), reason="No"
            )
            assert result.status == Status.DECLINED

    def test_decline_forbidden_from_terminal_status(self):
        loan_request = make_loan_request(status=Status.DECLINED)

        with pytest.raises(InvalidTransitionError):
            services.decline(loan_request, actor=make_staff_user("LOAN_OFFICER"), reason="No")

    def test_cancel_allowed_from_draft_submitted_under_review(self):
        for start_status in (Status.DRAFT, Status.SUBMITTED, Status.UNDER_REVIEW):
            loan_request = make_loan_request(status=start_status)
            result = services.cancel(loan_request, actor=loan_request.customer)
            assert result.status == Status.CANCELLED

    def test_cancel_forbidden_after_offer_sent(self):
        loan_request = make_loan_request(status=Status.OFFER_SENT)

        with pytest.raises(InvalidTransitionError):
            services.cancel(loan_request, actor=loan_request.customer)

    def test_mark_offer_sent_allowed_from_under_review_and_revision_requested(self):
        for start_status in (Status.UNDER_REVIEW, Status.REVISION_REQUESTED):
            loan_request = make_loan_request(status=start_status)
            result = services.mark_offer_sent(loan_request)
            assert result.status == Status.OFFER_SENT

    def test_customer_accept_reject_and_revision_all_require_offer_sent(self):
        for action, expected in (
            (services.mark_customer_accepted, Status.CUSTOMER_ACCEPTED),
            (services.mark_customer_rejected, Status.CUSTOMER_REJECTED),
            (services.mark_revision_requested, Status.REVISION_REQUESTED),
        ):
            loan_request = make_loan_request(status=Status.OFFER_SENT)
            result = action(loan_request, customer=loan_request.customer)
            assert result.status == expected

    def test_customer_accept_forbidden_when_not_offer_sent(self):
        loan_request = make_loan_request(status=Status.SUBMITTED)

        with pytest.raises(InvalidTransitionError):
            services.mark_customer_accepted(loan_request, customer=loan_request.customer)

    def test_back_under_review_from_revision_requested(self):
        loan_request = make_loan_request(status=Status.REVISION_REQUESTED)

        result = services.mark_back_under_review(
            loan_request, officer=make_staff_user("LOAN_OFFICER")
        )

        assert result.status == Status.UNDER_REVIEW

    def test_converted_to_loan_from_customer_accepted(self):
        loan_request = make_loan_request(status=Status.CUSTOMER_ACCEPTED)

        result = services.mark_converted_to_loan(loan_request)

        assert result.status == Status.CONVERTED_TO_LOAN

    def test_converted_to_loan_forbidden_without_acceptance(self):
        loan_request = make_loan_request(status=Status.OFFER_SENT)

        with pytest.raises(InvalidTransitionError):
            services.mark_converted_to_loan(loan_request)

    def test_terminal_states_accept_no_further_transitions(self):
        for terminal in (
            Status.CUSTOMER_REJECTED,
            Status.DECLINED,
            Status.CANCELLED,
            Status.CONVERTED_TO_LOAN,
        ):
            loan_request = make_loan_request(status=terminal)
            with pytest.raises(InvalidTransitionError):
                services.start_review(loan_request, officer=make_staff_user("LOAN_OFFICER"))

    def test_each_transition_writes_an_audit_event(self):
        from apps.audit.models import AuditEvent

        loan_request = make_loan_request(status=Status.SUBMITTED)
        services.start_review(loan_request, officer=make_staff_user("LOAN_OFFICER"))

        assert AuditEvent.objects.filter(
            entity_type="LoanRequest",
            entity_id=str(loan_request.pk),
            action="loan_request.start_review",
        ).exists()
