from django.contrib import admin

from apps.messaging.models import SMSMessage


@admin.register(SMSMessage)
class SMSMessageAdmin(admin.ModelAdmin):
    list_display = ["message_type", "recipient_phone_e164", "status", "attempt_count", "created_at"]
    list_filter = ["status", "message_type"]
    search_fields = ["recipient_phone_e164", "provider_message_id"]
    autocomplete_fields = ["customer", "loan"]
    raw_id_fields = ["installment"]
    readonly_fields = [f.name for f in SMSMessage._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
