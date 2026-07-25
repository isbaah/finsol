"""Stage 12 admin dashboard endpoints — all read-only, all staff-visible
(Section 10: every staff role, including AUDITOR, has read access to
operational records; nothing here mutates state). Money is serialized as
strings, matching every other endpoint in this API."""

from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

import apps.dashboards.services as dashboard_services
from common.permissions import STAFF_ROLES, has_any_role

_MONEY_METRICS = (
    "outstanding_portfolio_balance",
    "amount_due_this_month",
    "amount_collected_this_month",
    "overdue_amount",
)

CHART_MONTH_CHOICES = (6, 12)


class AdminDashboardMetricsView(APIView):
    """GET /api/v1/admin/dashboard/metrics/ — the Section 16 top metric
    cards plus work-queue counts, in one round trip."""

    permission_classes = [permissions.IsAuthenticated, has_any_role(*STAFF_ROLES)]

    def get(self, request):
        metrics = dashboard_services.dashboard_metrics(timezone.localdate())
        for field in _MONEY_METRICS:
            metrics[field] = str(metrics[field])
        return Response(metrics)


class AdminDashboardCollectionsChartView(APIView):
    """GET /api/v1/admin/dashboard/collections-chart/?months=6|12 —
    Section 16's expected-versus-collected monthly series."""

    permission_classes = [permissions.IsAuthenticated, has_any_role(*STAFF_ROLES)]

    def get(self, request):
        raw_months = request.query_params.get("months", "6")
        try:
            months = int(raw_months)
        except ValueError:
            months = 0
        if months not in CHART_MONTH_CHOICES:
            return Response(
                {"detail": "months must be 6 or 12."},
                status=400,
            )
        series = dashboard_services.collections_by_month(timezone.localdate(), months)
        return Response(
            [
                {
                    "month": row["month"].isoformat(),
                    "expected": str(row["expected"]),
                    "collected": str(row["collected"]),
                }
                for row in series
            ]
        )


class AdminDashboardUpcomingRepaymentsView(APIView):
    """GET /api/v1/admin/dashboard/upcoming-repayments/ — installments due
    in fewer than seven days, with each row's latest SMS status."""

    permission_classes = [permissions.IsAuthenticated, has_any_role(*STAFF_ROLES)]

    def get(self, request):
        rows = dashboard_services.upcoming_installments(timezone.localdate())
        return Response(
            [
                {
                    **row,
                    "installment_id": str(row["installment_id"]),
                    "loan_id": str(row["loan_id"]),
                    "total_due": str(row["total_due"]),
                    "outstanding_amount": str(row["outstanding_amount"]),
                    "due_date": row["due_date"].isoformat(),
                }
                for row in rows
            ]
        )


class AdminDashboardOverdueSummaryView(APIView):
    """GET /api/v1/admin/dashboard/overdue-summary/ — Section 16's overdue
    age buckets (1–7, 8–30, 31–60, 61+ days)."""

    permission_classes = [permissions.IsAuthenticated, has_any_role(*STAFF_ROLES)]

    def get(self, request):
        summary = dashboard_services.overdue_summary(timezone.localdate())
        return Response(
            {
                "buckets": [
                    {**bucket, "outstanding_total": str(bucket["outstanding_total"])}
                    for bucket in summary["buckets"]
                ],
                "total_outstanding": str(summary["total_outstanding"]),
            }
        )


class AdminDashboardRecentTransactionsView(APIView):
    """GET /api/v1/admin/dashboard/recent-transactions/ — the newest ledger
    entries, for the dashboard's recent-activity panel."""

    permission_classes = [permissions.IsAuthenticated, has_any_role(*STAFF_ROLES)]

    def get(self, request):
        entries = dashboard_services.recent_transactions()
        return Response(
            [
                {
                    "id": str(entry.pk),
                    "loan_id": str(entry.loan.pk),
                    "loan_number": entry.loan.loan_number,
                    "transaction_type": entry.transaction_type,
                    "amount": str(entry.amount),
                    "effective_date": entry.effective_date.isoformat(),
                    "created_at": entry.created_at.isoformat(),
                }
                for entry in entries
            ]
        )
