from django.urls import path

from apps.customers.views import CustomerDetailView, CustomerListView, MyProfileView

urlpatterns = [
    path("profile/", MyProfileView.as_view(), name="my-profile"),
    path("customers/", CustomerListView.as_view(), name="customer-list"),
    path("customers/<uuid:pk>/", CustomerDetailView.as_view(), name="customer-detail"),
]
