from django.urls import path

from apps.agreements.views import (
    AdminAgreementRetryEmailView,
    AgreementDetailView,
    AgreementDownloadView,
)

urlpatterns = [
    path("agreements/<uuid:pk>/", AgreementDetailView.as_view(), name="agreement-detail"),
    path(
        "agreements/<uuid:pk>/download/",
        AgreementDownloadView.as_view(),
        name="agreement-download",
    ),
    path(
        "admin/agreements/<uuid:pk>/retry-email/",
        AdminAgreementRetryEmailView.as_view(),
        name="admin-agreement-retry-email",
    ),
]
