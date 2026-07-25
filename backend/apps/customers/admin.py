from django.contrib import admin

from apps.customers.models import CustomerProfile


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    """Read-safe technical-support view. Full payout account numbers are
    shown here because Django admin access itself is restricted to trusted
    technical staff (is_staff=True) — this is not the business API, which
    always masks (see apps/customers/serializers.py).
    """

    list_display = [
        "user",
        "phone_number_e164",
        "preferred_disbursement_method",
        "profile_completed_at",
    ]
    list_filter = ["preferred_disbursement_method", "country"]
    search_fields = ["user__email", "phone_number_e164"]
    autocomplete_fields = ["user"]
    readonly_fields = ["id", "created_at", "updated_at"]
