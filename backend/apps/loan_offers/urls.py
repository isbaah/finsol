from django.urls import path

from apps.loan_offers.views import (
    AdminOfferCreateView,
    AdminOfferDetailView,
    AdminOfferSendView,
    AmortizationPreviewView,
    CustomerOfferAcceptView,
    CustomerOfferDetailView,
    CustomerOfferRejectView,
    CustomerOfferRequestRevisionView,
)

urlpatterns = [
    path(
        "admin/offers/preview/",
        AmortizationPreviewView.as_view(),
        name="offer-amortization-preview",
    ),
    path(
        "admin/loan-requests/<uuid:pk>/offers/",
        AdminOfferCreateView.as_view(),
        name="admin-offer-create",
    ),
    path(
        "admin/offers/<uuid:pk>/",
        AdminOfferDetailView.as_view(),
        name="admin-offer-detail",
    ),
    path(
        "admin/offers/<uuid:pk>/send/",
        AdminOfferSendView.as_view(),
        name="admin-offer-send",
    ),
    path(
        "customer/offers/<uuid:pk>/",
        CustomerOfferDetailView.as_view(),
        name="customer-offer-detail",
    ),
    path(
        "customer/offers/<uuid:pk>/accept/",
        CustomerOfferAcceptView.as_view(),
        name="customer-offer-accept",
    ),
    path(
        "customer/offers/<uuid:pk>/reject/",
        CustomerOfferRejectView.as_view(),
        name="customer-offer-reject",
    ),
    path(
        "customer/offers/<uuid:pk>/request-revision/",
        CustomerOfferRequestRevisionView.as_view(),
        name="customer-offer-request-revision",
    ),
]
