"""Post-Stage-12 customer "I've paid" claims: informational notices that
surface in the admin claims queue, never touching financial state."""

import json
from datetime import date
from decimal import Decimal

import pytest

from apps.audit.models import AuditEvent
from apps.repayments import services
from apps.repayments.models import PaymentClaim
from tests.factories import make_active_loan, make_staff_user, make_user

CLAIMS_URL = "/api/v1/admin/payment-claims/"


def claim_url(installment_id) -> str:
    return f"/api/v1/customer/installments/{installment_id}/claim-payment/"


def resolve_url(claim_id) -> str:
    return f"/api/v1/admin/payment-claims/{claim_id}/resolve/"


def post_json(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


def _loan_and_installment(**overrides):
    loan = make_active_loan(
        principal=Decimal("1000.00"),
        total_interest=Decimal("0.00"),
        installment_count=2,
        first_due_date=date(2027, 1, 1),
        **overrides,
    )
    return loan, loan.installments.get(sequence_number=1)


@pytest.mark.django_db
class TestCustomerClaim:
    def test_customer_can_claim_and_it_is_audited(self, client):
        loan, installment = _loan_and_installment()
        client.force_login(loan.customer)

        response = post_json(client, claim_url(installment.pk), {"note": "Paid via MoMo today"})

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "PENDING"
        assert body["note"] == "Paid via MoMo today"
        assert body["loan_number"] == loan.loan_number
        assert AuditEvent.objects.filter(action="payment_claim.create").exists()

    def test_duplicate_pending_claim_is_rejected(self, client):
        loan, installment = _loan_and_installment()
        client.force_login(loan.customer)
        assert post_json(client, claim_url(installment.pk), {}).status_code == 201

        response = post_json(client, claim_url(installment.pk), {})

        assert response.status_code == 409
        assert PaymentClaim.objects.count() == 1

    def test_cannot_claim_someone_elses_installment(self, client):
        _, installment = _loan_and_installment()
        client.force_login(make_user())

        response = post_json(client, claim_url(installment.pk), {})

        assert response.status_code == 404
        assert PaymentClaim.objects.count() == 0

    def test_cannot_claim_a_settled_installment(self, client):
        loan, installment = _loan_and_installment()
        services.record_payment(
            loan,
            amount=Decimal("500.00"),
            payment_date=date(2026, 7, 20),
            payment_method="MOBILE_MONEY",
            recorded_by=make_staff_user("FINANCE_OFFICER"),
        )
        installment.refresh_from_db()
        assert installment.status == "PAID"
        client.force_login(loan.customer)

        response = post_json(client, claim_url(installment.pk), {})

        assert response.status_code == 409


@pytest.mark.django_db
class TestAdminClaimQueue:
    def test_staff_can_list_pending_claims(self, client):
        loan, installment = _loan_and_installment()
        client.force_login(loan.customer)
        post_json(client, claim_url(installment.pk), {"note": "Sent it"})

        client.force_login(make_staff_user("AUDITOR"))
        response = client.get(CLAIMS_URL, {"status": "PENDING"})

        assert response.status_code == 200
        body = response.json()
        results = body["results"] if isinstance(body, dict) and "results" in body else body
        assert len(results) == 1
        assert results[0]["customer_email"] == loan.customer.email

    def test_customer_cannot_list_claims(self, client):
        client.force_login(make_user())
        assert client.get(CLAIMS_URL).status_code == 403

    def test_loan_officer_can_resolve_and_it_is_audited(self, client):
        loan, installment = _loan_and_installment()
        client.force_login(loan.customer)
        claim_id = post_json(client, claim_url(installment.pk), {}).json()["id"]

        client.force_login(make_staff_user("LOAN_OFFICER"))
        response = post_json(client, resolve_url(claim_id), {})

        assert response.status_code == 200
        assert response.json()["status"] == "RESOLVED"
        assert AuditEvent.objects.filter(action="payment_claim.resolve").exists()

    def test_auditor_cannot_resolve(self, client):
        loan, installment = _loan_and_installment()
        client.force_login(loan.customer)
        claim_id = post_json(client, claim_url(installment.pk), {}).json()["id"]

        client.force_login(make_staff_user("AUDITOR"))
        assert post_json(client, resolve_url(claim_id), {}).status_code == 403


@pytest.mark.django_db
class TestAutoResolve:
    def test_recording_the_payment_resolves_the_claim(self, client):
        loan, installment = _loan_and_installment()
        finance = make_staff_user("FINANCE_OFFICER")
        client.force_login(loan.customer)
        post_json(client, claim_url(installment.pk), {})

        services.record_payment(
            loan,
            amount=Decimal("500.00"),
            payment_date=date(2026, 7, 20),
            payment_method="MOBILE_MONEY",
            recorded_by=finance,
        )

        claim = PaymentClaim.objects.get()
        assert claim.status == PaymentClaim.Status.RESOLVED
        assert claim.resolved_by == finance
        assert claim.resolved_at is not None

    def test_partial_payment_leaves_the_claim_pending(self, client):
        loan, installment = _loan_and_installment()
        client.force_login(loan.customer)
        post_json(client, claim_url(installment.pk), {})

        services.record_payment(
            loan,
            amount=Decimal("100.00"),
            payment_date=date(2026, 7, 20),
            payment_method="MOBILE_MONEY",
            recorded_by=make_staff_user("FINANCE_OFFICER"),
        )

        assert PaymentClaim.objects.get().status == PaymentClaim.Status.PENDING
