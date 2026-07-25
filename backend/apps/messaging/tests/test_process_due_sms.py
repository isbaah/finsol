from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.loans.models import Loan, RepaymentInstallment
from apps.messaging.models import SMSMessage
from apps.repayments import services as repayment_services
from apps.repayments.models import Payment
from tests.factories import make_active_loan, make_staff_user

_MORNING_RUN = "2026-09-10T09:00:00+00:00"  # after 08:00, before 16:00 Accra
_AFTERNOON_RUN = "2026-09-10T17:00:00+00:00"  # after 16:00 Accra


def _run(**kwargs):
    out = StringIO()
    call_command("process_due_sms", stdout=out, **kwargs)
    return out.getvalue()


def _single_installment_loan(due_date: date) -> RepaymentInstallment:
    loan = make_active_loan(
        principal=Decimal("1000.00"),
        total_interest=Decimal("0.00"),
        installment_count=1,
        first_due_date=due_date,
    )
    return loan.installments.get(sequence_number=1)


@pytest.mark.django_db
class TestReminderWindows:
    @pytest.mark.parametrize(
        "days_ahead,expected_type",
        [
            (5, SMSMessage.MessageType.REPAYMENT_DUE_5_DAYS),
            (3, SMSMessage.MessageType.REPAYMENT_DUE_3_DAYS),
            (2, SMSMessage.MessageType.REPAYMENT_DUE_2_DAYS),
            (1, SMSMessage.MessageType.REPAYMENT_DUE_1_DAY),
        ],
    )
    def test_creates_the_expected_day_ahead_reminder(self, days_ahead, expected_type):
        due_date = date(2026, 9, 10) + timedelta(days=days_ahead)
        installment = _single_installment_loan(due_date)

        _run(now=_MORNING_RUN)

        assert SMSMessage.objects.filter(
            installment=installment, message_type=expected_type
        ).exists()

    def test_due_today_creates_both_morning_and_afternoon_reminders(self):
        installment = _single_installment_loan(date(2026, 9, 10))

        _run(now=_MORNING_RUN)
        _run(now=_AFTERNOON_RUN)

        assert SMSMessage.objects.filter(
            installment=installment, message_type=SMSMessage.MessageType.REPAYMENT_DUE_TODAY_MORNING
        ).exists()
        assert SMSMessage.objects.filter(
            installment=installment,
            message_type=SMSMessage.MessageType.REPAYMENT_DUE_TODAY_AFTERNOON,
        ).exists()

    def test_overdue_installment_gets_an_overdue_reminder(self):
        installment = _single_installment_loan(date(2026, 9, 1))

        _run(now=_MORNING_RUN)

        assert SMSMessage.objects.filter(
            installment=installment, message_type=SMSMessage.MessageType.REPAYMENT_OVERDUE
        ).exists()

    def test_running_twice_does_not_duplicate_reminders(self):
        installment = _single_installment_loan(date(2026, 9, 13))  # 3 days ahead

        _run(now=_MORNING_RUN)
        _run(now=_MORNING_RUN)

        assert (
            SMSMessage.objects.filter(
                installment=installment, message_type=SMSMessage.MessageType.REPAYMENT_DUE_3_DAYS
            ).count()
            == 1
        )

    def test_paid_installment_is_skipped(self):
        installment = _single_installment_loan(date(2026, 9, 13))
        finance = make_staff_user("FINANCE_OFFICER")
        repayment_services.record_payment(
            installment.loan,
            amount=Decimal("1000.00"),
            payment_date=timezone.localdate(),
            payment_method=Payment.Method.CASH,
            recorded_by=finance,
        )

        _run(now=_MORNING_RUN)

        assert not SMSMessage.objects.filter(installment=installment).exists()

    def test_reminder_text_uses_remaining_amount_after_a_partial_payment(self):
        installment = _single_installment_loan(date(2026, 9, 13))
        finance = make_staff_user("FINANCE_OFFICER")
        repayment_services.record_payment(
            installment.loan,
            amount=Decimal("400.00"),
            payment_date=timezone.localdate(),
            payment_method=Payment.Method.CASH,
            recorded_by=finance,
        )
        installment.refresh_from_db()
        assert installment.outstanding_amount == Decimal("600.00")

        _run(now=_MORNING_RUN)

        message = SMSMessage.objects.get(
            installment=installment, message_type=SMSMessage.MessageType.REPAYMENT_DUE_3_DAYS
        )
        assert "600.00" in message.message_body
        assert "1,000.00" not in message.message_body


