"""Read-only aggregate queries behind the Stage 12 admin dashboard.

No state is ever mutated here — every function is a plain query over data the
Stage 8–11 services already keep correct, so the dashboard can never disagree
with the ledger (master prompt Stage 12: "No business logic is duplicated in
frontend components" — the metric definitions live here, in one place).

Metric definitions (Section 16: "Each metric definition must be documented
and tested"):

- ``outstanding_portfolio_balance`` — SUM(``Loan.outstanding_balance``) over
  loans in a servicing status (DISBURSED/ACTIVE/OVERDUE). Pre-disbursement
  loans are excluded because no money has left the business yet (``create_loan``
  pre-sets ``outstanding_balance = total_repayable`` at PENDING_APPROVAL time),
  and PAID_OFF loans contribute zero by definition.
- ``amount_due_this_month`` — SUM(``RepaymentInstallment.total_due``) over
  non-WAIVED installments whose ``due_date`` falls inside the current calendar
  month, on loans that have actually been activated (servicing or PAID_OFF).
  This is "what the book expected to collect this month", so it deliberately
  does not shrink as payments arrive — compare it against
  ``amount_collected_this_month``.
- ``amount_collected_this_month`` — SUM(``Payment.amount``) over POSTED
  payments with ``payment_date`` in the current calendar month. Reversing a
  payment removes it from this figure (status flips to REVERSED).
- ``overdue_amount`` — SUM(``RepaymentInstallment.outstanding_amount``) over
  installments currently in OVERDUE status.
- ``active_loans`` — COUNT of loans in a servicing status
  (DISBURSED/ACTIVE/OVERDUE). DISBURSED is transient (record_disbursement
  moves DISBURSED -> ACTIVE in the same transaction) but is included
  defensively so the count could never miss a loan mid-flight.
"""

from datetime import date, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth

from apps.loan_requests.models import LoanRequest
from apps.loans.models import Loan, RepaymentInstallment
from apps.messaging.models import SMSMessage
from apps.repayments.models import LoanTransaction, Payment, PaymentClaim

ZERO = Decimal("0.00")

SERVICING_STATUSES = (Loan.Status.DISBURSED, Loan.Status.ACTIVE, Loan.Status.OVERDUE)
ACTIVATED_STATUSES = SERVICING_STATUSES + (Loan.Status.PAID_OFF,)

# Unpaid, chargeable installment statuses — the ones an upcoming-repayments
# operator actually needs to act on. PAID and WAIVED are excluded.
OPEN_INSTALLMENT_STATUSES = (
    RepaymentInstallment.Status.UPCOMING,
    RepaymentInstallment.Status.DUE,
    RepaymentInstallment.Status.PARTIALLY_PAID,
    RepaymentInstallment.Status.OVERDUE,
)

# Section 16's overdue age buckets: 1–7, 8–30, 31–60, 61+ days.
OVERDUE_BUCKETS = (
    ("1-7 days", 1, 7),
    ("8-30 days", 8, 30),
    ("31-60 days", 31, 60),
    ("61+ days", 61, None),
)


def _month_start(day: date) -> date:
    return day.replace(day=1)


def dashboard_metrics(today: date) -> dict:
    """The five Section 16 top metric cards plus the three work-queue counts
    the Stage 9 dashboard already showed — one call, so the dashboard makes
    one request instead of six ("Optimise dashboard queries")."""
    month_start = _month_start(today)
    next_month_start = month_start + relativedelta(months=1)

    outstanding = Loan.objects.filter(status__in=SERVICING_STATUSES).aggregate(
        total=Sum("outstanding_balance")
    )["total"]
    due_this_month = (
        RepaymentInstallment.objects.filter(
            loan__status__in=ACTIVATED_STATUSES,
            due_date__gte=month_start,
            due_date__lt=next_month_start,
        )
        .exclude(status=RepaymentInstallment.Status.WAIVED)
        .aggregate(total=Sum("total_due"))["total"]
    )
    collected_this_month = Payment.objects.filter(
        status=Payment.Status.POSTED,
        payment_date__gte=month_start,
        payment_date__lt=next_month_start,
    ).aggregate(total=Sum("amount"))["total"]
    overdue_amount = RepaymentInstallment.objects.filter(
        status=RepaymentInstallment.Status.OVERDUE
    ).aggregate(total=Sum("outstanding_amount"))["total"]

    return {
        "outstanding_portfolio_balance": outstanding or ZERO,
        "amount_due_this_month": due_this_month or ZERO,
        "amount_collected_this_month": collected_this_month or ZERO,
        "overdue_amount": overdue_amount or ZERO,
        "active_loans": Loan.objects.filter(status__in=SERVICING_STATUSES).count(),
        "new_request_count": LoanRequest.objects.filter(
            status=LoanRequest.Status.SUBMITTED
        ).count(),
        "pending_approval_count": Loan.objects.filter(status=Loan.Status.PENDING_APPROVAL).count(),
        "awaiting_disbursement_count": Loan.objects.filter(
            status=Loan.Status.APPROVED_FOR_DISBURSEMENT
        ).count(),
        "pending_payment_claim_count": PaymentClaim.objects.filter(
            status=PaymentClaim.Status.PENDING
        ).count(),
    }


