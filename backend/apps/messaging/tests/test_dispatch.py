from unittest.mock import patch

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.messaging import services
from apps.messaging.models import SMSMessage
from integrations.hubtel.base import SMSProviderResult
from tests.factories import make_user


def _pending_message(**overrides) -> SMSMessage:
    defaults = {
        "message_type": SMSMessage.MessageType.MANUAL_REMINDER,
        "recipient_phone_e164": "+233241234567",
        "message_body": "Test message",
        "status": SMSMessage.Status.PENDING,
        "customer": make_user(),
    }
    defaults.update(overrides)
    return SMSMessage.objects.create(**defaults)


@pytest.mark.django_db
class TestDispatchSms:
    def test_successful_send_marks_message_sent(self):
        message = _pending_message()
        result = SMSProviderResult(success=True, provider_message_id="pmid-1", response_code="0")

        with patch("apps.messaging.services.get_sms_provider") as mock_get_provider:
            mock_get_provider.return_value.send.return_value = result
            services.dispatch_sms(message.pk)

        message.refresh_from_db()
        assert message.status == SMSMessage.Status.SENT
        assert message.provider_message_id == "pmid-1"
        assert message.attempt_count == 1
        assert message.sent_at is not None

    def test_failed_send_schedules_a_retry(self):
        message = _pending_message()
        result = SMSProviderResult(success=False, error_summary="Server error")

        with patch("apps.messaging.services.get_sms_provider") as mock_get_provider:
            mock_get_provider.return_value.send.return_value = result
            services.dispatch_sms(message.pk)

        message.refresh_from_db()
        assert message.status == SMSMessage.Status.FAILED
        assert message.attempt_count == 1
        assert message.next_attempt_at is not None
        assert message.next_attempt_at > timezone.now()

    @override_settings(SMS_MAX_ATTEMPTS=2)
    def test_retry_limit_stops_scheduling_further_attempts(self):
        message = _pending_message(attempt_count=1, status=SMSMessage.Status.FAILED)
        result = SMSProviderResult(success=False, error_summary="Still failing")

        with patch("apps.messaging.services.get_sms_provider") as mock_get_provider:
            mock_get_provider.return_value.send.return_value = result
            services.dispatch_sms(message.pk)

        message.refresh_from_db()
        assert message.attempt_count == 2
        assert message.status == SMSMessage.Status.FAILED
        assert message.next_attempt_at is None  # attempt limit reached — no further retry

    def test_already_sent_message_is_not_resent(self):
        message = _pending_message(status=SMSMessage.Status.SENT)

        with patch("apps.messaging.services.get_sms_provider") as mock_get_provider:
            services.dispatch_sms(message.pk)
            mock_get_provider.return_value.send.assert_not_called()

    def test_dispatch_after_commit_fires_once_transaction_commits(
        self, django_capture_on_commit_callbacks
    ):
        result = SMSProviderResult(success=True, provider_message_id="pmid-2")
        with patch("apps.messaging.services.get_sms_provider") as mock_get_provider:
            mock_get_provider.return_value.send.return_value = result
            with django_capture_on_commit_callbacks(execute=True):
                message = _pending_message()
                services.dispatch_after_commit(message)

        message.refresh_from_db()
        assert message.status == SMSMessage.Status.SENT
