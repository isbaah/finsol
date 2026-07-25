"""Idempotent scheduled-reminder + retry sweep (master prompt Section 17 /
Section 24 Stage 11). No Redis or Celery — this command is meant to be
invoked by the platform's own cron/scheduler every 15 minutes or hourly; it
decides for itself whether a reminder slot is actually due on each run.

    python manage.py process_due_sms
    python manage.py process_due_sms --dry-run
    python manage.py process_due_sms --now "2026-09-15T08:00:00+00:00"
    python manage.py process_due_sms --limit 50

Overlapping-run protection uses a session-scoped PostgreSQL advisory lock
(`pg_try_advisory_lock`) rather than a transaction-scoped one, since the
whole point is to NOT hold one long-lived transaction across the batch
dispatch/rate-limit pass below.
"""

from __future__ import annotations

import json
import time
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection as db_connection
from django.utils import timezone
from django.utils.dateparse import parse_datetime

import apps.messaging.services as messaging_services
from apps.loans import services as loan_services
from apps.loans.models import Loan, RepaymentInstallment
from apps.messaging.models import SMSMessage

_ADVISORY_LOCK_KEY = 741852963

# (message_type, reminder_slot, days_until_due predicate) — evaluated once
# per outstanding installment per run.
_DAY_AHEAD_TYPES = {
    5: (SMSMessage.MessageType.REPAYMENT_DUE_5_DAYS, "5_DAYS"),
    3: (SMSMessage.MessageType.REPAYMENT_DUE_3_DAYS, "3_DAYS"),
    2: (SMSMessage.MessageType.REPAYMENT_DUE_2_DAYS, "2_DAYS"),
    1: (SMSMessage.MessageType.REPAYMENT_DUE_1_DAY, "1_DAY"),
}


def _try_acquire_lock() -> bool:
    with db_connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s)", [_ADVISORY_LOCK_KEY])
        return bool(cursor.fetchone()[0])


def _release_lock() -> None:
    with db_connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_unlock(%s)", [_ADVISORY_LOCK_KEY])


def _parse_hhmm(value: str) -> tuple[int, int]:
    hour, _, minute = value.partition(":")
    return int(hour), int(minute or 0)


