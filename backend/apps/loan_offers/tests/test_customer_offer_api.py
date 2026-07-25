import pytest

from apps.loan_offers.models import LoanOffer
from tests.factories import make_customer_profile, make_loan_request, make_offer, make_user

Status = LoanOffer.Status


def detail_url(offer_id) -> str:
    return f"/api/v1/customer/offers/{offer_id}/"


@pytest.mark.django_db
class TestCustomerOfferVisibility:
    def test_unauthenticated_is_rejected(self, client):
        offer = make_offer(status=Status.SENT)

        response = client.get(detail_url(offer.pk))

        assert response.status_code == 401

    def test_owner_can_view_their_sent_offer_and_full_schedule(self, client):
        profile = make_customer_profile()
        loan_request = make_loan_request(profile.user)
        offer = make_offer(loan_request, status=Status.SENT)
        client.force_login(profile.user)

        response = client.get(detail_url(offer.pk))

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == Status.SENT
        assert body["request_number"] == loan_request.request_number
        assert len(body["installments"]) == offer.installment_count
        assert "internal_notes" not in body
        assert "created_by" not in body

    def test_non_owner_cannot_view_someone_elses_offer(self, client):
        offer = make_offer(status=Status.SENT)
        client.force_login(make_user())

        response = client.get(detail_url(offer.pk))

        assert response.status_code == 403

    def test_customer_can_see_a_draft_offer_not_yet_sent(self, client):
        # Stage 7's page is read-only; nothing prevents a customer fetching
        # a not-yet-sent version by id if they somehow had it — the
        # frontend only ever links to the "current" (SENT) one via
        # LoanRequestSerializer.current_offer. Ownership is what matters
        # here, not offer status.
        profile = make_customer_profile()
        loan_request = make_loan_request(profile.user)
        offer = make_offer(loan_request, status=Status.DRAFT)
        client.force_login(profile.user)

        response = client.get(detail_url(offer.pk))

        assert response.status_code == 200
