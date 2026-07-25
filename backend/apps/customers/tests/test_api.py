import json

import pytest
from django.contrib.auth.models import Group

from apps.accounts.models import User
from apps.customers.models import CustomerProfile
from common.permissions import STAFF_ROLES

PROFILE_URL = "/api/v1/profile/"
CUSTOMERS_URL = "/api/v1/customers/"


def customer_detail_url(profile_id) -> str:
    return f"/api/v1/customers/{profile_id}/"


def put_json(client, url, payload):
    return client.put(url, data=json.dumps(payload), content_type="application/json")


def make_user(email="customer@example.com") -> User:
    return User.objects.create_user(email=email, password="s3cret-pass")  # nosec


def make_staff_user(role: str, email: str | None = None) -> User:
    user = make_user(email or f"{role.lower()}@example.com")
    group, _ = Group.objects.get_or_create(name=role)
    user.groups.add(group)
    return user


VALID_MOBILE_MONEY_PAYLOAD = {
    "first_name": "Ama",
    "last_name": "Owusu",
    "phone_number_e164": "0241234567",
    "address_line_1": "12 Ring Road",
    "city": "Accra",
    "preferred_disbursement_method": "MOBILE_MONEY",
    "mobile_money_network": "MTN",
    "mobile_money_number": "0241234567",
}

VALID_BANK_PAYLOAD = {
    "first_name": "Ama",
    "last_name": "Owusu",
    "phone_number_e164": "0201234567",
    "preferred_disbursement_method": "BANK",
    "bank_name": "GCB Bank",
    "bank_account_name": "Ama Owusu",
    "bank_account_number": "1234567890",
}


@pytest.mark.django_db
class TestProfileValidation:
    def test_get_returns_404_before_onboarding(self, client):
        client.force_login(make_user())

        response = client.get(PROFILE_URL)

        assert response.status_code == 404
        assert response.json()["code"] == "profile_not_found"

    def test_put_normalizes_local_phone_number_to_e164(self, client):
        client.force_login(make_user())

        response = put_json(client, PROFILE_URL, VALID_MOBILE_MONEY_PAYLOAD)

        assert response.status_code == 201
        assert response.json()["phone_number_e164"] == "+233241234567"
        assert response.json()["phone_country_code"] == "233"
        assert response.json()["profile_completed_at"] is not None

    def test_put_rejects_invalid_phone_number(self, client):
        client.force_login(make_user())

        response = put_json(
            client, PROFILE_URL, {**VALID_MOBILE_MONEY_PAYLOAD, "phone_number_e164": "123"}
        )

        assert response.status_code == 400
        assert "phone_number_e164" in response.json()

    def test_put_requires_mobile_money_fields_for_that_method(self, client):
        client.force_login(make_user())
        payload = {**VALID_MOBILE_MONEY_PAYLOAD}
        del payload["mobile_money_number"]

        response = put_json(client, PROFILE_URL, payload)

        assert response.status_code == 400
        assert "mobile_money_number" in response.json()

    def test_put_requires_bank_fields_for_that_method(self, client):
        client.force_login(make_user())
        payload = {**VALID_BANK_PAYLOAD}
        del payload["bank_account_number"]

        response = put_json(client, PROFILE_URL, payload)

        assert response.status_code == 400
        assert "bank_account_number" in response.json()

    def test_put_accepts_valid_bank_profile(self, client):
        client.force_login(make_user())

        response = put_json(client, PROFILE_URL, VALID_BANK_PAYLOAD)

        assert response.status_code == 201
        assert response.json()["bank_account_number"] == "1234567890"

    def test_put_requires_first_and_last_name(self, client):
        client.force_login(make_user())
        payload = {**VALID_MOBILE_MONEY_PAYLOAD}
        del payload["first_name"]
        del payload["last_name"]

        response = put_json(client, PROFILE_URL, payload)

        assert response.status_code == 400
        assert "first_name" in response.json()
        assert "last_name" in response.json()

    def test_put_stores_names_on_the_user_row(self, client):
        user = make_user()
        client.force_login(user)

        response = put_json(client, PROFILE_URL, VALID_MOBILE_MONEY_PAYLOAD)

        assert response.status_code == 201
        assert response.json()["first_name"] == "Ama"
        assert response.json()["last_name"] == "Owusu"
        user.refresh_from_db()
        assert user.get_full_name() == "Ama Owusu"

    def test_second_put_updates_existing_profile_returns_200(self, client):
        client.force_login(make_user())
        put_json(client, PROFILE_URL, VALID_MOBILE_MONEY_PAYLOAD)

        response = put_json(client, PROFILE_URL, {**VALID_MOBILE_MONEY_PAYLOAD, "city": "Kumasi"})

        assert response.status_code == 200
        assert response.json()["city"] == "Kumasi"
        assert CustomerProfile.objects.count() == 1


