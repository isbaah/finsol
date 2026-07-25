from django.contrib import admin

from apps.loan_offers.models import LoanOffer, OfferInstallment


class OfferInstallmentInline(admin.TabularInline):
    model = OfferInstallment
    extra = 0
    can_delete = False
    readonly_fields = [f.name for f in OfferInstallment._meta.fields]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(LoanOffer)
class LoanOfferAdmin(admin.ModelAdmin):
    list_display = ["__str__", "loan_request", "status", "principal", "total_repayable", "sent_at"]
    list_filter = ["status", "term_unit"]
    search_fields = ["loan_request__request_number"]
    autocomplete_fields = ["loan_request", "created_by", "sent_by"]
    readonly_fields = [f.name for f in LoanOffer._meta.fields]
    inlines = [OfferInstallmentInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
