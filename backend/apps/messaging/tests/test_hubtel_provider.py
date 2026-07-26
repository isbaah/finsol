"""Hubtel adapter tests (master prompt Section 22: "Hubtel success, timeout,
4xx, 5xx, and malformed-response tests using mocked HTTP") — no real network
call is ever made; `requests.get` itself is mocked."""

from unittest.mock import Mock, patch

import pytest
import requests
from django.test import override_settings

from integrations.hubtel import DryRunSMSProvider, HubtelSMSProvider, get_sms_provider


def _provider() -> HubtelSMSProvider:
    with override_settings(
        HUBTEL_BASE_URL="https://api.hubtel.test",
        HUBTEL_CLIENT_ID="test-id",
        HUBTEL_CLIENT_SECRET="test-secret",  # nosec
        HUBTEL_SENDER_ID="TESTSENDER",
        HUBTEL_CONNECT_TIMEOUT_SECONDS=5,
        HUBTEL_READ_TIMEOUT_SECONDS=10,
    ):
        return HubtelSMSProvider()


class TestHubtelSend:
    def test_success_returns_provider_message_id(self):
        provider = _provider()
        response = Mock(status_code=200)
        response.json.return_value = {"messageId": "abc-123"}

        with patch("integrations.hubtel.hubtel.requests.get", return_value=response) as mocked:
            result = provider.send(recipient_phone_e164="+233241234567", message_body="Hello")

        assert result.success is True
        assert result.provider_message_id == "abc-123"
        assert mocked.call_count == 1

    def test_timeout_is_reported_as_failure(self):
        provider = _provider()

        with patch(
            "integrations.hubtel.hubtel.requests.get", side_effect=requests.Timeout("timed out")
        ):
            result = provider.send(recipient_phone_e164="+233241234567", message_body="Hello")

        assert result.success is False
        assert "timed out" in result.error_summary.lower()

    def test_network_error_is_reported_as_failure(self):
        provider = _provider()

        with patch(
            "integrations.hubtel.hubtel.requests.get",
            side_effect=requests.ConnectionError("connection refused"),
        ):
            result = provider.send(recipient_phone_e164="+233241234567", message_body="Hello")

        assert result.success is False

    def test_authentication_failure_is_reported(self):
        provider = _provider()
        response = Mock(status_code=401)

        with patch("integrations.hubtel.hubtel.requests.get", return_value=response):
            result = provider.send(recipient_phone_e164="+233241234567", message_body="Hello")

        assert result.success is False
        assert result.response_code == "401"
        assert "auth" in result.error_summary.lower()

    def test_rate_limit_response_is_reported(self):
        provider = _provider()
        response = Mock(status_code=429)

        with patch("integrations.hubtel.hubtel.requests.get", return_value=response):
            result = provider.send(recipient_phone_e164="+233241234567", message_body="Hello")

        assert result.success is False
        assert result.response_code == "429"

    def test_server_error_is_reported(self):
        provider = _provider()
        response = Mock(status_code=503)

        with patch("integrations.hubtel.hubtel.requests.get", return_value=response):
            result = provider.send(recipient_phone_e164="+233241234567", message_body="Hello")

        assert result.success is False
        assert result.response_code == "503"

    def test_malformed_json_response_is_reported(self):
        provider = _provider()
        response = Mock(status_code=200)
        response.json.side_effect = ValueError("not JSON")

        with patch("integrations.hubtel.hubtel.requests.get", return_value=response):
            result = provider.send(recipient_phone_e164="+233241234567", message_body="Hello")

        assert result.success is False
        assert "malformed" in result.error_summary.lower()

    def test_4xx_business_rejection_is_reported(self):
        provider = _provider()
        response = Mock(status_code=400)
        response.json.return_value = {"message": "Invalid sender ID"}

        with patch("integrations.hubtel.hubtel.requests.get", return_value=response):
            result = provider.send(recipient_phone_e164="+233241234567", message_body="Hello")

        assert result.success is False
        assert result.error_summary == "Invalid sender ID"

    def test_2xx_with_nonzero_body_status_is_a_business_rejection(self):
        provider = _provider()
        response = Mock(status_code=201)
        response.json.return_value = {"status": 1004, "statusDescription": "Insufficient balance"}

        with patch("integrations.hubtel.hubtel.requests.get", return_value=response):
            result = provider.send(recipient_phone_e164="+233241234567", message_body="Hello")

        assert result.success is False
        assert result.response_code == "1004"

    def test_2xx_with_zero_body_status_succeeds(self):
        provider = _provider()
        response = Mock(status_code=201)
        response.json.return_value = {"status": 0, "messageId": "abc-123"}

        with patch("integrations.hubtel.hubtel.requests.get", return_value=response):
            result = provider.send(recipient_phone_e164="+233241234567", message_body="Hello")

        assert result.success is True
        assert result.provider_message_id == "abc-123"

    def test_get_status_returns_unknown(self):
        provider = _provider()
        result = provider.get_status("some-message-id")
        assert result.status == "UNKNOWN"


@pytest.mark.django_db
class TestGetSmsProvider:
    @override_settings(HUBTEL_ENABLED=False, SMS_DRY_RUN=True)
    def test_defaults_to_dry_run(self):
        assert isinstance(get_sms_provider(), DryRunSMSProvider)

    @override_settings(HUBTEL_ENABLED=True, SMS_DRY_RUN=True)
    def test_dry_run_flag_wins_even_when_hubtel_enabled(self):
        assert isinstance(get_sms_provider(), DryRunSMSProvider)

    @override_settings(HUBTEL_ENABLED=False, SMS_DRY_RUN=False)
    def test_hubtel_disabled_still_uses_dry_run(self):
        assert isinstance(get_sms_provider(), DryRunSMSProvider)

    @override_settings(HUBTEL_ENABLED=True, SMS_DRY_RUN=False)
    def test_both_env_flags_enable_real_provider_by_default(self):
        assert isinstance(get_sms_provider(), HubtelSMSProvider)

    @override_settings(HUBTEL_ENABLED=True, SMS_DRY_RUN=False)
    def test_dashboard_toggle_overrides_env_flags_when_paused(self):
        from apps.messaging.models import SMSSettings

        sms_settings = SMSSettings.get_solo()
        sms_settings.hubtel_enabled = False
        sms_settings.save(update_fields=["hubtel_enabled"])

        assert isinstance(get_sms_provider(), DryRunSMSProvider)


@pytest.mark.django_db
class TestDryRunProvider:
    def test_send_always_succeeds_without_network(self):
        provider = DryRunSMSProvider()
        result = provider.send(recipient_phone_e164="+233241234567", message_body="Hello")
        assert result.success is True
        assert result.provider_message_id.startswith("dry-run-")
