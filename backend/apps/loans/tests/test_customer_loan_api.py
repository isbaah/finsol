"""Stage 12: the customer loan list endpoint added for the customer
dashboard's active-loan summary (Section 15)."""

from datetime import date
from decimal import Decimal

import pytest

from tests.factories import make_active_loan, make_user

LIST_URL = "/api/v1/customer/loans/"


@pytest.mark.django_db
class TestCustomerLoanList:
    def test_unauthenticated_is_rejected(self, client):
        assert client.get(LIST_URL).status_code in (401, 403)

    def test_customer_sees_only_their_own_loans(self, client):
        mine = make_active_loan(
            principal=Decimal("1000.00"),
            total_interest=Decimal("0.00"),
            installment_count=2,
            first_due_date=date(2027, 1, 1),
        )
        make_active_loan(
            principal=Decimal("2000.00"),
            total_interest=Decimal("0.00"),
            installment_count=2,
            first_due_date=date(2027, 1, 1),
        )  # someone else's loan

        client.force_login(mine.customer)
        response = client.get(LIST_URL)

        assert response.status_code == 200
        body = response.json()
        results = body["results"] if isinstance(body, dict) and "results" in body else body
        assert [row["loan_number"] for row in results] == [mine.loan_number]
        # The list serializer carries the schedule the dashboard summarises.
        assert len(results[0]["installments"]) == 2

    def test_customer_with_no_loans_gets_an_empty_list(self, client):
        client.force_login(make_user())
        response = client.get(LIST_URL)
        assert response.status_code == 200
        body = response.json()
        results = body["results"] if isinstance(body, dict) and "results" in body else body
        assert results == []
