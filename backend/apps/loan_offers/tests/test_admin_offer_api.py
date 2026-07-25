import json

import pytest

from apps.loan_offers.models import LoanOffer
from apps.loan_requests.models import LoanRequest
from apps.messaging.models import SMSMessage
from tests.factories import make_customer_profile, make_loan_request, make_offer, make_staff_user

Status = LoanOffer.Status
RequestStatus = LoanRequest.Status

VALID_PAYLOAD = {
    "principal": "10000.00",
    "interest_rate_percent": "12.00",
    "term_count": 6,
    "term_unit": "MONTH",
    "first_due_date": "2026-09-01",
    "customer_terms": "Standard terms apply.",
}


def create_url(loan_request_id) -> str:
    return f"/api/v1/admin/loan-requests/{loan_request_id}/offers/"


def detail_url(offer_id) -> str:
    return f"/api/v1/admin/offers/{offer_id}/"


def send_url(offer_id) -> str:
    return f"/api/v1/admin/offers/{offer_id}/send/"


def post_json(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


def patch_json(client, url, payload):
    return client.patch(url, data=json.dumps(payload), content_type="application/json")


@pytest.mark.django_db
class TestCreateOfferPermissions:
    def test_unauthenticated_is_rejected(self, client):
        loan_request = make_loan_request(status=RequestStatus.UNDER_REVIEW)

        response = post_json(client, create_url(loan_request.pk), VALID_PAYLOAD)

        assert response.status_code == 401

    def test_customer_is_rejected(self, client):
        loan_request = make_loan_request(status=RequestStatus.UNDER_REVIEW)
        client.force_login(make_customer_profile().user)

        response = post_json(client, create_url(loan_request.pk), VALID_PAYLOAD)

        assert response.status_code == 403


@pytest.mark.django_db
class TestCreateOffer:
    def test_officer_can_create_a_draft_offer(self, client):
        loan_request = make_loan_request(status=RequestStatus.UNDER_REVIEW)
        client.force_login(make_staff_user("LOAN_OFFICER"))

        response = post_json(client, create_url(loan_request.pk), VALID_PAYLOAD)

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == Status.DRAFT
        assert body["version_number"] == 1
        assert body["total_repayable"] == "11200.00"
        assert len(body["installments"]) == 6

    def test_second_draft_gets_version_two(self, client):
        loan_request = make_loan_request(status=RequestStatus.UNDER_REVIEW)
        client.force_login(make_staff_user("LOAN_OFFICER"))

        post_json(client, create_url(loan_request.pk), VALID_PAYLOAD)
        response = post_json(client, create_url(loan_request.pk), VALID_PAYLOAD)

        assert response.json()["version_number"] == 2

    def test_offer_numbers_match_the_calculator_exactly(self, client):
        loan_request = make_loan_request(status=RequestStatus.UNDER_REVIEW)
        client.force_login(make_staff_user("LOAN_OFFICER"))

        response = post_json(client, create_url(loan_request.pk), VALID_PAYLOAD)

        body = response.json()
        assert body["total_interest"] == "1200.00"
        assert body["installments"][0]["due_date"] == "2026-09-01"

    @pytest.mark.parametrize(
        "status",
        [
            RequestStatus.SUBMITTED,
            RequestStatus.DECLINED,
            RequestStatus.CANCELLED,
            RequestStatus.CONVERTED_TO_LOAN,
        ],
    )
    def test_cannot_create_an_offer_for_a_request_not_open_for_offers(self, client, status):
        loan_request = make_loan_request(status=status)
        client.force_login(make_staff_user("LOAN_OFFICER"))

        response = post_json(client, create_url(loan_request.pk), VALID_PAYLOAD)

        assert response.status_code == 409

    def test_invalid_term_count_returns_400_not_500(self, client):
        loan_request = make_loan_request(status=RequestStatus.UNDER_REVIEW)
        client.force_login(make_staff_user("LOAN_OFFICER"))

        response = post_json(
            client, create_url(loan_request.pk), {**VALID_PAYLOAD, "term_count": 0}
        )

        assert response.status_code == 400


@pytest.mark.django_db
class TestEditDraftOffer:
    def test_officer_can_edit_a_draft_before_send(self, client):
        loan_request = make_loan_request(status=RequestStatus.UNDER_REVIEW)
        offer = make_offer(loan_request, status=Status.DRAFT)
        client.force_login(make_staff_user("LOAN_OFFICER"))

        response = patch_json(
            client, detail_url(offer.pk), {**VALID_PAYLOAD, "principal": "8000.00"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["principal"] == "8000.00"
        assert body["version_number"] == offer.version_number  # edited in place, no new version

    def test_cannot_edit_after_send(self, client):
        loan_request = make_loan_request(status=RequestStatus.OFFER_SENT)
        offer = make_offer(loan_request, status=Status.SENT)
        client.force_login(make_staff_user("LOAN_OFFICER"))

        response = patch_json(client, detail_url(offer.pk), VALID_PAYLOAD)

        assert response.status_code == 409

    def test_get_detail_returns_installments(self, client):
        offer = make_offer(status=Status.DRAFT)
        client.force_login(make_staff_user("LOAN_OFFICER"))

        response = client.get(detail_url(offer.pk))

        assert response.status_code == 200
        assert len(response.json()["installments"]) == offer.installment_count
        assert "internal_notes" in response.json()


@pytest.mark.django_db
class TestSendOffer:
    def test_officer_can_send_a_draft(self, client):
        loan_request = make_loan_request(status=RequestStatus.UNDER_REVIEW)
        offer = make_offer(loan_request, status=Status.DRAFT)
        client.force_login(make_staff_user("LOAN_OFFICER"))

        response = client.post(send_url(offer.pk))

        assert response.status_code == 200
        assert response.json()["status"] == Status.SENT
        offer.loan_request.refresh_from_db()
        assert offer.loan_request.status == RequestStatus.OFFER_SENT

    def test_sending_a_revision_supersedes_the_previous_sent_version(self, client):
        loan_request = make_loan_request(status=RequestStatus.UNDER_REVIEW)
        first = make_offer(loan_request, version_number=1, status=Status.SENT)
        second = make_offer(loan_request, version_number=2, status=Status.DRAFT)
        client.force_login(make_staff_user("LOAN_OFFICER"))

        response = client.post(send_url(second.pk))

        assert response.status_code == 200
        first.refresh_from_db()
        assert first.status == Status.SUPERSEDED
        second.refresh_from_db()
        assert second.status == Status.SENT

    def test_cannot_send_an_already_sent_offer(self, client):
        offer = make_offer(status=Status.SENT)
        client.force_login(make_staff_user("LOAN_OFFICER"))

        response = client.post(send_url(offer.pk))

        assert response.status_code == 409

    def test_sending_records_a_loan_offer_ready_sms(self, client):
        profile = make_customer_profile()
        loan_request = make_loan_request(profile.user, status=RequestStatus.UNDER_REVIEW)
        offer = make_offer(loan_request, status=Status.DRAFT)
        client.force_login(make_staff_user("LOAN_OFFICER"))

        client.post(send_url(offer.pk))

        sms = SMSMessage.objects.get(
            customer=profile.user, message_type=SMSMessage.MessageType.LOAN_OFFER_READY
        )
        assert sms.status == SMSMessage.Status.PENDING
        assert sms.recipient_phone_e164 == profile.phone_number_e164
