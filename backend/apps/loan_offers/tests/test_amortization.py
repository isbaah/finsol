from datetime import date
from decimal import Decimal

import pytest

from apps.loan_offers.amortization import AmortizationError, AmortizationInput, calculate


def _input(**overrides):
    defaults = {
        "principal": Decimal("5000.00"),
        "interest_rate_percent": Decimal("12.00"),
        "term_count": 6,
        "term_unit": "MONTH",
        "first_due_date": date(2026, 9, 1),
    }
    defaults.update(overrides)
    return AmortizationInput(**defaults)


def _sum(values):
    total = Decimal("0.00")
    for value in values:
        total += value
    return total


class TestValidation:
    def test_rejects_zero_principal(self):
        with pytest.raises(AmortizationError):
            calculate(_input(principal=Decimal("0.00")))

    def test_rejects_negative_principal(self):
        with pytest.raises(AmortizationError):
            calculate(_input(principal=Decimal("-100.00")))

    def test_rejects_negative_interest_rate(self):
        with pytest.raises(AmortizationError):
            calculate(_input(interest_rate_percent=Decimal("-1.00")))

    def test_rejects_zero_term_count(self):
        with pytest.raises(AmortizationError):
            calculate(_input(term_count=0))

    def test_rejects_negative_term_count(self):
        with pytest.raises(AmortizationError):
            calculate(_input(term_count=-3))

    def test_rejects_term_count_over_the_safe_bound(self):
        with pytest.raises(AmortizationError):
            calculate(_input(term_count=61))

    def test_rejects_unsupported_term_unit(self):
        with pytest.raises(AmortizationError):
            calculate(_input(term_unit="DAY"))

    def test_rejects_unsupported_interest_method(self):
        with pytest.raises(AmortizationError):
            calculate(_input(interest_method="REDUCING_BALANCE"))


class TestFlatTotalTermCalculation:
    def test_zero_interest_loan(self):
        result = calculate(_input(interest_rate_percent=Decimal("0.00"), term_count=4))

        assert result.total_interest == Decimal("0.00")
        assert result.total_repayable == Decimal("5000.00")
        assert all(line.interest_due == Decimal("0.00") for line in result.installments)

    def test_normal_interest_loan_matches_the_documented_worked_example(self):
        # docs/PRODUCT_ASSUMPTIONS.md Section 6 / master prompt Section 29:
        # GHS 10,000 at 12% flat total-term over 6 months.
        result = calculate(
            _input(
                principal=Decimal("10000.00"),
                interest_rate_percent=Decimal("12.00"),
                term_count=6,
            )
        )

        assert result.total_interest == Decimal("1200.00")
        assert result.total_repayable == Decimal("11200.00")
        assert result.installment_count == 6
        first_five = result.installments[:5]
        last = result.installments[5]
        assert all(line.principal_due == Decimal("1666.67") for line in first_five)
        assert all(line.interest_due == Decimal("200.00") for line in first_five)
        assert all(line.total_due == Decimal("1866.67") for line in first_five)
        # Residue correction: 10000.00 - (1666.67 * 5) = 1666.65 on the last line.
        assert last.principal_due == Decimal("1666.65")
        assert last.interest_due == Decimal("200.00")
        assert last.total_due == Decimal("1866.65")

    def test_one_installment(self):
        result = calculate(_input(term_count=1))

        assert len(result.installments) == 1
        line = result.installments[0]
        assert line.principal_due == Decimal("5000.00")
        assert line.interest_due == result.total_interest
        assert line.total_due == result.total_repayable

    def test_principal_that_creates_rounding_residue(self):
        # 1000 / 3 = 333.333... — the classic residue case.
        result = calculate(
            _input(
                principal=Decimal("1000.00"), interest_rate_percent=Decimal("0.00"), term_count=3
            )
        )

        assert result.installments[0].principal_due == Decimal("333.33")
        assert result.installments[1].principal_due == Decimal("333.33")
        assert result.installments[2].principal_due == Decimal("333.34")  # residue absorbed here
        assert _sum(line.principal_due for line in result.installments) == Decimal("1000.00")

    def test_exact_sum_reconciliation(self):
        result = calculate(
            _input(
                principal=Decimal("7777.77"), interest_rate_percent=Decimal("13.50"), term_count=7
            )
        )

        assert _sum(line.principal_due for line in result.installments) == Decimal("7777.77")
        assert _sum(line.interest_due for line in result.installments) == result.total_interest
        assert _sum(line.total_due for line in result.installments) == result.total_repayable
        assert result.total_repayable == Decimal("7777.77") + result.total_interest

    @pytest.mark.parametrize(
        "principal,rate,count",
        [
            (Decimal("100.00"), Decimal("5.00"), 2),
            (Decimal("999.99"), Decimal("17.00"), 11),
            (Decimal("1.00"), Decimal("0.01"), 1),
            (Decimal("50000.00"), Decimal("25.00"), 24),
            (Decimal("333.33"), Decimal("0.00"), 6),
        ],
    )
    def test_exact_reconciliation_across_many_combinations(self, principal, rate, count):
        result = calculate(
            _input(principal=principal, interest_rate_percent=rate, term_count=count)
        )

        assert _sum(line.principal_due for line in result.installments) == principal
        assert _sum(line.interest_due for line in result.installments) == result.total_interest
        assert _sum(line.total_due for line in result.installments) == result.total_repayable
        assert len(result.installments) == count


class TestDueDateGeneration:
    def test_weekly_schedule_adds_exact_seven_day_increments(self):
        result = calculate(_input(term_unit="WEEK", term_count=4, first_due_date=date(2026, 9, 1)))

        due_dates = [line.due_date for line in result.installments]
        assert due_dates == [
            date(2026, 9, 1),
            date(2026, 9, 8),
            date(2026, 9, 15),
            date(2026, 9, 22),
        ]

    def test_monthly_schedule_adds_calendar_months(self):
        result = calculate(
            _input(term_unit="MONTH", term_count=3, first_due_date=date(2026, 6, 15))
        )

        due_dates = [line.due_date for line in result.installments]
        assert due_dates == [date(2026, 6, 15), date(2026, 7, 15), date(2026, 8, 15)]

    def test_january_31_progression_clips_to_valid_end_of_month_each_time(self):
        result = calculate(
            _input(term_unit="MONTH", term_count=5, first_due_date=date(2026, 1, 31))
        )

        due_dates = [line.due_date for line in result.installments]
        # 2026 is not a leap year (Feb has 28 days); April has 30.
        assert due_dates == [
            date(2026, 1, 31),
            date(2026, 2, 28),
            date(2026, 3, 31),
            date(2026, 4, 30),
            date(2026, 5, 31),
        ]

    def test_leap_year_jan_31_progression_uses_feb_29(self):
        # 2028 is a leap year.
        result = calculate(
            _input(term_unit="MONTH", term_count=2, first_due_date=date(2028, 1, 31))
        )

        due_dates = [line.due_date for line in result.installments]
        assert due_dates == [date(2028, 1, 31), date(2028, 2, 29)]

    def test_leap_year_feb_29_start_progresses_to_non_leap_feb_28(self):
        result = calculate(
            _input(term_unit="MONTH", term_count=13, first_due_date=date(2028, 2, 29))
        )

        due_dates = [line.due_date for line in result.installments]
        assert due_dates[0] == date(2028, 2, 29)
        # 12 months later is Feb 2029 — not a leap year, so clipped to 28.
        assert due_dates[12] == date(2029, 2, 28)