class Command(BaseCommand):
    help = "Create/dispatch due repayment-reminder SMS and retry eligible failed sends. Idempotent."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Create/update records but never call the SMS provider.",
        )
        parser.add_argument(
            "--now", type=str, default=None, help="ISO-8601 timestamp to use as 'now' (testing)."
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=200,
            help="Maximum number of messages to dispatch this run.",
        )

    def handle(self, *args, **options):
        if not _try_acquire_lock():
            self.stdout.write("process_due_sms: another run is already in progress; exiting.")
            return

        try:
            summary = self._run(options)
        except Exception as exc:  # pragma: no cover - genuine command-level failure only
            raise CommandError(f"process_due_sms failed: {exc}") from exc
        finally:
            _release_lock()

        self.stdout.write(json.dumps(summary))

    def _now(self, options) -> datetime:
        if options["now"]:
            parsed = parse_datetime(options["now"])
            if parsed is None:
                raise CommandError(
                    f"--now value {options['now']!r} is not a valid ISO-8601 timestamp."
                )
            if timezone.is_naive(parsed):
                parsed = timezone.make_aware(parsed, timezone.utc)
            return parsed
        return timezone.now()

    def _run(self, options) -> dict:
        dry_run = options["dry_run"]
        limit = options["limit"]
        now = self._now(options)
        local_now = timezone.localtime(now)
        today = local_now.date()
        current_time = local_now.time()
        morning_time = _parse_hhmm(settings.SMS_DUE_MORNING_TIME)
        afternoon_time = _parse_hhmm(settings.SMS_DUE_AFTERNOON_TIME)
        reached_morning = (current_time.hour, current_time.minute) >= morning_time
        reached_afternoon = (current_time.hour, current_time.minute) >= afternoon_time

        status_changes = self._recompute_due_statuses(today)
        reminders_created = self._create_due_reminders(
            today=today, reached_morning=reached_morning, reached_afternoon=reached_afternoon
        )

        dispatched = failed = 0
        if not dry_run:
            dispatched, failed = self._dispatch_batch(limit=limit)

        return {
            "ran_at": now.isoformat(),
            "business_date": today.isoformat(),
            "dry_run": dry_run,
            "installment_status_changes": status_changes,
            "reminders_created": reminders_created,
            "messages_dispatched": dispatched,
            "messages_failed": failed,
        }

    def _recompute_due_statuses(self, today) -> int:
        """Section 4's forward-only due-date transitions
        (UPCOMING->DUE, DUE/PARTIALLY_PAID->OVERDUE) plus the matching
        Loan-level ACTIVE<->OVERDUE recomputation — the "piggyback on
        process_due_sms" resolution recorded in docs/STATUS_TRANSITIONS.md."""
        changed = 0
        installments = RepaymentInstallment.objects.select_related("loan").exclude(
            status__in=[RepaymentInstallment.Status.PAID, RepaymentInstallment.Status.WAIVED]
        )
        touched_loan_ids: set = set()
        for installment in installments:
            new_status = None
            if (
                installment.due_date < today
                and installment.status != RepaymentInstallment.Status.OVERDUE
            ):
                new_status = RepaymentInstallment.Status.OVERDUE
            elif (
                installment.due_date == today
                and installment.status == RepaymentInstallment.Status.UPCOMING
            ):
                new_status = RepaymentInstallment.Status.DUE
            if new_status:
                installment.status = new_status
                installment.save(update_fields=["status", "updated_at"])
                changed += 1
                touched_loan_ids.add(installment.loan_id)

        for loan in Loan.objects.filter(pk__in=touched_loan_ids):
            has_overdue = loan.installments.filter(
                status=RepaymentInstallment.Status.OVERDUE
            ).exists()
            if loan.status == Loan.Status.ACTIVE and has_overdue:
                loan_services.mark_overdue(loan)
            elif loan.status == Loan.Status.OVERDUE and not has_overdue:
                loan_services.mark_current(loan)
        return changed

    def _create_due_reminders(self, *, today, reached_morning, reached_afternoon) -> int:
        created = 0
        installments = (
            RepaymentInstallment.objects.select_related("loan", "loan__customer")
            .exclude(
                status__in=[RepaymentInstallment.Status.PAID, RepaymentInstallment.Status.WAIVED]
            )
            .filter(loan__status__in=[Loan.Status.ACTIVE, Loan.Status.OVERDUE])
        )

        for installment in installments:
            days_until = (installment.due_date - today).days
            candidates = []
            if reached_morning:
                if days_until in _DAY_AHEAD_TYPES:
                    candidates.append(_DAY_AHEAD_TYPES[days_until])
                elif days_until == 0:
                    candidates.append(
                        (SMSMessage.MessageType.REPAYMENT_DUE_TODAY_MORNING, "MORNING")
                    )
                elif days_until < 0:
                    candidates.append((SMSMessage.MessageType.REPAYMENT_OVERDUE, "OVERDUE"))
            if reached_afternoon and days_until == 0:
                candidates.append(
                    (SMSMessage.MessageType.REPAYMENT_DUE_TODAY_AFTERNOON, "AFTERNOON")
                )

            for message_type, slot in candidates:
                if self._create_reminder_if_missing(
                    installment=installment,
                    message_type=message_type,
                    slot=slot,
                    business_date=today,
                ):
                    created += 1
        return created

    def _create_reminder_if_missing(
        self, *, installment, message_type, slot, business_date
    ) -> bool:
        profile = getattr(installment.loan.customer, "customer_profile", None)
        phone = profile.phone_number_e164 if profile else ""
        _, created = SMSMessage.objects.get_or_create(
            installment=installment,
            message_type=message_type,
            reminder_business_date=business_date,
            reminder_slot=slot,
            defaults={
                "customer": installment.loan.customer,
                "loan": installment.loan,
                "recipient_phone_e164": phone,
                "message_body": messaging_services.render_reminder_message(
                    message_type=message_type, installment=installment
                ),
                "status": SMSMessage.Status.PENDING,
            },
        )
        return created

    def _dispatch_batch(self, *, limit: int) -> tuple[int, int]:
        now = timezone.now()
        candidates = list(
            SMSMessage.objects.filter(status=SMSMessage.Status.PENDING).order_by("created_at")[
                :limit
            ]
        )
        remaining = limit - len(candidates)
        if remaining > 0:
            candidates += list(
                SMSMessage.objects.filter(
                    status=SMSMessage.Status.FAILED,
                    next_attempt_at__isnull=False,
                    next_attempt_at__lte=now,
                ).order_by("next_attempt_at")[:remaining]
            )

        rate_limit = settings.HUBTEL_MAX_REQUESTS_PER_MINUTE or 0
        sent = failed = 0
        for index, message in enumerate(candidates, start=1):
            result = messaging_services.dispatch_sms(message.pk)
            if result and result.status == SMSMessage.Status.SENT:
                sent += 1
            else:
                failed += 1
            if rate_limit and index % rate_limit == 0 and index < len(candidates):
                time.sleep(60)  # pragma: no cover - only reached above the configured rate limit
        return sent, failed
