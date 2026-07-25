"""Proves Stage 5's acceptance criterion — "Preview and persisted
calculations use the same service" — concretely: the exact
AmortizationResult produced by calculate() (what the preview endpoint
returns) is what create_offer_with_schedule() persists, with no
translation that could let the two drift apart. Stage 7 wires the real
admin "create and send an offer" workflow on top of this same pipeline;
this stage proves the pipeline itself is sound.
"""

import dataclasses
from datetime import date
from decimal import Decimal

import pytest

from apps.loan_offers import services
from apps.loan_offers.amortization import AmortizationInput, calculate
from apps.loan_offers.models import LoanRequest
from tests.factories import make_loan_request, make_staff_user


@pytest.mark.django_db
def test_persisted_offer_totals_and_installments_match_the_calculator_exactly():
    loan_request = make_loan_request(status=LoanRequest.Status.UNDER_REVIEW)
    officer = make_staff_user("LOAN_OFFICER")
    calc_input = AmortizationInput(
        principal=Decimal("10000.00"),
        interest_rate_percent=Decimal("12.00"),
        term_count=6,
        term_unit="MONTH",
        first_due_date=date(2026, 9, 1),
    )

    result = calculate(calc_input)

    offer = services.create_offer_with_schedule(
        loan_request,
        officer=officer,
        principal=calc_input.principal,
        interest_rate_percent=calc_input.interest_rate_percent,
        term_count=calc_input.term_count,
        term_unit=calc_input.term_unit,
        first_due_date=calc_input.first_due_date,
        total_interest=result.total_interest,
        total_repayable=result.total_repayable,
        installment_count=result.installment_count,
        installments=[dataclasses.asdict(line) for line in result.installments],
    )

    assert offer.total_interest == result.total_interest
    assert offer.total_repayable == result.total_repayable
    assert offer.installment_count == result.installment_count

    persisted = list(offer.installments.order_by("sequence_number"))
    assert len(persisted) == len(result.installments)
    for persisted_row, calculated_row in zip(persisted, result.installments, strict=True):
        assert persisted_row.sequence_number == calculated_row.sequence_number
        assert persisted_row.due_date == calculated_row.due_date
        assert persisted_row.principal_due == calculated_row.principal_due
        assert persisted_row.interest_due == calculated_row.interest_due
        assert persisted_row.total_due == calculated_row.total_due
