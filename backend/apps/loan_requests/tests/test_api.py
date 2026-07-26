import json

import pytest

from apps.loan_requests.models import LoanRequest
from tests.factories import make_customer_profile, make_loan_request, make_staff_user, make_user

Status = LoanRequest.Status
LIST_CREATE_URL = "/api/v1/customer/loan-requests/"
ADMIN_LIST_URL = "/api/v1/admin/loan-requests/"

VALID_PAYLOAD = {
    "requested_amount": "2500.00",
    "purpose": "School fees",
    "requested_term_count": 6,
    "requested_term_unit": "MONTH",
}


def detail_url(pk) -> str:
    return f"/api/v1/customer/loan-requests/{pk}/"


def cancel_url(pk) -> str:
    return f"/api/v1/customer/loan-requests/{pk}/cancel/"


def admin_detail_url(pk) -> str:
    return f"/api/v1/admin/loan-requests/{pk}/"


def start_review_url(pk) -> str:
    return f"/api/v1/admin/loan-requests/{pk}/start-review/"


def decline_url(pk) -> str:
    return f"/api/v1/admin/loan-requests/{pk}/decline/"


def post_json(client, url, payload):
    return client.post(url, data=json.dumps(payload), content_type="application/json")


@pytest.mark.django_db
class TestCreateEligibility:
    def test_unauthenticated_is_rejected(self, client):
        response = post_json(client, LIST_CREATE_URL, VALID_PAYLOAD)

        assert response.status_code == 401

    def test_unverified_email_is_rejected(self, client):
        # A profile exists and is complete, but the email verification flag
        # is deliberately left false — reproduces the exact gap the
        # createsuperuser/create_super_admin fix closed for staff accounts.
        user = make_user()
        profile = make_customer_profile(user)
        from allauth.account.models import EmailAddress

        EmailAddress.objects.filter(user=user).update(verified=False)
        client.force_login(user)

        response = post_json(client, LIST_CREATE_URL, VALID_PAYLOAD)

        assert response.status_code == 403
        assert profile.user_id == user.id  # sanity: profile really was set up

    def test_no_profile_is_rejected(self, client):
        client.force_login(make_user())

        response = post_json(client, LIST_CREATE_URL, VALID_PAYLOAD)

        assert response.status_code == 403

    def test_incomplete_profile_is_rejected(self, client):
        user = make_user()
        make_customer_profile(user, completed=False)
        client.force_login(user)

        response = post_json(client, LIST_CREATE_URL, VALID_PAYLOAD)

        assert response.status_code == 403

    def test_eligible_customer_can_submit(self, client):
        user = make_user()
        make_customer_profile(user)
        client.force_login(user)

        response = post_json(client, LIST_CREATE_URL, VALID_PAYLOAD)

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == Status.SUBMITTED
        assert body["request_number"].startswith("REQ-")
        assert LoanRequest.objects.get(pk=body["id"]).payout_snapshot["method"] == "MOBILE_MONEY"


@pytest.mark.django_db
class TestCreateValidation:
    def test_negative_amount_is_rejected(self, client):
        user = make_user()
        make_customer_profile(user)
        client.force_login(user)

        response = post_json(client, LIST_CREATE_URL, {**VALID_PAYLOAD, "requested_amount": "-1"})

        assert response.status_code == 400

    def test_missing_purpose_is_rejected(self, client):
        user = make_user()
        make_customer_profile(user)
        client.force_login(user)

        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "purpose"}
        response = post_json(client, LIST_CREATE_URL, payload)

        assert response.status_code == 400


@pytest.mark.django_db
class TestDuplicateSubmitProtection:
    @pytest.mark.parametrize(
        "existing_status",
        [Status.SUBMITTED, Status.UNDER_REVIEW, Status.OFFER_SENT, Status.REVISION_REQUESTED],
    )
    def test_second_submission_blocked_while_one_is_in_flight(self, client, existing_status):
        user = make_user()
        make_customer_profile(user)
        make_loan_request(user, status=existing_status)
        client.force_login(user)

        response = post_json(client, LIST_CREATE_URL, VALID_PAYLOAD)

        assert response.status_code == 400

    @pytest.mark.parametrize(
        "terminal_status", [Status.DECLINED, Status.CANCELLED, Status.CUSTOMER_REJECTED]
    )
    def test_new_submission_allowed_once_previous_is_terminal(self, client, terminal_status):
        user = make_user()
        make_customer_profile(user)
        make_loan_request(user, status=terminal_status)
        client.force_login(user)

        response = post_json(client, LIST_CREATE_URL, VALID_PAYLOAD)

        assert response.status_code == 201


@pytest.mark.django_db
class TestCustomerOwnership:
    def test_list_only_shows_own_requests(self, client):
        mine = make_user()
        my_request = make_loan_request(mine)
        make_loan_request(make_user())  # someone else's
        client.force_login(mine)

        response = client.get(LIST_CREATE_URL)

        body = response.json()
        assert body["count"] == 1
        assert body["results"][0]["request_number"] == my_request.request_number

    def test_owner_can_view_own_request_detail(self, client):
        owner = make_user()
        loan_request = make_loan_request(owner)
        client.force_login(owner)

        response = client.get(detail_url(loan_request.pk))

        assert response.status_code == 200
        assert response.json()["request_number"] == loan_request.request_number

    def test_non_owner_cannot_view_someone_elses_request(self, client):
        loan_request = make_loan_request(make_user())
        client.force_login(make_user())

        response = client.get(detail_url(loan_request.pk))

        assert response.status_code == 403

    def test_status_timeline_reflects_service_layer_transitions(self, client):
        owner = make_user()
        loan_request = make_loan_request(owner, status=Status.SUBMITTED)
        client.force_login(owner)

        from apps.loan_requests import services

        services.start_review(loan_request, officer=make_staff_user("LOAN_OFFICER"))

        response = client.get(detail_url(loan_request.pk))

        assert response.json()["status"] == Status.UNDER_REVIEW