@pytest.mark.django_db
class TestOverdueRecomputation:
    def test_overdue_installment_flips_installment_and_loan_status(self):
        installment = _single_installment_loan(date(2026, 9, 1))
        loan = installment.loan
        assert loan.status == Loan.Status.ACTIVE

        _run(now=_MORNING_RUN)

        installment.refresh_from_db()
        loan.refresh_from_db()
        assert installment.status == RepaymentInstallment.Status.OVERDUE
        assert loan.status == Loan.Status.OVERDUE

    def test_loan_returns_to_active_once_the_overdue_installment_is_paid(self):
        installment = _single_installment_loan(date(2026, 9, 1))
        loan = installment.loan
        _run(now=_MORNING_RUN)
        loan.refresh_from_db()
        assert loan.status == Loan.Status.OVERDUE

        finance = make_staff_user("FINANCE_OFFICER")
        repayment_services.record_payment(
            loan,
            amount=Decimal("1000.00"),
            payment_date=timezone.localdate(),
            payment_method=Payment.Method.CASH,
            recorded_by=finance,
        )

        loan.refresh_from_db()
        assert loan.status == Loan.Status.PAID_OFF


@pytest.mark.django_db(transaction=True)
class TestOverlappingRunProtection:
    def test_advisory_lock_blocks_a_second_session_holding_it(self):
        """Simulates two overlapping cron invocations as two real
        PostgreSQL sessions (a single session's advisory locks are
        re-entrant against itself, so this can't be proven on one
        connection) — the second session must observe the lock as held."""
        import psycopg
        from django.db import connection as db_connection

        from apps.messaging.management.commands.process_due_sms import _ADVISORY_LOCK_KEY

        db = db_connection.settings_dict
        dsn = (
            f"host={db['HOST']} port={db['PORT']} dbname={db['NAME']} "
            f"user={db['USER']} password={db['PASSWORD']}"
        )

        with db_connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(%s)", [_ADVISORY_LOCK_KEY])
            assert cursor.fetchone()[0] is True

            try:
                with psycopg.connect(dsn) as other_conn, other_conn.cursor() as other_cursor:
                    other_cursor.execute("SELECT pg_try_advisory_lock(%s)", [_ADVISORY_LOCK_KEY])
                    assert other_cursor.fetchone()[0] is False
            finally:
                cursor.execute("SELECT pg_advisory_unlock(%s)", [_ADVISORY_LOCK_KEY])

    def test_command_exits_cleanly_when_lock_is_already_held(self):
        import psycopg
        from django.db import connection as db_connection

        from apps.messaging.management.commands.process_due_sms import _ADVISORY_LOCK_KEY

        db = db_connection.settings_dict
        dsn = (
            f"host={db['HOST']} port={db['PORT']} dbname={db['NAME']} "
            f"user={db['USER']} password={db['PASSWORD']}"
        )
        with psycopg.connect(dsn) as other_conn, other_conn.cursor() as other_cursor:
            other_cursor.execute("SELECT pg_try_advisory_lock(%s)", [_ADVISORY_LOCK_KEY])
            assert other_cursor.fetchone()[0] is True

            output = _run(now=_MORNING_RUN)

            other_cursor.execute("SELECT pg_advisory_unlock(%s)", [_ADVISORY_LOCK_KEY])

        assert "already in progress" in output
