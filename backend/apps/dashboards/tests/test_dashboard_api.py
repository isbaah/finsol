"""Stage 12: metric-accuracy and access-control tests for the admin
dashboard endpoints. Every scenario builds its data through the real Stage
8–10 service functions (make_active_loan / record_payment), so these tests
verify the documented metric definitions against genuinely-produced state,
not hand-inserted rows."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from freezegun import freeze_time

import apps.repayments.services as repayment_services
from apps.loans.models import Loan, RepaymentInstallment
from apps.messaging.models import SMSMessage
from tests.factories import make_active_loan, make_staff_user, make_user

TODAY = "2026-07-15 12:00:00"

METRICS_URL = "/api/v1/admin/dashboard/metrics/"
CHART_URL = "/api/v1/admin/dashboard/collections-chart/"
UPCOMING_URL = "/api/v1/admin/dashboard/upcoming-repayments/"
OVERDUE_URL = "/api/v1/admin/dashboard/overdue-summary/"
TRANSACTIONS_URL = "/api/v1/admin/dashboard/recent-transactions/"


def _pay(loan, amount, payment_date):
    return repayment_services.record_payment(
        loan,
        amount=Decimal(amount),
        payment_date=payment_date,
        payment_method="MOBILE_MONEY",
        recorded_by=make_staff_user("FINANCE_OFFICER"),
    )


def _make_overdue_loan(*, principal="500.00", due_date):
    """An activated loan whose single installment is overdue — statuses set
    directly, the same way process_due_sms's recomputation would land them."""
    loan = make_active_loan(
        principal=Decimal(principal),
        total_interest=Decimal("0.00"),
        installment_count=1,
        first_due_date=due_date,
    )
    loan.status = Loan.Status.OVERDUE
    loan.save(update_fields=["status"])
    loan.installments.update(status=RepaymentInstallment.Status.OVERDUE)
    return loan


@pytest.mark.django_db
class TestDashboardAccess:
    def test_unauthenticated_is_rejected(self, client):
        for url in (METRICS_URL, CHART_URL, UPCOMING_URL, OVERDUE_URL, TRANSACTIONS_URL):
            assert client.get(url).status_code in (401, 403)

    def test_customer_is_rejected(self, client):
        client.force_login(make_user())
        for url in (METRICS_URL, CHART_URL, UPCOMING_URL, OVERDUE_URL, TRANSACTIONS_URL):
            assert client.get(url).status_code == 403

    def test_auditor_has_read_access(self, client):
        client.force_login(make_staff_user("AUDITOR"))
        for url in (METRICS_URL, CHART_URL, UPCOMING_URL, OVERDUE_URL, TRANSACTIONS_URL):
            assert client.get(url).status_code == 200


@pytest.mark.django_db
class TestDashboardMetrics:
    @freeze_time(TODAY)
    def test_metric_definitions_are_accurate(self, client):
        # Loan A: 1000 + 200 interest over 4 installments of 300, first due
        # 20 Jul — one installment lands in the current month.
        loan_a = make_active_loan(
            principal=Decimal("1000.00"),
            total_interest=Decimal("200.00"),
            installment_count=4,
            first_due_date=date(2026, 7, 20),
        )
        _pay(loan_a, "300.00", date(2026, 7, 10))
        # Loan B: 500 due 5 Jul, now overdue and unpaid.
        _make_overdue_loan(principal="500.00", due_date=date(2026, 7, 5))

        client.force_login(make_staff_user("SUPER_ADMIN"))
        body = client.get(METRICS_URL).json()

        # 1200 - 300 paid on loan A, plus the full 500 still out on loan B.
        assert body["outstanding_portfolio_balance"] == "1400.00"
        # Installments due in July: loan A's 300 (paid or not — "expected"
        # never shrinks) + loan B's 500.
        assert body["amount_due_this_month"] == "800.00"
        assert body["amount_collected_this_month"] == "300.00"
        assert body["overdue_amount"] == "500.00"
        assert body["active_loans"] == 2

    @freeze_time(TODAY)
    def test_reversed_payment_drops_out_of_collected(self, client):
        loan = make_active_loan(
            principal=Decimal("1000.00"),
            total_interest=Decimal("0.00"),
            installment_count=2,
            first_due_date=date(2026, 8, 1),
        )
        payment = _pay(loan, "400.00", date(2026, 7, 10))
        repayment_services.reverse_payment(
            payment, actor=make_staff_user("FINANCE_OFFICER"), reason="Recorded in error"
        )

        client.force_login(make_staff_user("SUPER_ADMIN"))
        body = client.get(METRICS_URL).json()

        assert body["amount_collected_this_month"] == "0.00"
        assert body["outstanding_portfolio_balance"] == "1000.00"

    @freeze_time(TODAY)
    def test_pre_disbursement_loans_are_excluded_from_portfolio(self, client):
        from tests.factories import make_loan

        make_loan(principal=Decimal("9999.00"))  # PENDING_APPROVAL — no money out yet

        client.force_login(make_staff_user("SUPER_ADMIN"))
        body = client.get(METRICS_URL).json()

        assert body["outstanding_portfolio_balance"] == "0.00"
        assert body["active_loans"] == 0
        assert body["pending_approval_count"] == 1


