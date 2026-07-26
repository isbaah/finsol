import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.audit.models import AuditEvent
from apps.messaging.models import SMSMessage, SMSSettings
from integrations.hubtel.base import SMSProviderResult
from tests.factories import make_active_loan, make_staff_user, make_user


def post_json(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


def list_url() -> str:
    return "/api/v1/admin/sms-messages/"


def summary_url() -> str:
    return "/api/v1/admin/sms-messages/summary/"


def retry_url(message_id) -> str:
    return f"/api/v1/admin/sms-messages/{message_id}/retry/"


def manual_reminder_url(installment_id) -> str:
    return f"/api/v1/admin/installments/{installment_id}/manual-reminder/"


def sms_settings_url() -> str:
    return "/api/v1/admin/sms-settings/"


def _installment():
    loan = make_active_loan(
        principal=Decimal("1000.00"),
        total_interest=Decimal("0.00"),
        installment_count=1,
        first_due_date=date(2027, 1, 1),
    )
    return loan.installments.get(sequence_number=1)


@pytest.mark.django_db
class TestAdminSmsList:
    def test_unauthenticated_is_rejected(self, client):
        assert client.get(list_url()).status_code in (401, 403)

    def test_staff_can_list(self, client):
        # make_active_loan() itself fires OFFER_ACCEPTED_CUSTOMER,
        # LOAN_APPROVED, and LOAN_DISBURSED_CUSTOMER SMS along the way —
        # count against the baseline rather than assuming zero.
        installment = _installment()
        baseline = SMSMessage.objects.count()
        client.force_login(make_staff_user("SUPER_ADMIN"))
        post_json(client, manual_reminder_url(installment.pk), {"reason": "Test"})

        response = client.get(list_url())

        assert response.status_code == 200
        body = response.json()
        results = body["results"] if isinstance(body, dict) and "results" in body else body
        assert len(results) == baseline + 1

    def test_summary_returns_status_counts(self, client):
        installment = _installment()
        baseline = SMSMessage.objects.count()
        client.force_login(make_staff_user("SUPER_ADMIN"))
        post_json(client, manual_reminder_url(installment.pk), {"reason": "Test"})

        response = client.get(summary_url())

        assert response.status_code == 200
        body = response.json()
        assert set(body.keys()) == {choice for choice, _ in SMSMessage.Status.choices}
        assert sum(body.values()) == baseline + 1


@pytest.mark.django_db
class TestManualReminder:
    def test_customer_cannot_send_a_manual_reminder(self, client):
        installment = _installment()
        client.force_login(make_user())

        response = post_json(client, manual_reminder_url(installment.pk), {"reason": "Call"})

        assert response.status_code == 403

    def test_loan_officer_can_send_a_manual_reminder_and_it_is_audited(self, client):
        installment = _installment()
        client.force_login(make_staff_user("LOAN_OFFICER"))

        response = post_json(
            client, manual_reminder_url(installment.pk), {"reason": "Customer requested a nudge"}
        )

        assert response.status_code == 201
        assert response.json()["message_type"] == SMSMessage.MessageType.MANUAL_REMINDER
        event = AuditEvent.objects.get(action="sms_message.manual_reminder")
        assert event.reason == "Customer requested a nudge"

    def test_manual_reminder_may_be_sent_more_than_once(self, client):
        installment = _installment()
        client.force_login(make_staff_user("LOAN_OFFICER"))

        first = post_json(client, manual_reminder_url(installment.pk), {"reason": "First nudge"})
        second = post_json(client, manual_reminder_url(installment.pk), {"reason": "Second nudge"})

        assert first.status_code == 201
        assert second.status_code == 201
        assert (
            SMSMessage.objects.filter(
                installment=installment, message_type=SMSMessage.MessageType.MANUAL_REMINDER
            ).count()
            == 2
        )


@pytest.mark.django_db
class TestRetry:
    def test_finance_officer_cannot_retry(self, client):
        installment = _installment()
        client.force_login(make_staff_user("SUPER_ADMIN"))
        message_id = post_json(client, manual_reminder_url(installment.pk), {"reason": "x"}).json()[
            "id"
        ]

        client.force_login(make_staff_user("FINANCE_OFFICER"))
        response = post_json(client, retry_url(message_id), {})

        assert response.status_code == 403

    def test_loan_officer_can_retry_a_failed_message_and_it_is_audited(self, client):
        installment = _installment()
        client.force_login(make_staff_user("LOAN_OFFICER"))
        message_id = post_json(client, manual_reminder_url(installment.pk), {"reason": "x"}).json()[
            "id"
        ]
        message = SMSMessage.objects.get(pk=message_id)
        message.status = SMSMessage.Status.FAILED
        message.save(update_fields=["status"])

        result = SMSProviderResult(success=True, provider_message_id="retry-pmid")
        with patch("apps.messaging.services.get_sms_provider") as mock_get_provider:
            mock_get_provider.return_value.send.return_value = result
            response = post_json(client, retry_url(message_id), {})

        assert response.status_code == 200
        assert response.json()["status"] == SMSMessage.Status.SENT
        assert AuditEvent.objects.filter(action="sms_message.manual_retry").exists()


@pytest.mark.django_db
class TestAdminSmsSettings:
    def test_unauthenticated_is_rejected(self, client):
        assert client.get(sms_settings_url()).status_code in (401, 403)

    def test_defaults_are_enabled_with_standard_reminder_times(self, client):
        client.force_login(make_staff_user("AUDITOR"))

        response = client.get(sms_settings_url())

        assert response.status_code == 200
        body = response.json()
        assert body["hubtel_enabled"] is True
        assert body["morning_reminder_time"] == "08:00:00"
        assert body["afternoon_reminder_time"] == "16:00:00"

    def test_non_super_admin_cannot_change_settings(self, client):
        client.force_login(make_staff_user("LOAN_OFFICER"))

        response = client.put(
            sms_settings_url(),
            data=json.dumps({"hubtel_enabled": False, "morning_reminder_time": "09:00"}),
            content_type="application/json",
        )

        assert response.status_code == 403
        assert SMSSettings.get_solo().hubtel_enabled is True

    def test_super_admin_can_pause_sending_and_it_is_audited(self, client):
        client.force_login(make_staff_user("SUPER_ADMIN"))

        response = client.put(
            sms_settings_url(),
            data=json.dumps(
                {
                    "hubtel_enabled": False,
                    "morning_reminder_time": "09:30",
                    "afternoon_reminder_time": "17:15",
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 200
        settings_row = SMSSettings.get_solo()
        assert settings_row.hubtel_enabled is False
        assert str(settings_row.morning_reminder_time) == "09:30:00"
        assert str(settings_row.afternoon_reminder_time) == "17:15:00"
        assert AuditEvent.objects.filter(action="sms_settings.update").exists()
