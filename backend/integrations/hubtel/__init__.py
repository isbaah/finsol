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
    """Real Hubtel sending requires the env-level gate (HUBTEL_ENABLED=true,
    SMS_DRY_RUN=false — the all-defaults-off state always resolves here,
    never to HubtelSMSProvider; Section 17/20: "real sending must be
    impossible unless explicit environment configuration enables it") AND
    the admin-dashboard `SMSSettings.hubtel_enabled` pause/resume toggle.
    The env vars are a one-time, deploy-time "go-live" switch; the DB flag
    is the day-to-day on/off control an admin can flip without server
    access — deliberately layered so neither one alone can turn on real
    (paid) sending."""
    if not (settings.HUBTEL_ENABLED and not settings.SMS_DRY_RUN):
        return DryRunSMSProvider()

    # Imported lazily: this package sits underneath apps.messaging in the
    # dependency graph, so importing its models at module scope risks
    # running before Django's app registry is ready.
    from apps.messaging.models import SMSSettings

    if SMSSettings.get_solo().hubtel_enabled:
        return HubtelSMSProvider()
    return DryRunSMSProvider()
