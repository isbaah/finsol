"""Provider-neutral SMS interface (master prompt Section 17):

    SMSProvider.send(...) -> SMSProviderResult
    SMSProvider.get_status(provider_message_id) -> SMSDeliveryResult

apps/messaging/services.py is the only caller of get_sms_provider() —
nothing outside the messaging app ever imports a concrete provider class
directly ("route SMS through the messaging application service").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class SMSProviderResult:
    success: bool
    provider_message_id: str = ""
    response_code: str = ""
    error_summary: str = ""
    raw_response: dict = field(default_factory=dict)


@dataclass
class SMSDeliveryResult:
    # "DELIVERED" | "FAILED" | "PENDING" | "UNKNOWN"
    status: str
    raw_response: dict = field(default_factory=dict)


class SMSProvider(Protocol):
    def send(self, *, recipient_phone_e164: str, message_body: str) -> SMSProviderResult: ...

    def get_status(self, provider_message_id: str) -> SMSDeliveryResult: ...
