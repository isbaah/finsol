from django.urls import path

from apps.repayments.views import (
    AdminLoanRepaymentListCreateView,
    AdminPaymentClaimListView,
    AdminPaymentClaimResolveView,
    AdminPaymentReverseView,
    AdminRepaymentAccountView,
    CustomerInstallmentClaimView,
    RepaymentAccountView,
)

urlpatterns = [
    path(
        "admin/loans/<uuid:pk>/repayments/",
        AdminLoanRepaymentListCreateView.as_view(),
        name="admin-loan-repayments",
    ),
    path(
        "admin/repayments/<uuid:pk>/reverse/",
        AdminPaymentReverseView.as_view(),
        name="admin-payment-reverse",
    ),
    path(
        "admin/payment-claims/",
        AdminPaymentClaimListView.as_view(),
        name="admin-payment-claim-list",
    ),
    path(
        "admin/payment-claims/<uuid:pk>/resolve/",
        AdminPaymentClaimResolveView.as_view(),
        name="admin-payment-claim-resolve",
    ),
    path(
        "customer/installments/<uuid:pk>/claim-payment/",
        CustomerInstallmentClaimView.as_view(),
        name="customer-installment-claim-payment",
    ),
    path("repayment-account/", RepaymentAccountView.as_view(), name="repayment-account"),
    path(
        "admin/repayment-account/",
        AdminRepaymentAccountView.as_view(),
        name="admin-repayment-account",
    ),
]
