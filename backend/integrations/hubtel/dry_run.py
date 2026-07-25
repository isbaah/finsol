"""Default SMS provider — never makes a network call. Used whenever real
sending isn't explicitly enabled (see get_sms_provider() in __init__.py),
which is the default in every environment including production until an
operator deliberately flips both HUBTEL_ENABLED and SMS_DRY_RUN.
"""

from __future__ import annotations

import logging
import uuid

from .base import SMSDeliveryResult, SMSProviderResult

logger = logging.getLogger(__name__)


class DryRunSMSProvider:
    def send(self, *, recipient_phone_e164: str, message_body: str) -> SMSProviderResult:
        provider_message_id = f"dry-run-{uuid.uuid4().hex[:16]}"
        logger.info(
            "sms.dry_run.send recipient=%s provider_message_id=%s length=%d",
            recipient_phone_e164,
            provider_message_id,
            len(message_body),
        )
        return SMSProviderResult(
            success=True, provider_message_id=provider_message_id, response_code="0"
        )

    def get_status(self, provider_message_id: str) -> SMSDeliveryResult:
        return SMSDeliveryResult(status="DELIVERED")
