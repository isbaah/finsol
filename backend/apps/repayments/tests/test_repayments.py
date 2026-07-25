import threading
from datetime import date
from decimal import Decimal

import pytest
from django.db import connection
from django.utils import timezone

from apps.loans.models import Loan, RepaymentInstallment
from apps.repayments import services
from apps.repayments.models import LoanTransaction, Payment
from common.domain import InvalidTransitionError
from tests.factories import make_active_loan, make_staff_user, make_user


@pytest.mark.django_db
class TestLedgerAppendOnly:
    def test_loan_transaction_cannot_be_updated(self):
        loan = make_active_loan()
        entry = services.post_ledger_entry(
            loan,
            transaction_type=LoanTransaction.TransactionType.ADJUSTMENT,
            amount=Decimal("10.00"),
            effective_date=timezone.localdate(),
            source_object=loan,
            recorded_by=make_user(),
        )

        entry.amount = Decimal("999.00")
        with pytest.raises(ValueError):
            entry.save()

    def test_loan_transaction_cannot_be_deleted(self):
        loan = make_active_loan()
        entry = services.post_ledger_entry(
            loan,
            transaction_type=LoanTransaction.TransactionType.ADJUSTMENT,
            amount=Decimal("10.00"),
            effective_date=timezone.localdate(),
            source_object=loan,
            recorded_by=make_user(),
        )

        with pytest.raises(ValueError):
            entry.delete()

        assert LoanTransaction.objects.filter(pk=entry.pk).exists()


@pytest.mark.django_db
class TestPostLedgerEntry:
    def test_positive_amount_increases_outstanding_balance(self):
        loan = make_active_loan()
        starting = loan.outstanding_balance

        entry = services.post_ledger_entry(
            loan,
            transaction_type=LoanTransaction.TransactionType.ADJUSTMENT,
            amount=Decimal("50.00"),
            effective_date=timezone.localdate(),
            source_object=loan,
            recorded_by=make_user(),
        )

        loan.refresh_from_db()
        assert loan.outstanding_balance == starting + Decimal("50.00")
        assert entry.balance_after == loan.outstanding_balance

    def test_negative_amount_decreases_outstanding_balance(self):
        loan = make_active_loan()
        starting = loan.outstanding_balance

        services.post_ledger_entry(
            loan,
            transaction_type=LoanTransaction.TransactionType.REPAYMENT,
            amount=Decimal("-200.00"),
            effective_date=timezone.localdate(),
            source_object=loan,
            recorded_by=make_user(),
        )

        loan.refresh_from_db()
        assert loan.outstanding_balance == starting - Decimal("200.00")


@pytest.mark.django_db(transaction=True)
def test_concurrent_ledger_postings_do_not_lose_updates():
    """Fires many concurrent post_ledger_entry() calls against the same
    loan and proves the final balance reflects every single one — the
    concrete "concurrent transition protection where practical" test.
    Relies on post_ledger_entry()'s select_for_update() on the Loan row to
    serialize the read-modify-write instead of racing to a lost update.
    """
    loan = make_active_loan()
    starting_balance = loan.outstanding_balance
    # make_active_loan() already posts one DISBURSEMENT ledger entry, so the
    # 15 ADJUSTMENT postings below land on top of that baseline.
    starting_transaction_count = loan.transactions.count()
    recorder = make_user()
    errors: list[Exception] = []
    lock = threading.Lock()

    def worker():
        try:
            services.post_ledger_entry(
                loan,
                transaction_type=LoanTransaction.TransactionType.ADJUSTMENT,
                amount=Decimal("1.00"),
                effective_date=timezone.localdate(),
                source_object=loan,
                recorded_by=recorder,
            )
        except Exception as exc:  # pragma: no cover - failure path only
            with lock:
                errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker) for _ in range(15)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    loan.refresh_from_db()
    assert loan.outstanding_balance == starting_balance + Decimal("15.00")
    assert loan.transactions.count() == starting_transaction_count + 15