@pytest.mark.django_db
class TestCollectionsChart:
    @freeze_time(TODAY)
    def test_rejects_unsupported_month_windows(self, client):
        client.force_login(make_staff_user("SUPER_ADMIN"))
        assert client.get(CHART_URL, {"months": "7"}).status_code == 400
        assert client.get(CHART_URL, {"months": "abc"}).status_code == 400

    @freeze_time(TODAY)
    def test_series_groups_expected_and_collected_by_month(self, client):
        loan = make_active_loan(
            principal=Decimal("1000.00"),
            total_interest=Decimal("200.00"),
            installment_count=4,
            first_due_date=date(2026, 7, 20),
        )
        _pay(loan, "300.00", date(2026, 7, 10))
        _pay(loan, "100.00", date(2026, 6, 20))

        client.force_login(make_staff_user("SUPER_ADMIN"))
        body = client.get(CHART_URL, {"months": "6"}).json()

        assert len(body) == 6
        assert body[0]["month"] == "2026-02-01"
        assert body[-1]["month"] == "2026-07-01"
        by_month = {row["month"]: row for row in body}
        assert by_month["2026-07-01"]["expected"] == "300.00"
        assert by_month["2026-07-01"]["collected"] == "300.00"
        assert by_month["2026-06-01"]["expected"] == "0.00"
        assert by_month["2026-06-01"]["collected"] == "100.00"
        assert by_month["2026-05-01"]["collected"] == "0.00"

    @freeze_time(TODAY)
    def test_twelve_month_window(self, client):
        client.force_login(make_staff_user("SUPER_ADMIN"))
        body = client.get(CHART_URL, {"months": "12"}).json()
        assert len(body) == 12
        assert body[0]["month"] == "2025-08-01"


