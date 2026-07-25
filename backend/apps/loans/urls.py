from django.urls import path

from apps.loans.views import (
    AdminLoanApproveView,
    AdminLoanDetailView,
    AdminLoanDisburseView,
    AdminLoanListView,
    CustomerLoanDetailView,
    CustomerLoanListView,
    LoanPayoutDetailsRevealView,
)

urlpatterns = [
    path("admin/loans/", AdminLoanListView.as_view(), name="admin-loan-list"),
    path("admin/loans/<uuid:pk>/", AdminLoanDetailView.as_view(), name="admin-loan-detail"),
    path(
        "admin/loans/<uuid:pk>/approve/",
        AdminLoanApproveView.as_view(),
        name="admin-loan-approve",
    ),
    path(
        "admin/loans/<uuid:pk>/disburse/",
        AdminLoanDisburseView.as_view(),
        name="admin-loan-disburse",
    ),
    path(
        "admin/loans/<uuid:pk>/payout-details/",
        LoanPayoutDetailsRevealView.as_view(),
        name="admin-loan-payout-details",
    ),
    path("customer/loans/", CustomerLoanListView.as_view(), name="customer-loan-list"),
    path(
        "customer/loans/<uuid:pk>/", CustomerLoanDetailView.as_view(), name="customer-loan-detail"
    ),
]