def _make_repayable_loan(**overrides) -> Loan:
    """A 4-installment, GHS 1,200 loan (GHS 300/installment: GHS 250
    principal + GHS 50 interest) — round numbers made for exact allocation
    math in the tests below."""
    defaults = {
        "principal": Decimal("1000.00"),
        "total_interest": Decimal("200.00"),
        "installment_count": 4,
        # Comfortably in the future relative to any plausible test-run date
        # — every not-yet-paid installment below must land on UPCOMING, not
        # OVERDUE (see _recompute_installment()'s due-date comparison).
        "first_due_date": date(2027, 1, 1),
    }
    defaults.update(overrides)
    return make_active_loan(**defaults)


@pytest.mark.django_db
class TestRecordAndReversePayment:
    def test_record_payment_posts_a_repayment_ledger_entry(self):
        loan = make_active_loan()
        starting = loan.outstanding_balance
        finance = make_staff_user("FINANCE_OFFICER")

        payment = services.record_payment(
            loan,
            amount=Decimal("300.00"),
            payment_date=timezone.localdate(),
            payment_method=Payment.Method.MOBILE_MONEY,
            recorded_by=finance,
        )

        assert payment.status == Payment.Status.POSTED
        assert payment.receipt_number.startswith("RCT-")
        loan.refresh_from_db()
        assert loan.outstanding_balance == starting - Decimal("300.00")
        assert loan.amount_repaid == Decimal("300.00")

    def test_receipt_numbers_are_unique(self):
        loan = make_active_loan()
        finance = make_staff_user("FINANCE_OFFICER")

        first = services.record_payment(
            loan,
            amount=Decimal("100.00"),
            payment_date=timezone.localdate(),
            payment_method=Payment.Method.CASH,
            recorded_by=finance,
        )
        second = services.record_payment(
            loan,
            amount=Decimal("100.00"),
            payment_date=timezone.localdate(),
            payment_method=Payment.Method.CASH,
            recorded_by=finance,
        )

        assert first.receipt_number != second.receipt_number

    def test_idempotency_key_is_unique_when_supplied(self):
        loan = make_active_loan()
        finance = make_staff_user("FINANCE_OFFICER")
        services.record_payment(
            loan,
            amount=Decimal("100.00"),
            payment_date=timezone.localdate(),
            payment_method=Payment.Method.CASH,
            recorded_by=finance,
            idempotency_key="dup-key-1",
        )

        with pytest.raises(services.DuplicatePaymentSubmissionError):
            services.record_payment(
                loan,
                amount=Decimal("100.00"),
                payment_date=timezone.localdate(),
                payment_method=Payment.Method.CASH,
                recorded_by=finance,
                idempotency_key="dup-key-1",
            )

    def test_reverse_payment_flips_status_and_restores_balance(self):
        loan = make_active_loan()
        finance = make_staff_user("FINANCE_OFFICER")
        payment = services.record_payment(
            loan,
            amount=Decimal("300.00"),
            payment_date=timezone.localdate(),
            payment_method=Payment.Method.MOBILE_MONEY,
            recorded_by=finance,
        )
        loan.refresh_from_db()
        after_payment_balance = loan.outstanding_balance

        result = services.reverse_payment(payment, actor=finance, reason="Wrong loan")

        assert result.status == Payment.Status.REVERSED
        assert result.amount == Decimal("300.00")  # original row's amount untouched
        loan.refresh_from_db()
        assert loan.outstanding_balance == after_payment_balance + Decimal("300.00")
        assert loan.amount_repaid == Decimal("0.00")

    def test_reverse_payment_forbidden_when_not_posted(self):
        loan = make_active_loan()
        finance = make_staff_user("FINANCE_OFFICER")
        payment = services.record_payment(
            loan,
            amount=Decimal("300.00"),
            payment_date=timezone.localdate(),
            payment_method=Payment.Method.MOBILE_MONEY,
            recorded_by=finance,
        )
        services.reverse_payment(payment, actor=finance, reason="First reversal")
        payment.refresh_from_db()

        with pytest.raises(InvalidTransitionError):
            services.reverse_payment(payment, actor=finance, reason="Second reversal")