@pytest.mark.django_db
class TestOwnershipIsolation:
    def test_customer_never_sees_another_customers_profile(self, client):
        client.force_login(make_user("owner@example.com"))
        put_json(client, PROFILE_URL, VALID_MOBILE_MONEY_PAYLOAD)
        client.logout()

        client.force_login(make_user("other@example.com"))
        response = client.get(PROFILE_URL)

        assert response.status_code == 404

    def test_customer_cannot_reach_the_staff_customer_list(self, client):
        client.force_login(make_user())

        response = client.get(CUSTOMERS_URL)

        assert response.status_code == 403

    def test_customer_cannot_reach_the_staff_customer_detail(self, client):
        owner = make_user("owner2@example.com")
        client.force_login(owner)
        put_json(client, PROFILE_URL, VALID_MOBILE_MONEY_PAYLOAD)
        profile_id = owner.customer_profile.id

        response = client.get(customer_detail_url(profile_id))

        assert response.status_code == 403


@pytest.mark.django_db
class TestRoleMatrix:
    def test_unauthenticated_request_is_rejected(self, client):
        response = client.get(CUSTOMERS_URL)

        assert response.status_code == 401

    @pytest.mark.parametrize("role", STAFF_ROLES)
    def test_every_staff_role_can_list_customers(self, client, role):
        client.force_login(make_staff_user(role))

        response = client.get(CUSTOMERS_URL)

        assert response.status_code == 200

    def test_django_superuser_without_a_business_role_is_still_rejected(self, client):
        # Section 10: is_superuser is a technical-admin flag, not a business
        # role shortcut — it must not silently satisfy has_any_role checks.
        admin = User.objects.create_superuser(email="admin@example.com", password="s3cret-pass")  # nosec
        client.force_login(admin)

        response = client.get(CUSTOMERS_URL)

        assert response.status_code == 403


@pytest.mark.django_db
class TestMaskingAndUnauthorisedReveal:
    def _create_profile_for(self, client, email) -> CustomerProfile:
        client.force_login(make_user(email))
        put_json(client, PROFILE_URL, VALID_MOBILE_MONEY_PAYLOAD)
        client.logout()
        return CustomerProfile.objects.get(user__email=email)

    def test_staff_list_never_exposes_full_mobile_money_number(self, client):
        self._create_profile_for(client, "masked1@example.com")
        client.force_login(make_staff_user("SUPER_ADMIN", "admin-viewer@example.com"))

        response = client.get(CUSTOMERS_URL)

        body = response.json()
        numbers = [row["mobile_money_number"] for row in body["results"]]
        assert all(not n.endswith("0241234567") for n in numbers)
        assert all(n == "•••• 4567" for n in numbers)

    def test_staff_detail_never_exposes_full_mobile_money_number(self, client):
        profile = self._create_profile_for(client, "masked2@example.com")
        client.force_login(make_staff_user("FINANCE_OFFICER", "finance-viewer@example.com"))

        response = client.get(customer_detail_url(profile.id))

        assert response.json()["mobile_money_number"] == "•••• 4567"

    def test_staff_detail_response_contains_no_raw_account_number_anywhere(self, client):
        # Belt-and-suspenders: even if a future field were added, the raw
        # digits collected for this profile must never appear verbatim.
        profile = self._create_profile_for(client, "masked3@example.com")
        client.force_login(make_staff_user("AUDITOR", "auditor-viewer@example.com"))

        response = client.get(customer_detail_url(profile.id))

        assert "0241234567" not in response.content.decode()

    def test_no_query_parameter_bypasses_masking(self, client):
        profile = self._create_profile_for(client, "masked4@example.com")
        client.force_login(make_staff_user("SUPER_ADMIN", "super-viewer@example.com"))

        response = client.get(f"{customer_detail_url(profile.id)}?reveal=true")

        assert response.json()["mobile_money_number"] == "•••• 4567"

    def test_customers_own_profile_view_shows_full_number_to_themselves(self, client):
        client.force_login(make_user("self-view@example.com"))
        put_json(client, PROFILE_URL, VALID_MOBILE_MONEY_PAYLOAD)

        response = client.get(PROFILE_URL)

        assert response.json()["mobile_money_number"] == "0241234567"
