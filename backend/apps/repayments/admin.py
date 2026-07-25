from django.contrib import admin

from apps.repayments.models import LoanTransaction, Payment, PaymentAllocation


class PaymentAllocationInline(admin.TabularInline):
    model = PaymentAllocation
    extra = 0
    can_delete = False
    readonly_fields = [f.name for f in PaymentAllocation._meta.fields]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["receipt_number", "loan", "amount", "status", "recorded_at"]
    list_filter = ["status", "payment_method"]
    search_fields = ["receipt_number", "loan__loan_number", "external_transaction_reference"]
    autocomplete_fields = ["loan", "recorded_by", "reversal_of"]
    readonly_fields = [f.name for f in Payment._meta.fields]
    inlines = [PaymentAllocationInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LoanTransaction)
class LoanTransactionAdmin(admin.ModelAdmin):
    """Read-only — the model itself refuses updates/deletes (see models.py)."""

    list_display = ["loan", "transaction_type", "amount", "balance_after", "created_at"]
    list_filter = ["transaction_type"]
    search_fields = ["loan__loan_number"]
    autocomplete_fields = ["loan", "recorded_by"]
    readonly_fields = [f.name for f in LoanTransaction._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