@pytest.mark.django_db
class TestAllocation:
    def test_exact_installment_payment_marks_it_paid(self):
        loan = _make_repayable_loan()
        finance = make_staff_user("FINANCE_OFFICER")

        services.record_payment(
            loan,
            amount=Decimal("300.00"),
            payment_date=timezone.localdate(),
            payment_method=Payment.Method.CASH,
            recorded_by=finance,
        )

        first = loan.installments.get(sequence_number=1)
        assert first.status == RepaymentInstallment.Status.PAID
        assert first.outstanding_amount == Decimal("0.00")
        assert first.amount_paid == Decimal("300.00")
        second = loan.installments.get(sequence_number=2)
        assert second.status == RepaymentInstallment.Status.UPCOMING

    def test_partial_payment_covers_interest_before_principal(self):
        loan = _make_repayable_loan()
        finance = make_staff_user("FINANCE_OFFICER")

        services.record_payment(
            loan,
            amount=Decimal("100.00"),
            payment_date=timezone.localdate(),
            payment_method=Payment.Method.CASH,
            recorded_by=finance,
        )

        first = loan.installments.get(sequence_number=1)
        allocation = first.allocations.get()
        assert allocation.interest_amount == Decimal("50.00")  # interest_due, covered first
        assert allocation.principal_amount == Decimal("50.00")  # remainder to principal
        assert first.status == RepaymentInstallment.Status.PARTIALLY_PAID
        assert first.outstanding_amount == Decimal("200.00")

    def test_multi_installment_payment_spans_several_installments(self):
        loan = _make_repayable_loan()
        finance = make_staff_user("FINANCE_OFFICER")

        services.record_payment(
            loan,
            amount=Decimal("700.00"),
            payment_date=timezone.localdate(),
            payment_method=Payment.Method.CASH,
            recorded_by=finance,
        )

        first, second, third, fourth = loan.installments.order_by("sequence_number")
        assert first.status == RepaymentInstallment.Status.PAID
        assert second.status == RepaymentInstallment.Status.PAID
        assert third.status == RepaymentInstallment.Status.PARTIALLY_PAID
        assert third.amount_paid == Decimal("100.00")
        assert fourth.status == RepaymentInstallment.Status.UPCOMING

    def test_final_payoff_closes_the_loan(self):
        loan = _make_repayable_loan()
        finance = make_staff_user("FINANCE_OFFICER")

        payment = services.record_payment(
            loan,
            amount=Decimal("1200.00"),
            payment_date=timezone.localdate(),
            payment_method=Payment.Method.CASH,
            recorded_by=finance,
        )

        loan.refresh_from_db()
        assert loan.status == Loan.Status.PAID_OFF
        assert loan.outstanding_balance == Decimal("0.00")
        assert loan.amount_repaid == Decimal("1200.00")
        assert loan.closed_at is not None
        assert all(
            installment.status == RepaymentInstallment.Status.PAID
            for installment in loan.installments.all()
        )
        assert payment.status == Payment.Status.POSTED

    def test_reversing_the_final_payment_reopens_the_loan(self):
        loan = _make_repayable_loan()
        finance = make_staff_user("FINANCE_OFFICER")
        payment = services.record_payment(
            loan,
            amount=Decimal("1200.00"),
            payment_date=timezone.localdate(),
            payment_method=Payment.Method.CASH,
            recorded_by=finance,
        )

        services.reverse_payment(payment, actor=finance, reason="Duplicate entry")

        loan.refresh_from_db()
        assert loan.status == Loan.Status.ACTIVE
        assert loan.closed_at is None
        assert loan.outstanding_balance == Decimal("1200.00")
        assert all(
            installment.status == RepaymentInstallment.Status.UPCOMING
            for installment in loan.installments.all()
        )

    def test_overpayment_is_rejected(self):
        loan = _make_repayable_loan()
        finance = make_staff_user("FINANCE_OFFICER")

        with pytest.raises(services.OverpaymentError):
            services.record_payment(
                loan,
                amount=Decimal("1200.01"),
                payment_date=timezone.localdate(),
                payment_method=Payment.Method.CASH,
                recorded_by=finance,
            )

    def test_duplicate_external_reference_is_rejected(self):
        loan = _make_repayable_loan()
        finance = make_staff_user("FINANCE_OFFICER")
        services.record_payment(
            loan,
            amount=Decimal("100.00"),
            payment_date=timezone.localdate(),
            payment_method=Payment.Method.MOBILE_MONEY,
            recorded_by=finance,
            external_transaction_reference="TX-100",
        )

        with pytest.raises(services.DuplicatePaymentReferenceError):
            services.record_payment(
                loan,
                amount=Decimal("50.00"),
                payment_date=timezone.localdate(),
                payment_method=Payment.Method.MOBILE_MONEY,
                recorded_by=finance,
                external_transaction_reference="TX-100",
            )

    def test_zero_or_negative_amount_is_rejected(self):
        loan = _make_repayable_loan()
        finance = make_staff_user("FINANCE_OFFICER")

        with pytest.raises(services.InvalidPaymentAmountError):
            services.record_payment(
                loan,
                amount=Decimal("0.00"),
                payment_date=timezone.localdate(),
                payment_method=Payment.Method.CASH,
                recorded_by=finance,
            )

    def test_repayment_rejected_for_a_loan_not_yet_active(self):
        from tests.factories import make_loan

        loan = make_loan()  # PENDING_APPROVAL — never disbursed
        finance = make_staff_user("FINANCE_OFFICER")

        with pytest.raises(services.LoanNotOpenForRepaymentError):
            services.record_payment(
                loan,
                amount=Decimal("10.00"),
                payment_date=timezone.localdate(),
                payment_method=Payment.Method.CASH,
                recorded_by=finance,
            )


