from django.conf import settings

from .base import SMSDeliveryResult, SMSProvider, SMSProviderResult
from .dry_run import DryRunSMSProvider
from .hubtel import HubtelSMSProvider

__all__ = [
    "SMSProvider",
    "SMSProviderResult",
    "SMSDeliveryResult",
    "DryRunSMSProvider",
    "HubtelSMSProvider",
    "get_sms_provider",
]


def get_sms_provider() -> SMSProvider:
    """Real Hubtel sending requires BOTH flags explicitly set — the
    all-defaults-off state (HUBTEL_ENABLED=false, SMS_DRY_RUN=true) always
    resolves here, never to HubtelSMSProvider (Section 17/20: "real sending
    must be impossible unless explicit environment configuration enables
    it")."""
    if settings.HUBTEL_ENABLED and not settings.SMS_DRY_RUN:
        return HubtelSMSProvider()
    return DryRunSMSProvider()
