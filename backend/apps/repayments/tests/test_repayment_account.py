"""The company repayment-collection account: super-admin-managed, readable
by every signed-in customer (they need the full details to pay into it)."""

import json

import pytest

from apps.audit.models import AuditEvent
from apps.repayments.models import RepaymentAccount
from tests.factories import make_staff_user, make_user

CUSTOMER_URL = "/api/v1/repayment-account/"
ADMIN_URL = "/api/v1/admin/repayment-account/"

DETAILS = {
    "mobile_money_network": "MTN",
    "mobile_money_number": "0551234567",
    "mobile_money_account_name": "Finsol Ltd",
    "bank_name": "GCB Bank",
    "bank_account_name": "Finsol Ltd",
    "bank_account_number": "9876543210",
    "payment_instructions": "Use your loan number as the payment reference.",
}


def put_json(client, url, payload):
    return client.put(url, data=json.dumps(payload), content_type="application/json")


@pytest.mark.django_db
class TestRepaymentAccount:
    def test_unauthenticated_is_rejected(self, client):
        assert client.get(CUSTOMER_URL).status_code in (401, 403)

    def test_customer_reads_full_unmasked_details(self, client):
        RepaymentAccount.get_solo()
        RepaymentAccount.objects.update(**DETAILS)
        client.force_login(make_user())

        response = client.get(CUSTOMER_URL)

        assert response.status_code == 200
        body = response.json()
        assert body["mobile_money_number"] == "0551234567"
        assert body["bank_account_number"] == "9876543210"

    def test_super_admin_can_update_and_it_is_audited(self, client):
        client.force_login(make_staff_user("SUPER_ADMIN"))

        response = put_json(client, ADMIN_URL, DETAILS)

        assert response.status_code == 200
        assert RepaymentAccount.get_solo().mobile_money_number == "0551234567"
        assert AuditEvent.objects.filter(action="repayment_account.update").exists()

    def test_other_staff_can_read_but_not_update(self, client):
        client.force_login(make_staff_user("LOAN_OFFICER"))

        assert client.get(ADMIN_URL).status_code == 200
        assert put_json(client, ADMIN_URL, DETAILS).status_code == 403

    def test_customer_cannot_use_the_admin_endpoint(self, client):
        client.force_login(make_user())
        assert client.get(ADMIN_URL).status_code == 403
        assert put_json(client, ADMIN_URL, DETAILS).status_code == 403

    def test_singleton_never_duplicates(self, client):
        first = RepaymentAccount.get_solo()
        second = RepaymentAccount.get_solo()
        assert first.pk == second.pk
        assert RepaymentAccount.objects.count() == 1
