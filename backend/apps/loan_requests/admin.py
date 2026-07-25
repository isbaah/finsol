from django.contrib import admin

from apps.loan_requests.models import LoanRequest


@admin.register(LoanRequest)
class LoanRequestAdmin(admin.ModelAdmin):
    """Read-safe technical-support view — status is never editable here;
    all transitions go through apps/loan_requests/services.py.
    """

    list_display = ["request_number", "customer", "requested_amount", "status", "submitted_at"]
    list_filter = ["status", "requested_term_unit"]
    search_fields = ["request_number", "customer__email"]
    autocomplete_fields = ["customer", "assigned_to"]
    readonly_fields = [f.name for f in LoanRequest._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