@pytest.mark.django_db
class TestUpcomingRepayments:
    @freeze_time(TODAY)
    def test_window_is_under_seven_days_and_excludes_settled_rows(self, client):
        in_window = make_active_loan(
            principal=Decimal("600.00"),
            total_interest=Decimal("0.00"),
            installment_count=2,
            first_due_date=date(2026, 7, 18),  # 3 days out
        )
        make_active_loan(
            principal=Decimal("700.00"),
            total_interest=Decimal("0.00"),
            installment_count=1,
            first_due_date=date(2026, 7, 22),  # exactly 7 days out — excluded
        )
        paid = make_active_loan(
            principal=Decimal("800.00"),
            total_interest=Decimal("0.00"),
            installment_count=1,
            first_due_date=date(2026, 7, 16),
        )
        _pay(paid, "800.00", date(2026, 7, 14))  # settles it — excluded

        client.force_login(make_staff_user("SUPER_ADMIN"))
        body = client.get(UPCOMING_URL).json()

        assert len(body) == 1
        row = body[0]
        assert row["loan_number"] == in_window.loan_number
        assert row["due_date"] == "2026-07-18"
        assert row["days_remaining"] == 3
        assert row["total_due"] == "300.00"
        assert row["last_sms_status"] is None

    @freeze_time(TODAY)
    def test_reports_the_latest_sms_for_the_installment(self, client):
        loan = make_active_loan(
            principal=Decimal("600.00"),
            total_interest=Decimal("0.00"),
            installment_count=1,
            first_due_date=date(2026, 7, 18),
        )
        installment = loan.installments.get(sequence_number=1)
        first = SMSMessage.objects.create(
            customer=loan.customer,
            loan=loan,
            installment=installment,
            message_type=SMSMessage.MessageType.REPAYMENT_DUE_5_DAYS,
            recipient_phone_e164="+233241234567",
            message_body="first",
            status=SMSMessage.Status.FAILED,
        )
        # freeze_time gives both rows an identical auto_now_add timestamp —
        # backdate the first so "latest" is well-defined, as it is in reality.
        SMSMessage.objects.filter(pk=first.pk).update(
            created_at=timezone.now() - timedelta(minutes=5)
        )
        SMSMessage.objects.create(
            customer=loan.customer,
            loan=loan,
            installment=installment,
            message_type=SMSMessage.MessageType.MANUAL_REMINDER,
            recipient_phone_e164="+233241234567",
            message_body="second",
            status=SMSMessage.Status.SENT,
        )

        client.force_login(make_staff_user("SUPER_ADMIN"))
        body = client.get(UPCOMING_URL).json()

        assert len(body) == 1
        assert body[0]["last_sms_status"] == "SENT"
        assert body[0]["last_sms_type"] == "MANUAL_REMINDER"


@pytest.mark.django_db
class TestOverdueSummary:
    @freeze_time(TODAY)
    def test_buckets_by_days_overdue(self, client):
        _make_overdue_loan(principal="100.00", due_date=date(2026, 7, 12))  # 3 days
        _make_overdue_loan(principal="200.00", due_date=date(2026, 7, 8))  # 7 days (boundary)
        _make_overdue_loan(principal="300.00", due_date=date(2026, 6, 15))  # 30 days (boundary)
        _make_overdue_loan(principal="400.00", due_date=date(2026, 6, 10))  # 35 days
        _make_overdue_loan(principal="500.00", due_date=date(2026, 5, 1))  # 75 days

        client.force_login(make_staff_user("SUPER_ADMIN"))
        body = client.get(OVERDUE_URL).json()

        by_label = {bucket["label"]: bucket for bucket in body["buckets"]}
        assert by_label["1-7 days"]["installment_count"] == 2
        assert by_label["1-7 days"]["outstanding_total"] == "300.00"
        assert by_label["8-30 days"]["installment_count"] == 1
        assert by_label["8-30 days"]["outstanding_total"] == "300.00"
        assert by_label["31-60 days"]["installment_count"] == 1
        assert by_label["31-60 days"]["outstanding_total"] == "400.00"
        assert by_label["61+ days"]["installment_count"] == 1
        assert by_label["61+ days"]["outstanding_total"] == "500.00"
        assert body["total_outstanding"] == "1500.00"

    @freeze_time(TODAY)
    def test_empty_book_returns_zeroed_buckets(self, client):
        client.force_login(make_staff_user("SUPER_ADMIN"))
        body = client.get(OVERDUE_URL).json()
        assert body["total_outstanding"] == "0.00"
        assert all(bucket["installment_count"] == 0 for bucket in body["buckets"])


@pytest.mark.django_db
class TestRecentTransactions:
    # Deliberately unfrozen: the endpoint doesn't depend on "today", and
    # real (distinct) created_at timestamps are what newest-first orders by.
    def test_returns_newest_ledger_entries_first(self, client):
        loan = make_active_loan(
            principal=Decimal("1000.00"),
            total_interest=Decimal("0.00"),
            installment_count=2,
            first_due_date=date(2026, 8, 1),
        )
        _pay(loan, "500.00", date(2026, 7, 10))

        client.force_login(make_staff_user("SUPER_ADMIN"))
        body = client.get(TRANSACTIONS_URL).json()

        assert body[0]["transaction_type"] == "REPAYMENT"
        assert body[0]["loan_number"] == loan.loan_number
        types = [row["transaction_type"] for row in body]
        assert "DISBURSEMENT" in types
