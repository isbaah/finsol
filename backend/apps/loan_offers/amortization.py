"""The authoritative financial calculation engine (master prompt Section 13
/ docs/ARCHITECTURE.md Section 8):

    AmortizationCalculator.calculate(input: AmortizationInput) -> AmortizationResult

Pure and deterministic — no HTTP, no database I/O, no Django model
imports. This is what makes it safe to call from both the Stage 5 preview
endpoint (which must never persist anything) and the real offer-creation
path (apps/loan_offers/services.py::create_offer_with_schedule), so preview
and persisted numbers can never drift apart — they're the same function
call.

Only one strategy is implemented for the MVP (`FLAT_TOTAL_TERM`,
docs/PRODUCT_ASSUMPTIONS.md Section 6 / ADR-003), dispatched by
`interest_method` so a second strategy is an additive change later, not a
rewrite of this module or its callers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from common.money import quantize

MAX_TERM_COUNT = 60  # matches apps/loan_offers/models.py's LoanOffer bound
FLAT_TOTAL_TERM = "FLAT_TOTAL_TERM"
WEEK = "WEEK"
MONTH = "MONTH"


class AmortizationError(ValueError):
    """Raised for invalid input — a domain error, not a Django validation
    error, since this module has no framework dependency of its own."""


@dataclass(frozen=True)
class AmortizationInput:
    principal: Decimal
    interest_rate_percent: Decimal
    term_count: int
    term_unit: str  # WEEK | MONTH
    first_due_date: date
    interest_method: str = FLAT_TOTAL_TERM


@dataclass(frozen=True)
class InstallmentLine:
    sequence_number: int
    due_date: date
    principal_due: Decimal
    interest_due: Decimal
    total_due: Decimal


@dataclass(frozen=True)
class AmortizationResult:
    total_interest: Decimal
    total_repayable: Decimal
    installment_count: int
    installments: list[InstallmentLine]


def calculate(data: AmortizationInput) -> AmortizationResult:
    _validate(data)
    if data.interest_method == FLAT_TOTAL_TERM:
        return _calculate_flat_total_term(data)
    raise AmortizationError(f"Unsupported interest method: {data.interest_method!r}.")


def _validate(data: AmortizationInput) -> None:
    if data.principal <= 0:
        raise AmortizationError("Principal must be greater than zero.")
    if data.interest_rate_percent < 0:
        raise AmortizationError("Interest rate percent cannot be negative.")
    if data.term_count <= 0:
        raise AmortizationError("Term count must be greater than zero.")
    if data.term_count > MAX_TERM_COUNT:
        raise AmortizationError(f"Term count cannot exceed {MAX_TERM_COUNT}.")
    if data.term_unit not in (WEEK, MONTH):
        raise AmortizationError(f"Unsupported term unit: {data.term_unit!r}.")


def _generate_due_dates(first_due_date: date, term_unit: str, count: int) -> list[date]:
    """Each due date is computed independently from `first_due_date` (never
    cumulatively from the previous due date), so a schedule starting on the
    31st correctly clips per-month (31 -> 28/29 -> 31 -> 30 -> 31...)
    instead of permanently drifting to the 28th once a short month is hit —
    Section 13: "For months lacking the same day number, use the valid
    end-of-month behavior."
    """
    if term_unit == WEEK:
        return [first_due_date + timedelta(weeks=i) for i in range(count)]
    return [first_due_date + relativedelta(months=i) for i in range(count)]


def _calculate_flat_total_term(data: AmortizationInput) -> AmortizationResult:
    total_interest = quantize(data.principal * data.interest_rate_percent / Decimal(100))
    total_repayable = quantize(data.principal + total_interest)
    count = data.term_count

    due_dates = _generate_due_dates(data.first_due_date, data.term_unit, count)
    principal_each = quantize(data.principal / count)
    interest_each = quantize(total_interest / count)

    installments: list[InstallmentLine] = []
    principal_accumulated = Decimal("0.00")
    interest_accumulated = Decimal("0.00")
    for sequence_number in range(1, count + 1):
        if sequence_number < count:
            principal_due = principal_each
            interest_due = interest_each
        else:
            # Exact residue correction: whatever rounding left unaccounted
            # for goes entirely on the final installment, so the sums
            # reconcile exactly to the penny (Section 13).
            principal_due = quantize(data.principal - principal_accumulated)
            interest_due = quantize(total_interest - interest_accumulated)
        principal_accumulated += principal_due
        interest_accumulated += interest_due
        installments.append(
            InstallmentLine(
                sequence_number=sequence_number,
                due_date=due_dates[sequence_number - 1],
                principal_due=principal_due,
                interest_due=interest_due,
                total_due=quantize(principal_due + interest_due),
            )
        )

    return AmortizationResult(
        total_interest=total_interest,
        total_repayable=total_repayable,
        installment_count=count,
        installments=installments,
    )
