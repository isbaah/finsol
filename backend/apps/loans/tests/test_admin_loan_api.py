import json
from decimal import Decimal

import pytest

from apps.audit.models import AuditEvent
from apps.loans.models import Disbursement, Loan, RepaymentInstallment
from apps.repayments.models import LoanTransaction
from tests.factories import make_loan, make_staff_user, make_user

Status = Loan.Status


def post_json(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


def list_url() -> str:
    return "/api/v1/admin/loans/"


def detail_url(loan_id) -> str:
    return f"/api/v1/admin/loans/{loan_id}/"


def approve_url(loan_id) -> str:
    return f"/api/v1/admin/loans/{loan_id}/approve/"


def disburse_url(loan_id) -> str:
    return f"/api/v1/admin/loans/{loan_id}/disburse/"


def payout_details_url(loan_id) -> str:
    return f"/api/v1/admin/loans/{loan_id}/payout-details/"


@pytest.mark.django_db
class TestAdminLoanVisibility:
    def test_unauthenticated_is_rejected(self, client):
        loan = make_loan()

        assert client.get(list_url()).status_code == 401
        assert client.get(detail_url(loan.pk)).status_code == 401

    def test_customer_cannot_view_admin_loan_list(self, client):
        client.force_login(make_user())

        response = client.get(list_url())

        assert response.status_code == 403

    @pytest.mark.parametrize(
        "role", ["LOAN_OFFICER", "APPROVER", "FINANCE_OFFICER", "AUDITOR", "SUPER_ADMIN"]
    )
    def test_every_staff_role_can_view(self, client, role):
        loan = make_loan()
        client.force_login(make_staff_user(role))

        list_response = client.get(list_url())
        detail_response = client.get(detail_url(loan.pk))

        assert list_response.status_code == 200
        assert detail_response.status_code == 200
        assert detail_response.json()["loan_number"] == loan.loan_number


@pytest.mark.django_db
class TestApproveLoan:
    def test_approver_can_approve(self, client):
        loan = make_loan()
        client.force_login(make_staff_user("APPROVER"))

        response = client.post(approve_url(loan.pk))

        assert response.status_code == 200
        assert response.json()["status"] == Status.APPROVED_FOR_DISBURSEMENT

    def test_super_admin_can_approve(self, client):
        loan = make_loan()
        client.force_login(make_staff_user("SUPER_ADMIN"))

        response = client.post(approve_url(loan.pk))

        assert response.status_code == 200

    @pytest.mark.parametrize("role", ["LOAN_OFFICER", "FINANCE_OFFICER", "AUDITOR"])
    def test_other_staff_roles_cannot_approve(self, client, role):
        loan = make_loan()
        client.force_login(make_staff_user(role))

        response = client.post(approve_url(loan.pk))

        assert response.status_code == 403

    def test_cannot_approve_twice(self, client):
        loan = make_loan()
        client.force_login(make_staff_user("APPROVER"))
        first = client.post(approve_url(loan.pk))
        assert first.status_code == 200

        second = client.post(approve_url(loan.pk))

        assert second.status_code == 409


@pytest.mark.django_db
class TestDisburseLoan:
    def _approved_loan(self):
        loan = make_loan()
        from apps.loans import services

        return services.approve_loan(loan, approver=make_staff_user("APPROVER"))

    def _payload(self, loan, **overrides):
        payload = {
            "amount": str(loan.principal),
            "method": Disbursement.Method.MOBILE_MONEY,
            "external_transaction_reference": "",
            "notes": "",
        }
        payload.update(overrides)
        return payload

    def test_finance_officer_can_disburse(self, client):
        loan = self._approved_loan()
        client.force_login(make_staff_user("FINANCE_OFFICER"))

        response = post_json(client, disburse_url(loan.pk), self._payload(loan))

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == Status.ACTIVE
        assert body["disbursement"]["amount"] == str(loan.principal)

    @pytest.mark.parametrize("role", ["LOAN_OFFICER", "APPROVER", "AUDITOR"])
    def test_other_staff_roles_cannot_disburse(self, client, role):
        loan = self._approved_loan()
        client.force_login(make_staff_user(role))

        response = post_json(client, disburse_url(loan.pk), self._payload(loan))

        assert response.status_code == 403

    def test_cannot_disburse_before_approval(self, client):
        loan = make_loan()
        client.force_login(make_staff_user("FINANCE_OFFICER"))

        response = post_json(client, disburse_url(loan.pk), self._payload(loan))

        assert response.status_code == 409

    def test_amount_mismatch_is_rejected(self, client):
        loan = self._approved_loan()
        client.force_login(make_staff_user("FINANCE_OFFICER"))

        response = post_json(
            client,
            disburse_url(loan.pk),
            self._payload(loan, amount=str(loan.principal + Decimal("1.00"))),
        )

        assert response.status_code == 409
        loan.refresh_from_db()
        assert loan.status == Status.APPROVED_FOR_DISBURSEMENT

    def test_duplicate_disbursement_is_rejected(self, client):
        loan = self._approved_loan()
        client.force_login(make_staff_user("FINANCE_OFFICER"))
        first = post_json(client, disburse_url(loan.pk), self._payload(loan))
        assert first.status_code == 200

        second = post_json(client, disburse_url(loan.pk), self._payload(loan))

        assert second.status_code == 409
        assert Disbursement.objects.filter(loan=loan).count() == 1

    def test_duplicate_external_reference_is_rejected(self, client):
        loan_a = self._approved_loan()
        loan_b = self._approved_loan()
        client.force_login(make_staff_user("FINANCE_OFFICER"))
        first = post_json(
            client,
            disburse_url(loan_a.pk),
            self._payload(loan_a, external_transaction_reference="DUP-1"),
        )
        assert first.status_code == 200

        second = post_json(
            client,
            disburse_url(loan_b.pk),
            self._payload(loan_b, external_transaction_reference="DUP-1"),
        )

        assert second.status_code == 409
        assert not Disbursement.objects.filter(loan=loan_b).exists()

    def test_schedule_is_copied_from_the_accepted_offer(self, client):
        loan = self._approved_loan()
        client.force_login(make_staff_user("FINANCE_OFFICER"))

        response = post_json(client, disburse_url(loan.pk), self._payload(loan))

        assert response.status_code == 200
        offer_installments = list(loan.accepted_offer.installments.order_by("sequence_number"))
        repayment_installments = list(
            RepaymentInstallment.objects.filter(loan=loan).order_by("sequence_number")
        )
        assert len(repayment_installments) == len(offer_installments)
        for offer_row, repayment_row in zip(
            offer_installments, repayment_installments, strict=True
        ):
            assert repayment_row.total_due == offer_row.total_due
            assert repayment_row.due_date == offer_row.due_date
            assert repayment_row.status == RepaymentInstallment.Status.UPCOMING

    def test_ledger_entry_is_posted_without_changing_outstanding_balance(self, client):
        loan = self._approved_loan()
        balance_before = loan.outstanding_balance
        client.force_login(make_staff_user("FINANCE_OFFICER"))

        response = post_json(client, disburse_url(loan.pk), self._payload(loan))

        assert response.status_code == 200
        loan.refresh_from_db()
        entry = LoanTransaction.objects.get(
            loan=loan, transaction_type=LoanTransaction.TransactionType.DISBURSEMENT
        )
        assert entry.amount == loan.principal
        assert entry.balance_after == balance_before
        assert loan.outstanding_balance == balance_before
        assert loan.outstanding_balance == loan.total_repayable


@pytest.mark.django_db
class TestPayoutDetailsReveal:
    def test_finance_officer_can_reveal(self, client):
        loan = make_loan()
        client.force_login(make_staff_user("FINANCE_OFFICER"))

        response = client.get(payout_details_url(loan.pk))

        assert response.status_code == 200
        assert response.json()["mobile_money_number"] == "0241234567"

    @pytest.mark.parametrize("role", ["LOAN_OFFICER", "APPROVER", "AUDITOR"])
    def test_other_staff_roles_cannot_reveal(self, client, role):
        loan = make_loan()
        client.force_login(make_staff_user(role))

        response = client.get(payout_details_url(loan.pk))

        assert response.status_code == 403

    def test_reveal_is_audited_without_raw_digits(self, client):
        loan = make_loan()
        client.force_login(make_staff_user("FINANCE_OFFICER"))

        client.get(payout_details_url(loan.pk))

        event = AuditEvent.objects.get(action="customer_profile.payout_details_reveal")
        assert "0241234567" not in json.dumps(event.after)


@pytest.mark.django_db
class TestCustomerLoanDetail:
    def customer_url(self, loan_id) -> str:
        return f"/api/v1/customer/loans/{loan_id}/"

    def test_owner_can_view_their_loan(self, client):
        loan = make_loan()
        client.force_login(loan.customer)

        response = client.get(self.customer_url(loan.pk))

        assert response.status_code == 200
        assert response.json()["loan_number"] == loan.loan_number

    def test_non_owner_cannot_view(self, client):
        loan = make_loan()
        client.force_login(make_user())

        response = client.get(self.customer_url(loan.pk))

        assert response.status_code == 403
