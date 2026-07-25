from django.contrib import admin

from apps.agreements.models import Agreement


@admin.register(Agreement)
class AgreementAdmin(admin.ModelAdmin):
    list_display = ["offer", "customer", "typed_legal_name", "accepted_at", "email_delivery_status"]
    search_fields = ["offer__loan_request__request_number", "customer__email", "typed_legal_name"]
    autocomplete_fields = ["offer", "customer"]
    readonly_fields = [f.name for f in Agreement._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