@pytest.mark.django_db
class TestReconciliation:
    def test_freshly_disbursed_loan_reconciles_cleanly(self):
        loan = _make_repayable_loan()
        assert services.reconcile_loan(loan) == []

    def test_loan_reconciles_after_a_partial_payment(self):
        loan = _make_repayable_loan()
        finance = make_staff_user("FINANCE_OFFICER")
        services.record_payment(
            loan,
            amount=Decimal("450.00"),
            payment_date=timezone.localdate(),
            payment_method=Payment.Method.CASH,
            recorded_by=finance,
        )
        loan.refresh_from_db()
        assert services.reconcile_loan(loan) == []

    def test_reconcile_loan_reports_a_drifted_amount_repaid(self):
        loan = _make_repayable_loan()
        finance = make_staff_user("FINANCE_OFFICER")
        services.record_payment(
            loan,
            amount=Decimal("300.00"),
            payment_date=timezone.localdate(),
            payment_method=Payment.Method.CASH,
            recorded_by=finance,
        )
        loan.refresh_from_db()
        # Simulate drift by bypassing the service layer directly.
        Loan.objects.filter(pk=loan.pk).update(amount_repaid=Decimal("999.00"))
        loan.refresh_from_db()

        differences = services.reconcile_loan(loan)

        assert any("amount_repaid" in difference for difference in differences)

    def test_reconcile_all_loans_only_reports_loans_with_differences(self):
        clean_loan = _make_repayable_loan()
        drifted_loan = _make_repayable_loan()
        Loan.objects.filter(pk=drifted_loan.pk).update(amount_repaid=Decimal("999.00"))

        results = services.reconcile_all_loans()

        assert clean_loan.loan_number not in results
        assert drifted_loan.loan_number in results


@pytest.mark.django_db(transaction=True)
def test_concurrent_repayments_do_not_lose_updates():
    """Ten threads each post a GHS 10 payment against the same loan; proves
    record_payment()'s select_for_update() on the Loan row serializes
    concurrent postings instead of racing to a lost update (Stage 10's
    explicit "Concurrency protection" test)."""
    loan = _make_repayable_loan()
    finance = make_staff_user("FINANCE_OFFICER")
    errors: list[Exception] = []
    lock = threading.Lock()

    def worker():
        try:
            services.record_payment(
                loan,
                amount=Decimal("10.00"),
                payment_date=timezone.localdate(),
                payment_method=Payment.Method.CASH,
                recorded_by=finance,
            )
        except Exception as exc:  # pragma: no cover - failure path only
            with lock:
                errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    loan.refresh_from_db()
    assert loan.outstanding_balance == Decimal("1100.00")
    assert loan.amount_repaid == Decimal("100.00")
    assert loan.payments.count() == 10
    assert services.reconcile_loan(loan) == []
