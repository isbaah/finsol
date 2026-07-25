"""Centralised Decimal money quantization (master prompt Section 13:
"Never use binary floating-point values for money or rates... Centralise
quantization in a money utility"). Every monetary calculation in the
codebase — the amortization engine (apps/loan_offers/amortization.py),
ledger postings, everything — rounds through quantize(), so "two decimal
places, ROUND_HALF_UP" is enforced in exactly one place.
"""

from decimal import ROUND_HALF_UP, Decimal

TWO_PLACES = Decimal("0.01")


def quantize(amount: Decimal) -> Decimal:
    return Decimal(amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def to_decimal(value: str | int | Decimal) -> Decimal:
    """Safe construction from str/int/Decimal — never from float, since a
    float literal already carries binary floating-point representation
    error before Decimal() ever sees it (Decimal(0.1) != Decimal("0.1"))."""
    if isinstance(value, float):
        raise TypeError(
            "Money values must never be constructed from float — use str, int, or Decimal."
        )
    return Decimal(value)
