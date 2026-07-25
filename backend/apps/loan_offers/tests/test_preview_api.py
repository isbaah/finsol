import json

import pytest

from apps.loan_offers.models import LoanOffer, OfferInstallment
from tests.factories import make_staff_user, make_user

PREVIEW_URL = "/api/v1/admin/offers/preview/"

VALID_PAYLOAD = {
    "principal": "10000.00",
    "interest_rate_percent": "12.00",
    "term_count": 6,
    "term_unit": "MONTH",
    "first_due_date": "2026-09-01",
}


def post_json(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


@pytest.mark.django_db
class TestPreviewPermissions:
    def test_unauthenticated_is_rejected(self, client):
        response = post_json(client, PREVIEW_URL, VALID_PAYLOAD)

        assert response.status_code == 401

    def test_plain_customer_is_rejected(self, client):
        client.force_login(make_user())

        response = post_json(client, PREVIEW_URL, VALID_PAYLOAD)

        assert response.status_code == 403

    @pytest.mark.parametrize("role", ["FINANCE_OFFICER", "APPROVER", "AUDITOR"])
    def test_non_offer_creating_staff_roles_are_rejected(self, client, role):
        client.force_login(make_staff_user(role))

        response = post_json(client, PREVIEW_URL, VALID_PAYLOAD)

        assert response.status_code == 403

    @pytest.mark.parametrize("role", ["LOAN_OFFICER", "SUPER_ADMIN"])
    def test_authorised_roles_can_preview(self, client, role):
        client.force_login(make_staff_user(role))

        response = post_json(client, PREVIEW_URL, VALID_PAYLOAD)

        assert response.status_code == 200


@pytest.mark.django_db
class TestPreviewCalculation:
    def test_preview_returns_the_same_numbers_the_calculator_would(self, client):
        client.force_login(make_staff_user("LOAN_OFFICER"))

        response = post_json(client, PREVIEW_URL, VALID_PAYLOAD)

        body = response.json()
        assert body["total_interest"] == "1200.00"
        assert body["total_repayable"] == "11200.00"
        assert body["installment_count"] == 6
        assert len(body["installments"]) == 6
        assert body["installments"][0]["due_date"] == "2026-09-01"
        assert body["installments"][-1]["due_date"] == "2027-02-01"

    def test_invalid_term_count_returns_400_not_500(self, client):
        client.force_login(make_staff_user("LOAN_OFFICER"))

        response = post_json(client, PREVIEW_URL, {**VALID_PAYLOAD, "term_count": 0})

        assert response.status_code == 400

    def test_negative_principal_returns_400(self, client):
        client.force_login(make_staff_user("LOAN_OFFICER"))

        response = post_json(client, PREVIEW_URL, {**VALID_PAYLOAD, "principal": "-500.00"})

        assert response.status_code == 400

    def test_invalid_term_unit_returns_400(self, client):
        client.force_login(make_staff_user("LOAN_OFFICER"))

        response = post_json(client, PREVIEW_URL, {**VALID_PAYLOAD, "term_unit": "DAY"})

        assert response.status_code == 400

    def test_preview_never_persists_an_offer_or_installments(self, client):
        client.force_login(make_staff_user("LOAN_OFFICER"))

        post_json(client, PREVIEW_URL, VALID_PAYLOAD)
        post_json(client, PREVIEW_URL, VALID_PAYLOAD)
        post_json(client, PREVIEW_URL, {**VALID_PAYLOAD, "term_count": 12})

        assert LoanOffer.objects.count() == 0
        assert OfferInstallment.objects.count() == 0
