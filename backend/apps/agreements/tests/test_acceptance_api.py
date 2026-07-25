import base64
import hashlib
import json
from io import BytesIO

import pytest
from django.core import mail
from PIL import Image

from apps.agreements.models import Agreement
from apps.loan_offers.models import LoanOffer
from apps.loan_requests.models import LoanRequest
from apps.loans.models import Loan
from integrations.storage.backends import get_storage
from tests.factories import (
    make_customer_profile,
    make_loan_request,
    make_offer,
    make_staff_user,
    make_user,
)

Status = LoanOffer.Status


def post_json(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


def _signature_data_url(fmt: str = "PNG") -> str:
    image = Image.new("RGBA", (12, 8), (10, 20, 30, 255))
    buf = BytesIO()
    image.save(buf, format=fmt)
    encoded = base64.b64encode(buf.getvalue()).decode()
    mime = "png" if fmt == "PNG" else "jpeg"
    return f"data:image/{mime};base64,{encoded}"


def _sent_offer():
    profile = make_customer_profile()
    loan_request = make_loan_request(profile.user)
    offer = make_offer(loan_request, status=Status.SENT)
    return profile, loan_request, offer


def accept_url(offer_id) -> str:
    return f"/api/v1/customer/offers/{offer_id}/accept/"


def reject_url(offer_id) -> str:
    return f"/api/v1/customer/offers/{offer_id}/reject/"


def revision_url(offer_id) -> str:
    return f"/api/v1/customer/offers/{offer_id}/request-revision/"


def _accept_payload(**overrides) -> dict:
    payload = {
        "typed_legal_name": "Ama Owusu",
        "declaration_accepted": True,
        "signature_image": _signature_data_url(),
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
class TestOfferAcceptance:
    def test_unauthenticated_is_rejected(self, client):
        _, _, offer = _sent_offer()

        response = post_json(client, accept_url(offer.pk), _accept_payload())

        assert response.status_code == 401

    def test_non_owner_cannot_accept(self, client):
        _, _, offer = _sent_offer()
        client.force_login(make_user())

        response = post_json(client, accept_url(offer.pk), _accept_payload())

        assert response.status_code == 403

    def test_valid_acceptance_creates_agreement_and_loan(self, client):
        profile, loan_request, offer = _sent_offer()
        client.force_login(profile.user)

        response = post_json(client, accept_url(offer.pk), _accept_payload())

        assert response.status_code == 201
        body = response.json()
        assert body["agreement"]["typed_legal_name"] == "Ama Owusu"
        assert body["agreement"]["email_delivery_status"] == "SENT"
        assert body["loan"]["status"] == Loan.Status.PENDING_APPROVAL
        assert body["loan"]["principal"] == str(offer.principal)

        offer.refresh_from_db()
        loan_request.refresh_from_db()
        assert offer.status == Status.ACCEPTED
        assert loan_request.status == LoanRequest.Status.CONVERTED_TO_LOAN
        assert Loan.objects.filter(loan_request=loan_request).exists()
        assert len(mail.outbox) == 1
        assert mail.outbox[0].attachments

    def test_declaration_must_be_checked(self, client):
        profile, _, offer = _sent_offer()
        client.force_login(profile.user)

        response = post_json(
            client, accept_url(offer.pk), _accept_payload(declaration_accepted=False)
        )

        assert response.status_code == 400

    def test_invalid_signature_is_rejected(self, client):
        profile, _, offer = _sent_offer()
        client.force_login(profile.user)

        response = post_json(
            client,
            accept_url(offer.pk),
            _accept_payload(signature_image="not-a-real-data-url"),
        )

        assert response.status_code == 409
        assert not Agreement.objects.exists()

    def test_non_image_bytes_are_rejected(self, client):
        profile, _, offer = _sent_offer()
        client.force_login(profile.user)
        fake = base64.b64encode(b"not an image at all").decode()

        response = post_json(
            client,
            accept_url(offer.pk),
            _accept_payload(signature_image=f"data:image/png;base64,{fake}"),
        )

        assert response.status_code == 409
        assert not Agreement.objects.exists()

    def test_non_current_offer_cannot_be_accepted(self, client):
        # A superseded (no longer current) version can never be accepted —
        # only the offer service's own SENT-only transition guard matters
        # here, so build the fixture directly in SUPERSEDED rather than
        # going through send_offer()'s live supersede flow.
        profile, loan_request, offer = _sent_offer()
        offer.status = Status.SUPERSEDED
        offer.save(update_fields=["status"])
        client.force_login(profile.user)

        response = post_json(client, accept_url(offer.pk), _accept_payload())

        assert response.status_code == 409
        assert not Agreement.objects.exists()

    def test_double_acceptance_is_rejected(self, client):
        profile, _, offer = _sent_offer()
        client.force_login(profile.user)
        first = post_json(client, accept_url(offer.pk), _accept_payload())
        assert first.status_code == 201

        second = post_json(client, accept_url(offer.pk), _accept_payload())

        assert second.status_code == 409
        assert Agreement.objects.filter(offer=offer).count() == 1

    def test_hash_generation_matches_stored_bytes(self, client):
        profile, _, offer = _sent_offer()
        client.force_login(profile.user)

        response = post_json(client, accept_url(offer.pk), _accept_payload())
        assert response.status_code == 201

        agreement = Agreement.objects.get(offer=offer)
        storage = get_storage()
        pdf_bytes = storage.read(agreement.agreement_pdf_path)
        signature_bytes = storage.read(agreement.signature_image_path)
        assert hashlib.sha256(pdf_bytes).hexdigest() == agreement.agreement_pdf_sha256
        assert hashlib.sha256(signature_bytes).hexdigest() == agreement.signature_image_sha256
        assert pdf_bytes.startswith(b"%PDF")

    def test_email_failure_does_not_undo_acceptance(self, client, monkeypatch):
        import django.core.mail as mail_module

        def _raise(self, fail_silently=False):
            raise RuntimeError("smtp down")

        monkeypatch.setattr(mail_module.EmailMessage, "send", _raise)

        profile, loan_request, offer = _sent_offer()
        client.force_login(profile.user)

        response = post_json(client, accept_url(offer.pk), _accept_payload())

        assert response.status_code == 201
        body = response.json()
        assert body["agreement"]["email_delivery_status"] == "FAILED"
        offer.refresh_from_db()
        loan_request.refresh_from_db()
        assert offer.status == Status.ACCEPTED
        assert loan_request.status == LoanRequest.Status.CONVERTED_TO_LOAN
        assert Loan.objects.filter(loan_request=loan_request).exists()


@pytest.mark.django_db
class TestOfferRejectAndRevision:
    def test_reject_moves_offer_and_request_to_terminal_states(self, client):
        profile, loan_request, offer = _sent_offer()
        client.force_login(profile.user)

        response = post_json(client, reject_url(offer.pk), {"reason": "Too expensive"})

        assert response.status_code == 200
        offer.refresh_from_db()
        loan_request.refresh_from_db()
        assert offer.status == Status.REJECTED
        assert loan_request.status == LoanRequest.Status.CUSTOMER_REJECTED

    def test_reject_reason_is_optional(self, client):
        profile, _, offer = _sent_offer()
        client.force_login(profile.user)

        response = post_json(client, reject_url(offer.pk), {})

        assert response.status_code == 200

    def test_request_revision_requires_a_reason(self, client):
        profile, _, offer = _sent_offer()
        client.force_login(profile.user)

        response = post_json(client, revision_url(offer.pk), {})

        assert response.status_code == 400

    def test_request_revision_moves_request_to_revision_requested(self, client):
        profile, loan_request, offer = _sent_offer()
        client.force_login(profile.user)

        response = post_json(
            client, revision_url(offer.pk), {"reason": "Please lower the monthly amount"}
        )

        assert response.status_code == 200
        offer.refresh_from_db()
        loan_request.refresh_from_db()
        assert offer.status == Status.REJECTED
        assert loan_request.status == LoanRequest.Status.REVISION_REQUESTED

    def test_non_owner_cannot_reject(self, client):
        _, _, offer = _sent_offer()
        client.force_login(make_user())

        response = post_json(client, reject_url(offer.pk), {"reason": "no"})

        assert response.status_code == 403


@pytest.mark.django_db
class TestAgreementDownload:
    def _accept(self, client, profile, offer):
        client.force_login(profile.user)
        response = post_json(client, accept_url(offer.pk), _accept_payload())
        assert response.status_code == 201
        return response.json()["agreement"]["id"]

    def test_owner_can_download(self, client):
        profile, _, offer = _sent_offer()
        agreement_id = self._accept(client, profile, offer)

        response = client.get(f"/api/v1/agreements/{agreement_id}/download/")

        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert response.content.startswith(b"%PDF")

    def test_non_owner_cannot_download(self, client):
        profile, _, offer = _sent_offer()
        agreement_id = self._accept(client, profile, offer)
        client.logout()
        client.force_login(make_user())

        response = client.get(f"/api/v1/agreements/{agreement_id}/download/")

        assert response.status_code == 403

    def test_staff_can_download(self, client):
        profile, _, offer = _sent_offer()
        agreement_id = self._accept(client, profile, offer)
        client.logout()
        client.force_login(make_staff_user("LOAN_OFFICER"))

        response = client.get(f"/api/v1/agreements/{agreement_id}/download/")

        assert response.status_code == 200

    def test_unauthenticated_cannot_download(self, client):
        profile, _, offer = _sent_offer()
        agreement_id = self._accept(client, profile, offer)
        client.logout()

        response = client.get(f"/api/v1/agreements/{agreement_id}/download/")

        assert response.status_code == 401


@pytest.mark.django_db
class TestAgreementEmailRetry:
    def test_retry_resends_after_a_failure(self, client, monkeypatch):
        import django.core.mail as mail_module

        def _raise(self, fail_silently=False):
            raise RuntimeError("smtp down")

        monkeypatch.setattr(mail_module.EmailMessage, "send", _raise)
        profile, _, offer = _sent_offer()
        client.force_login(profile.user)
        accept_response = post_json(client, accept_url(offer.pk), _accept_payload())
        agreement_id = accept_response.json()["agreement"]["id"]
        assert accept_response.json()["agreement"]["email_delivery_status"] == "FAILED"
        client.logout()

        monkeypatch.undo()
        client.force_login(make_staff_user("LOAN_OFFICER"))
        retry_response = client.post(f"/api/v1/admin/agreements/{agreement_id}/retry-email/")

        assert retry_response.status_code == 200
        assert retry_response.json()["email_delivery_status"] == "SENT"

    def test_only_staff_can_retry(self, client):
        profile, _, offer = _sent_offer()
        client.force_login(profile.user)
        accept_response = post_json(client, accept_url(offer.pk), _accept_payload())
        agreement_id = accept_response.json()["agreement"]["id"]

        response = client.post(f"/api/v1/admin/agreements/{agreement_id}/retry-email/")

        assert response.status_code == 403
