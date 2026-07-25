from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.loan_offers import services as offer_services
from apps.loan_offers.models import LoanOffer
from apps.loans import services
from apps.loans.models import Disbursement, Loan, RepaymentInstallment
from common.domain import InvalidTransitionError
from tests.factories import make_agreement, make_offer, make_staff_user, make_user

Status = Loan.Status


def _make_loan(**overrides) -> Loan:
    offer = make_offer(status=LoanOffer.Status.SENT)
    offer_services.accept_offer(offer, customer=offer.loan_request.customer)
    offer.refresh_from_db()
    agreement = make_agreement(offer)
    return services.create_loan(offer.loan_request, offer, agreement)


@pytest.mark.django_db
class TestCreateLoan:
    def test_creates_pending_approval_with_a_loan_number(self):
        loan = _make_loan()

        assert loan.status == Status.PENDING_APPROVAL
        assert loan.loan_number.startswith("LN-")
        assert loan.outstanding_balance == loan.total_repayable

    def test_marks_loan_request_converted_to_loan(self):
        loan = _make_loan()

        loan.loan_request.refresh_from_db()
        assert loan.loan_request.status == "CONVERTED_TO_LOAN"

    def test_loan_numbers_are_unique(self):
        first = _make_loan()
        second = _make_loan()

        assert first.loan_number != second.loan_number


@pytest.mark.django_db
class TestLoanConstraints:
    def test_principal_must_be_positive(self):
        loan = _make_loan()

        with transaction.atomic(), pytest.raises(IntegrityError):
            Loan.objects.filter(pk=loan.pk).update(principal=Decimal("-1.00"))

    def test_disbursement_is_one_per_loan(self):
        loan = _make_loan()
        finance = make_staff_user("FINANCE_OFFICER")
        Disbursement.objects.create(
            loan=loan,
            amount=loan.principal,
            method=Disbursement.Method.MOBILE_MONEY,
            recorded_by=finance,
            recorded_at=timezone.now(),
        )

        with transaction.atomic(), pytest.raises(IntegrityError):
            Disbursement.objects.create(
                loan=loan,
                amount=loan.principal,
                method=Disbursement.Method.MOBILE_MONEY,
                recorded_by=finance,
                recorded_at=timezone.now(),
            )

    def test_disbursement_external_reference_unique_when_set(self):
        finance = make_staff_user("FINANCE_OFFICER")
        loan_a = _make_loan()
        loan_b = _make_loan()
        Disbursement.objects.create(
            loan=loan_a,
            amount=loan_a.principal,
            method=Disbursement.Method.BANK,
            external_transaction_reference="DUP-REF",
            recorded_by=finance,
            recorded_at=timezone.now(),
        )

        with transaction.atomic(), pytest.raises(IntegrityError):
            Disbursement.objects.create(
                loan=loan_b,
                amount=loan_b.principal,
                method=Disbursement.Method.BANK,
                external_transaction_reference="DUP-REF",
                recorded_by=finance,
                recorded_at=timezone.now(),
            )

    def test_repayment_installment_sequence_unique_per_loan(self):
        loan = _make_loan()
        RepaymentInstallment.objects.create(
            loan=loan,
            sequence_number=1,
            due_date=timezone.localdate(),
            principal_due=Decimal("100.00"),
            interest_due=Decimal("10.00"),
            total_due=Decimal("110.00"),
            outstanding_amount=Decimal("110.00"),
        )

        with transaction.atomic(), pytest.raises(IntegrityError):
            RepaymentInstallment.objects.create(
                loan=loan,
                sequence_number=1,
                due_date=timezone.localdate(),
                principal_due=Decimal("50.00"),
                interest_due=Decimal("5.00"),
                total_due=Decimal("55.00"),
                outstanding_amount=Decimal("55.00"),
            )


