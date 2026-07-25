import django_filters

from apps.messaging.models import SMSMessage


class SMSMessageFilter(django_filters.FilterSet):
    status = django_filters.MultipleChoiceFilter(choices=SMSMessage.Status.choices)
    message_type = django_filters.MultipleChoiceFilter(choices=SMSMessage.MessageType.choices)
    loan = django_filters.UUIDFilter(field_name="loan_id")

    class Meta:
        model = SMSMessage
        fields = ["status", "message_type", "loan"]
