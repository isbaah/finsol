import json
from datetime import date
from decimal import Decimal

import pytest

from apps.audit.models import AuditEvent
from apps.repayments.models import Payment
from tests.factories import make_active_loan, make_staff_user, make_user


def post_json(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


def repayments_url(loan_id) -> str:
    return f"/api/v1/admin/loans/{loan_id}/repayments/"


def reverse_url(payment_id) -> str:
    return f"/api/v1/admin/repayments/{payment_id}/reverse/"


def _loan(**overrides):
    return make_active_loan(
        principal=Decimal("1000.00"),
        total_interest=Decimal("0.00"),
        installment_count=1,
        first_due_date=date(2027, 1, 1),
        **overrides,
    )


def _payload(**overrides):
    payload = {
        "amount": "300.00",
        "payment_date": "2026-07-20",
        "payment_method": Payment.Method.CASH,
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
class TestRecordPaymentApi:
    def test_unauthenticated_is_rejected(self, client):
        loan = _loan()
        response = post_json(client, repayments_url(loan.pk), _payload())
        assert response.status_code in (401, 403)

    @pytest.mark.parametrize("role", ["LOAN_OFFICER", "APPROVER", "AUDITOR"])
    def test_non_finance_roles_are_rejected(self, client, role):
        loan = _loan()
        client.force_login(make_staff_user(role))
        response = post_json(client, repayments_url(loan.pk), _payload())
        assert response.status_code == 403

    def test_finance_officer_can_record_a_payment(self, client):
        loan = _loan()
        client.force_login(make_staff_user("FINANCE_OFFICER"))

        response = post_json(client, repayments_url(loan.pk), _payload())

        assert response.status_code == 201
        body = response.json()
        assert body["receipt_number"].startswith("RCT-")
        assert body["status"] == Payment.Status.POSTED
        assert AuditEvent.objects.filter(action="payment.record").exists()

    def test_overpayment_returns_409(self, client):
        loan = _loan()
        client.force_login(make_staff_user("FINANCE_OFFICER"))

        response = post_json(client, repayments_url(loan.pk), _payload(amount="1000.01"))

        assert response.status_code == 409

    def test_duplicate_idempotency_key_returns_409_not_a_second_payment(self, client):
        loan = _loan()
        client.force_login(make_staff_user("FINANCE_OFFICER"))
        payload = _payload(idempotency_key="click-1")

        first = post_json(client, repayments_url(loan.pk), payload)
        second = post_json(client, repayments_url(loan.pk), payload)

        assert first.status_code == 201
        assert second.status_code == 409
        assert loan.payments.count() == 1

    def test_staff_can_list_payment_history(self, client):
        loan = _loan()
        client.force_login(make_staff_user("FINANCE_OFFICER"))
        post_json(client, repayments_url(loan.pk), _payload())

        response = client.get(repayments_url(loan.pk))

        assert response.status_code == 200
        body = response.json()
        results = body["results"] if isinstance(body, dict) and "results" in body else body
        assert len(results) == 1
        assert results[0]["amount"] == "300.00"

    def test_auditor_can_read_but_not_write(self, client):
        loan = _loan()
        client.force_login(make_staff_user("AUDITOR"))

        response = client.get(repayments_url(loan.pk))

        assert response.status_code == 200


@pytest.mark.django_db
class TestReversePaymentApi:
    def _posted_payment(self, client):
        loan = _loan()
        client.force_login(make_staff_user("FINANCE_OFFICER"))
        response = post_json(client, repayments_url(loan.pk), _payload())
        return loan, response.json()["id"]

    def test_finance_officer_can_reverse_with_a_reason(self, client):
        loan, payment_id = self._posted_payment(client)

        response = post_json(client, reverse_url(payment_id), {"reason": "Wrong loan"})

        assert response.status_code == 200
        assert response.json()["status"] == Payment.Status.REVERSED
        loan.refresh_from_db()
        assert loan.outstanding_balance == Decimal("1000.00")

    def test_reversal_without_a_reason_is_rejected(self, client):
        _, payment_id = self._posted_payment(client)
        client.force_login(make_staff_user("FINANCE_OFFICER"))

        response = post_json(client, reverse_url(payment_id), {"reason": ""})

        assert response.status_code == 400

    def test_approver_cannot_reverse_a_payment(self, client):
        _, payment_id = self._posted_payment(client)
        client.force_login(make_staff_user("APPROVER"))

        response = post_json(client, reverse_url(payment_id), {"reason": "Test"})

        assert response.status_code == 403

    def test_customer_cannot_reach_the_reverse_endpoint(self, client):
        _, payment_id = self._posted_payment(client)
        client.force_login(make_user())

        response = post_json(client, reverse_url(payment_id), {"reason": "Test"})

        assert response.status_code == 403