@pytest.mark.django_db
class TestCancel:
    def test_owner_can_cancel_a_submitted_request(self, client):
        owner = make_user()
        loan_request = make_loan_request(owner, status=Status.SUBMITTED)
        client.force_login(owner)

        response = client.post(cancel_url(loan_request.pk))

        assert response.status_code == 200
        assert response.json()["status"] == Status.CANCELLED

    def test_cannot_cancel_after_offer_sent(self, client):
        owner = make_user()
        loan_request = make_loan_request(owner, status=Status.OFFER_SENT)
        client.force_login(owner)

        response = client.post(cancel_url(loan_request.pk))

        assert response.status_code == 409

    def test_non_owner_cannot_cancel(self, client):
        loan_request = make_loan_request(make_user(), status=Status.SUBMITTED)
        client.force_login(make_user())

        response = client.post(cancel_url(loan_request.pk))

        assert response.status_code == 403


@pytest.mark.django_db
class TestAdminQueue:
    def test_customer_is_rejected(self, client):
        client.force_login(make_user())

        response = client.get(ADMIN_LIST_URL)

        assert response.status_code == 403

    def test_staff_sees_the_new_request(self, client):
        loan_request = make_loan_request(make_user())
        client.force_login(make_staff_user("LOAN_OFFICER"))

        response = client.get(ADMIN_LIST_URL)

        assert response.status_code == 200
        numbers = [row["request_number"] for row in response.json()["results"]]
        assert loan_request.request_number in numbers

    def test_filter_by_status(self, client):
        make_loan_request(make_user(), status=Status.SUBMITTED)
        make_loan_request(make_user(), status=Status.DECLINED)
        client.force_login(make_staff_user("LOAN_OFFICER"))

        response = client.get(ADMIN_LIST_URL, {"status": Status.DECLINED})

        results = response.json()["results"]
        assert all(row["status"] == Status.DECLINED for row in results)
        assert len(results) == 1

    def test_search_by_request_number(self, client):
        loan_request = make_loan_request(make_user())
        make_loan_request(make_user())
        client.force_login(make_staff_user("LOAN_OFFICER"))

        response = client.get(ADMIN_LIST_URL, {"search": loan_request.request_number})

        results = response.json()["results"]
        assert len(results) == 1
        assert results[0]["request_number"] == loan_request.request_number

    def test_list_includes_the_preferred_term(self, client):
        loan_request = make_loan_request(
            make_user(), requested_term_count=9, requested_term_unit="MONTH"
        )
        client.force_login(make_staff_user("LOAN_OFFICER"))

        response = client.get(ADMIN_LIST_URL)

        results = response.json()["results"]
        row = next(
            r for r in results if r["request_number"] == loan_request.request_number
        )
        assert row["requested_term_count"] == 9
        assert row["requested_term_unit"] == "MONTH"

    def test_detail_includes_offer_history(self, client):
        from tests.factories import make_offer

        loan_request = make_loan_request(make_user(), status=Status.UNDER_REVIEW)
        make_offer(loan_request, version_number=1)
        client.force_login(make_staff_user("LOAN_OFFICER"))

        response = client.get(admin_detail_url(loan_request.pk))

        assert response.status_code == 200
        assert len(response.json()["offers"]) == 1


@pytest.mark.django_db
class TestAdminTransitions:
    def test_start_review_assigns_the_calling_officer(self, client):
        loan_request = make_loan_request(make_user(), status=Status.SUBMITTED)
        officer = make_staff_user("LOAN_OFFICER")
        client.force_login(officer)

        response = client.post(start_review_url(loan_request.pk))

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == Status.UNDER_REVIEW
        assert body["assigned_to_name"] == officer.get_full_name()

    def test_start_review_twice_is_a_conflict_not_a_500(self, client):
        loan_request = make_loan_request(make_user(), status=Status.UNDER_REVIEW)
        client.force_login(make_staff_user("LOAN_OFFICER"))

        response = client.post(start_review_url(loan_request.pk))

        assert response.status_code == 409

    def test_decline_requires_a_reason(self, client):
        loan_request = make_loan_request(make_user(), status=Status.SUBMITTED)
        client.force_login(make_staff_user("LOAN_OFFICER"))

        response = post_json(client, decline_url(loan_request.pk), {})

        assert response.status_code == 400

    def test_decline_with_reason_succeeds(self, client):
        loan_request = make_loan_request(make_user(), status=Status.SUBMITTED)
        client.force_login(make_staff_user("LOAN_OFFICER"))

        response = post_json(client, decline_url(loan_request.pk), {"reason": "Insufficient info"})

        assert response.status_code == 200
        assert response.json()["status"] == Status.DECLINED

    def test_customer_cannot_start_review(self, client):
        loan_request = make_loan_request(make_user(), status=Status.SUBMITTED)
        client.force_login(make_user())

        response = client.post(start_review_url(loan_request.pk))

        assert response.status_code == 403
