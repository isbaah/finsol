"""Real Hubtel SMS adapter (master prompt Section 17, Section 30's Hubtel
docs reference). Sends via Hubtel's Quick SMS endpoint
(`GET {base}/v1/messages/send`, default base `https://smsc.hubtel.com`),
which takes `clientid`/`clientsecret`/`from`/`to`/`content` as query-string
parameters rather than a JSON body or HTTP Basic Auth header. Confirmed
live against the account this was configured for: POST returns HTTP 411
(the endpoint requires GET, not POST — it rejects a bodyless POST for
lacking a Content-Length), and a successful GET returns HTTP 201 with a
JSON body `{"status": 0, "messageId": ..., ...}` — a non-zero `status`
means a business-level rejection even though the HTTP status is 2xx.

**Security note**: the Quick SMS API puts the client secret in the URL
query string rather than a header. `requests` does not log request URLs on
its own, and nothing in this module logs the constructed URL — keep it that
way (log status codes/recipients, never `response.url` or the request
params) so the secret never ends up in application logs.

**Known limitation (see docs/BUILD_PROGRESS.md's Stage 11 section)**:
Hubtel's public SMS product delivers final delivery confirmation through a
delivery-callback webhook configured on the Hubtel account, not a
documented pull/status-query REST endpoint. `get_status()` is implemented
defensively — it returns `UNKNOWN` rather than guessing an endpoint shape
that could silently misreport delivery status in production. The
`query_sms_status` management command (Stage 11) is therefore best-effort:
it re-confirms `SENT` messages are still not definitively `FAILED`, but
cannot itself promote a message to `DELIVERED` until a real callback
receiver or a confirmed status endpoint is added — flagged, not silently
worked around.
"""

from __future__ import annotations

import logging

import requests
from django.conf import settings

from .base import SMSDeliveryResult, SMSProviderResult

logger = logging.getLogger(__name__)


class HubtelSMSProvider:
    def __init__(self) -> None:
        self._base_url = (settings.HUBTEL_BASE_URL or "https://smsc.hubtel.com").rstrip("/")
        self._client_id = settings.HUBTEL_CLIENT_ID
        self._client_secret = settings.HUBTEL_CLIENT_SECRET
        self._sender_id = settings.HUBTEL_SENDER_ID
        self._timeout = (
            settings.HUBTEL_CONNECT_TIMEOUT_SECONDS,
            settings.HUBTEL_READ_TIMEOUT_SECONDS,
        )

    def send(self, *, recipient_phone_e164: str, message_body: str) -> SMSProviderResult:
        url = f"{self._base_url}/v1/messages/send"
        params = {
            "clientid": self._client_id,
            "clientsecret": self._client_secret,
            "from": self._sender_id,
            "to": recipient_phone_e164.lstrip("+"),
            "content": message_body,
        }
        try:
            response = requests.get(
                url,
                params=params,
                timeout=self._timeout,
            )
        except requests.Timeout as exc:
            logger.warning("sms.hubtel.timeout recipient=%s", recipient_phone_e164)
            return SMSProviderResult(
                success=False, error_summary=f"Hubtel request timed out: {exc}"
            )
        except requests.RequestException as exc:
            logger.warning(
                "sms.hubtel.network_error recipient=%s error=%s", recipient_phone_e164, exc
            )
            return SMSProviderResult(success=False, error_summary=f"Hubtel network error: {exc}")

        return self._parse_response(response)

    def _parse_response(self, response: requests.Response) -> SMSProviderResult:
        status_code = response.status_code

        if status_code in (401, 403):
            logger.error("sms.hubtel.auth_failure status_code=%d", status_code)
            return SMSProviderResult(
                success=False,
                response_code=str(status_code),
                error_summary=(
                    "Hubtel authentication failed — check HUBTEL_CLIENT_ID/HUBTEL_CLIENT_SECRET."
                ),
            )
        if status_code == 429:
            logger.warning("sms.hubtel.rate_limited")
            return SMSProviderResult(
                success=False, response_code="429", error_summary="Hubtel rate limit exceeded."
            )
        if status_code >= 500:
            logger.warning("sms.hubtel.server_error status_code=%d", status_code)
            return SMSProviderResult(
                success=False,
                response_code=str(status_code),
                error_summary=f"Hubtel server error ({status_code}).",
            )

        try:
            data = response.json()
        except ValueError:
            logger.warning("sms.hubtel.malformed_response status_code=%d", status_code)
            return SMSProviderResult(
                success=False,
                response_code=str(status_code),
                error_summary="Malformed (non-JSON) response from Hubtel.",
            )
        if not isinstance(data, dict):
            return SMSProviderResult(
                success=False,
                response_code=str(status_code),
                error_summary="Unexpected response shape from Hubtel.",
            )

        if status_code >= 400:
            return SMSProviderResult(
                success=False,
                response_code=str(status_code),
                error_summary=str(
                    data.get("message") or data.get("Message") or "Hubtel rejected the request."
                ),
                raw_response=data,
            )

        # Quick SMS returns HTTP 200 even for business-level rejections (bad
        # sender ID, insufficient balance, etc.) — the real outcome is in the
        # body's "status" field (0/"0" = success; anything else = failure).
        body_status = data.get("status", data.get("Status"))
        if body_status is not None and str(body_status) != "0":
            logger.warning("sms.hubtel.business_rejection status=%s", body_status)
            return SMSProviderResult(
                success=False,
                response_code=str(body_status),
                error_summary=str(
                    data.get("message")
                    or data.get("Message")
                    or data.get("statusDescription")
                    or f"Hubtel rejected the request (status {body_status})."
                ),
                raw_response=data,
            )

        message_id = str(
            data.get("messageId") or data.get("MessageId") or data.get("message_id") or ""
        )
        return SMSProviderResult(
            success=True,
            provider_message_id=message_id,
            response_code=str(status_code),
            raw_response=data,
        )

    def get_status(self, provider_message_id: str) -> SMSDeliveryResult:
        return SMSDeliveryResult(status="UNKNOWN")
