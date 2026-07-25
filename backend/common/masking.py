"""Display-masking for sensitive account identifiers (Section 12.2's
CustomerProfile payout fields; Section 16's disbursement modal).

This is presentation-only. It never substitutes for keeping the real value
out of a serializer that shouldn't return it in the first place — see
apps/customers/serializers.py's MaskedCustomerProfileSerializer.
"""


def mask_tail(value: str, visible: int = 4) -> str:
    if not value:
        return ""
    tail = value[-visible:]
    return f"•••• {tail}"
