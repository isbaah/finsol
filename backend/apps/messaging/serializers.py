from rest_framework import serializers

from apps.messaging.models import SMSMessage, SMSSettings


class SMSMessageSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    loan_number = serializers.CharField(source="loan.loan_number", read_only=True)

    class Meta:
        model = SMSMessage
        fields = [
            "id",
            "message_type",
            "recipient_phone_e164",
            "message_body",
            "status",
            "customer_name",
            "loan_number",
            "attempt_count",
            "next_attempt_at",
            "sent_at",
            "delivered_at",
            "failed_at",
            "last_error_summary",
            "created_at",
        ]
        read_only_fields = fields

    def get_customer_name(self, obj: SMSMessage) -> str:
        return obj.customer.get_full_name() if obj.customer else ""


class ManualReminderSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class SMSSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMSSettings
        fields = [
            "hubtel_enabled",
            "morning_reminder_time",
            "afternoon_reminder_time",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]
