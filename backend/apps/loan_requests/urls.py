from django.urls import path

from apps.loan_requests.views import (
    AdminLoanRequestDeclineView,
    AdminLoanRequestDetailView,
    AdminLoanRequestListView,
    AdminLoanRequestStartReviewView,
    LoanRequestCancelView,
    LoanRequestDetailView,
    LoanRequestListCreateView,
)

urlpatterns = [
    path(
        "customer/loan-requests/",
        LoanRequestListCreateView.as_view(),
        name="customer-loan-request-list",
    ),
    path(
        "customer/loan-requests/<uuid:pk>/",
        LoanRequestDetailView.as_view(),
        name="customer-loan-request-detail",
    ),
    path(
        "customer/loan-requests/<uuid:pk>/cancel/",
        LoanRequestCancelView.as_view(),
        name="customer-loan-request-cancel",
    ),
    path(
        "admin/loan-requests/",
        AdminLoanRequestListView.as_view(),
        name="admin-loan-request-list",
    ),
    path(
        "admin/loan-requests/<uuid:pk>/",
        AdminLoanRequestDetailView.as_view(),
        name="admin-loan-request-detail",
    ),
    path(
        "admin/loan-requests/<uuid:pk>/start-review/",
        AdminLoanRequestStartReviewView.as_view(),
        name="admin-loan-request-start-review",
    ),
    path(
        "admin/loan-requests/<uuid:pk>/decline/",
        AdminLoanRequestDeclineView.as_view(),
        name="admin-loan-request-decline",
    ),
]
