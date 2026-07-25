from django.contrib import admin

from apps.loans.models import Disbursement, Loan, RepaymentInstallment


class RepaymentInstallmentInline(admin.TabularInline):
    model = RepaymentInstallment
    extra = 0
    can_delete = False
    readonly_fields = [f.name for f in RepaymentInstallment._meta.fields]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ["loan_number", "customer", "status", "principal", "outstanding_balance"]
    list_filter = ["status"]
    search_fields = ["loan_number", "customer__email"]
    autocomplete_fields = ["customer", "loan_request", "accepted_offer", "agreement", "approved_by"]
    readonly_fields = [f.name for f in Loan._meta.fields]
    inlines = [RepaymentInstallmentInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Disbursement)
class DisbursementAdmin(admin.ModelAdmin):
    list_display = ["loan", "amount", "method", "recorded_by", "recorded_at"]
    search_fields = ["loan__loan_number", "external_transaction_reference"]
    autocomplete_fields = ["loan", "recorded_by"]
    readonly_fields = [f.name for f in Disbursement._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
