from django.urls import path

from apps.dashboards.views import (
    AdminDashboardCollectionsChartView,
    AdminDashboardMetricsView,
    AdminDashboardOverdueSummaryView,
    AdminDashboardRecentTransactionsView,
    AdminDashboardUpcomingRepaymentsView,
)

urlpatterns = [
    path(
        "admin/dashboard/metrics/",
        AdminDashboardMetricsView.as_view(),
        name="admin-dashboard-metrics",
    ),
    path(
        "admin/dashboard/collections-chart/",
        AdminDashboardCollectionsChartView.as_view(),
        name="admin-dashboard-collections-chart",
    ),
    path(
        "admin/dashboard/upcoming-repayments/",
        AdminDashboardUpcomingRepaymentsView.as_view(),
        name="admin-dashboard-upcoming-repayments",
    ),
    path(
        "admin/dashboard/overdue-summary/",
        AdminDashboardOverdueSummaryView.as_view(),
        name="admin-dashboard-overdue-summary",
    ),
    path(
        "admin/dashboard/recent-transactions/",
        AdminDashboardRecentTransactionsView.as_view(),
        name="admin-dashboard-recent-transactions",
    ),
]