def collections_by_month(today: date, months: int) -> list[dict]:
    """Section 16's expected-versus-collected chart series: one row per
    calendar month for the last ``months`` months ending with the current
    month. ``expected`` groups installment ``total_due`` by due month (same
    definition as ``amount_due_this_month``); ``collected`` groups POSTED
    payment amounts by ``payment_date`` month. Months with no activity are
    filled in as zero so the chart never has gaps."""
    window_start = _month_start(today) - relativedelta(months=months - 1)
    window_end = _month_start(today) + relativedelta(months=1)

    expected_rows = (
        RepaymentInstallment.objects.filter(
            loan__status__in=ACTIVATED_STATUSES,
            due_date__gte=window_start,
            due_date__lt=window_end,
        )
        .exclude(status=RepaymentInstallment.Status.WAIVED)
        .annotate(month=TruncMonth("due_date"))
        .values("month")
        .annotate(total=Sum("total_due"))
    )
    collected_rows = (
        Payment.objects.filter(
            status=Payment.Status.POSTED,
            payment_date__gte=window_start,
            payment_date__lt=window_end,
        )
        .annotate(month=TruncMonth("payment_date"))
        .values("month")
        .annotate(total=Sum("amount"))
    )
    expected_by_month = {row["month"]: row["total"] for row in expected_rows}
    collected_by_month = {row["month"]: row["total"] for row in collected_rows}

    series = []
    for offset in range(months):
        month = window_start + relativedelta(months=offset)
        series.append(
            {
                "month": month,
                "expected": expected_by_month.get(month, ZERO),
                "collected": collected_by_month.get(month, ZERO),
            }
        )
    return series


def upcoming_installments(today: date, *, horizon_days: int = 7, limit: int = 100) -> list[dict]:
    """Section 16's upcoming-repayments table: unpaid installments due in
    fewer than ``horizon_days`` days (today inclusive), on loans still being
    serviced, with the latest SMS recorded against each installment (one
    batched query, not one per row)."""
    installments = list(
        RepaymentInstallment.objects.filter(
            loan__status__in=SERVICING_STATUSES,
            status__in=OPEN_INSTALLMENT_STATUSES,
            due_date__gte=today,
            due_date__lt=today + timedelta(days=horizon_days),
        )
        .select_related("loan", "loan__customer")
        .order_by("due_date", "loan__loan_number")[:limit]
    )

    last_sms_by_installment: dict = {}
    messages = SMSMessage.objects.filter(
        installment__in=[installment.pk for installment in installments]
    ).order_by("installment_id", "-created_at")
    for message in messages:
        last_sms_by_installment.setdefault(message.installment_id, message)

    rows = []
    for installment in installments:
        last_sms = last_sms_by_installment.get(installment.pk)
        rows.append(
            {
                "installment_id": installment.pk,
                "loan_id": installment.loan.pk,
                "loan_number": installment.loan.loan_number,
                "customer_name": installment.loan.customer.get_full_name(),
                "sequence_number": installment.sequence_number,
                "total_due": installment.total_due,
                "outstanding_amount": installment.outstanding_amount,
                "due_date": installment.due_date,
                "days_remaining": (installment.due_date - today).days,
                "status": installment.status,
                "last_sms_status": last_sms.status if last_sms else None,
                "last_sms_type": last_sms.message_type if last_sms else None,
            }
        )
    return rows


def overdue_summary(today: date) -> dict:
    """Section 16's overdue table, aggregated into the four age buckets in a
    single query. An installment's age is ``today - due_date`` in days; only
    OVERDUE-status installments count (so a paid-late-but-settled installment
    never reappears here)."""

    def _bucket_range(min_days: int, max_days: int | None) -> Q:
        condition = Q(due_date__lte=today - timedelta(days=min_days))
        if max_days is not None:
            condition &= Q(due_date__gte=today - timedelta(days=max_days))
        return condition

    aggregates = {}
    for index, (_, min_days, max_days) in enumerate(OVERDUE_BUCKETS):
        bucket_filter = _bucket_range(min_days, max_days)
        aggregates[f"bucket_{index}_outstanding"] = Sum("outstanding_amount", filter=bucket_filter)
        aggregates[f"bucket_{index}_installments"] = Count("pk", filter=bucket_filter)
        aggregates[f"bucket_{index}_loans"] = Count("loan", distinct=True, filter=bucket_filter)
    aggregates["total_outstanding"] = Sum("outstanding_amount")

    result = RepaymentInstallment.objects.filter(
        status=RepaymentInstallment.Status.OVERDUE
    ).aggregate(**aggregates)

    buckets = []
    for index, (label, min_days, max_days) in enumerate(OVERDUE_BUCKETS):
        buckets.append(
            {
                "label": label,
                "min_days": min_days,
                "max_days": max_days,
                "installment_count": result[f"bucket_{index}_installments"] or 0,
                "loan_count": result[f"bucket_{index}_loans"] or 0,
                "outstanding_total": result[f"bucket_{index}_outstanding"] or ZERO,
            }
        )
    return {"buckets": buckets, "total_outstanding": result["total_outstanding"] or ZERO}


def recent_transactions(*, limit: int = 8) -> list[LoanTransaction]:
    """The dashboard's recent-ledger-activity panel — newest first, straight
    from the append-only LoanTransaction ledger."""
    return list(LoanTransaction.objects.select_related("loan").order_by("-created_at")[:limit])