@pytest.mark.django_db
class TestLoanTransitions:
    def test_approve_from_pending_approval(self):
        loan = _make_loan()
        approver = make_staff_user("APPROVER")

        result = services.approve_loan(loan, approver=approver)

        assert result.status == Status.APPROVED_FOR_DISBURSEMENT
        assert result.approved_by == approver

    def test_approve_forbidden_when_not_pending(self):
        loan = _make_loan()
        services.approve_loan(loan, approver=make_staff_user("APPROVER"))
        loan.refresh_from_db()

        with pytest.raises(InvalidTransitionError):
            services.approve_loan(loan, approver=make_staff_user("APPROVER"))

    def test_cancel_allowed_before_disbursement(self):
        loan = _make_loan()

        result = services.cancel_loan(loan, actor=make_user(), reason="Customer withdrew")

        assert result.status == Status.CANCELLED
        assert result.closed_at is not None

    def test_activate_after_disbursement_moves_through_disbursed_to_active(self):
        loan = _make_loan()
        approver = make_staff_user("APPROVER")
        finance = make_staff_user("FINANCE_OFFICER")
        services.approve_loan(loan, approver=approver)
        loan.refresh_from_db()
        disbursement = Disbursement.objects.create(
            loan=loan,
            amount=loan.principal,
            method=Disbursement.Method.MOBILE_MONEY,
            recorded_by=finance,
            recorded_at=timezone.now(),
        )

        result = services.activate_after_disbursement(loan, disbursement=disbursement)

        assert result.status == Status.ACTIVE
        assert result.amount_disbursed == loan.principal
        assert result.disbursed_at is not None

    def test_activate_forbidden_before_approval(self):
        loan = _make_loan()
        finance = make_staff_user("FINANCE_OFFICER")
        disbursement = Disbursement.objects.create(
            loan=loan,
            amount=loan.principal,
            method=Disbursement.Method.MOBILE_MONEY,
            recorded_by=finance,
            recorded_at=timezone.now(),
        )

        with pytest.raises(InvalidTransitionError):
            services.activate_after_disbursement(loan, disbursement=disbursement)

    def test_mark_overdue_and_mark_current_round_trip(self):
        loan = _make_loan()
        loan.status = Status.ACTIVE
        loan.save(update_fields=["status"])

        overdue = services.mark_overdue(loan)
        assert overdue.status == Status.OVERDUE

        current = services.mark_current(overdue)
        assert current.status == Status.ACTIVE

    def test_mark_paid_off_from_active_or_overdue(self):
        loan = _make_loan()
        loan.status = Status.ACTIVE
        loan.save(update_fields=["status"])

        result = services.mark_paid_off(loan)

        assert result.status == Status.PAID_OFF
        assert result.closed_at is not None


@pytest.mark.django_db
class TestCopyScheduleFromOffer:
    def test_copies_every_offer_installment(self):
        loan = _make_loan()

        rows = services.copy_schedule_from_offer(loan, loan.accepted_offer)

        assert len(rows) == loan.accepted_offer.installments.count()
        assert loan.installments.count() == len(rows)
        first = loan.installments.get(sequence_number=1)
        offer_first = loan.accepted_offer.installments.get(sequence_number=1)
        assert first.total_due == offer_first.total_due
        assert first.status == RepaymentInstallment.Status.UPCOMING


@pytest.mark.django_db
class TestWaiveInstallment:
    def test_waive_from_upcoming(self):
        loan = _make_loan()
        services.copy_schedule_from_offer(loan, loan.accepted_offer)
        installment = loan.installments.get(sequence_number=1)

        result = services.waive_installment(
            installment, actor=make_staff_user("SUPER_ADMIN"), reason="Goodwill"
        )

        assert result.status == RepaymentInstallment.Status.WAIVED

    def test_cannot_waive_an_already_paid_installment(self):
        loan = _make_loan()
        services.copy_schedule_from_offer(loan, loan.accepted_offer)
        installment = loan.installments.get(sequence_number=1)
        installment.status = RepaymentInstallment.Status.PAID
        installment.save(update_fields=["status"])

        with pytest.raises(InvalidTransitionError):
            services.waive_installment(
                installment, actor=make_staff_user("SUPER_ADMIN"), reason="Goodwill"
            )
