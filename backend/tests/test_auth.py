import json
import re
from urllib.parse import parse_qs, urlparse

import pytest

from apps.accounts.models import User

SIGNUP_URL = "/_allauth/browser/v1/auth/signup"
LOGIN_URL = "/_allauth/browser/v1/auth/login"
SESSION_URL = "/_allauth/browser/v1/auth/session"
VERIFY_EMAIL_URL = "/_allauth/browser/v1/auth/email/verify"
REQUEST_RESET_URL = "/_allauth/browser/v1/auth/password/request"
RESET_PASSWORD_URL = "/_allauth/browser/v1/auth/password/reset"
PROVIDER_REDIRECT_URL = "/_allauth/browser/v1/auth/provider/redirect"
ME_URL = "/api/v1/me/"

STRONG_PASSWORD = "a-very-strong-pass-1"  # nosec


def post_json(client, url, payload, **kwargs):
    return client.post(url, data=json.dumps(payload), content_type="application/json", **kwargs)


def extract_key_from_email(body: str) -> str:
    match = re.search(r"https?://\S+", body)
    assert match, f"no link found in email body: {body}"
    url = match.group(0)
    qs = parse_qs(urlparse(url).query)
    assert "key" in qs, f"no key query param in {url}"
    return qs["key"][0]


def signup_and_verify(client, mailoutbox, email):
    post_json(client, SIGNUP_URL, {"email": email, "password": STRONG_PASSWORD})
    key = extract_key_from_email(mailoutbox[-1].body)
    post_json(client, VERIFY_EMAIL_URL, {"key": key})
    client.logout()


@pytest.mark.django_db
class TestSignup:
    def test_signup_creates_user_pending_email_verification(self, client):
        response = post_json(
            client, SIGNUP_URL, {"email": "new.customer@example.com", "password": STRONG_PASSWORD}
        )

        assert response.status_code == 401
        body = response.json()
        assert body["meta"]["is_authenticated"] is False
        flow_ids = {flow["id"] for flow in body["data"]["flows"]}
        assert "verify_email" in flow_ids
        pending = next(f for f in body["data"]["flows"] if f["id"] == "verify_email")
        assert pending["is_pending"] is True

        user = User.objects.get(email="new.customer@example.com")
        assert user.check_password(STRONG_PASSWORD)

    def test_signup_sends_one_verification_email(self, client, mailoutbox):
        post_json(
            client, SIGNUP_URL, {"email": "mail.check@example.com", "password": STRONG_PASSWORD}
        )

        assert len(mailoutbox) == 1
        assert "mail.check@example.com" in mailoutbox[0].to
        assert "/auth/verify-email?key=" in mailoutbox[0].body

    def test_duplicate_signup_resends_verification_without_creating_second_user(
        self, client, mailoutbox
    ):
        """Re-submitting signup for an already-pending email is how a user
        recovers a lost verification link in link-based mode (there is no
        separate resend endpoint for link mode — /email/verify/resend is
        code-mode only, see ResendEmailVerificationCodeView). This also
        doubles as allauth's anti-enumeration behavior: a second signup for
        an existing, already-verified email returns the same generic
        pending-style response rather than a "this email is taken" error
        that would let an attacker probe which emails are registered.
        """
        post_json(client, SIGNUP_URL, {"email": "dupe@example.com", "password": STRONG_PASSWORD})
        response = post_json(
            client, SIGNUP_URL, {"email": "DUPE@example.com", "password": "another-strong-pass-2"}
        )

        assert response.status_code == 401
        assert User.objects.filter(email__iexact="dupe@example.com").count() == 1
        assert len(mailoutbox) == 2

    def test_weak_password_is_rejected(self, client):
        response = post_json(
            client, SIGNUP_URL, {"email": "weak@example.com", "password": "12345678"}
        )

        assert response.status_code == 400
        body = response.json()
        assert any(e.get("param") == "password" for e in body["errors"])


@pytest.mark.django_db
class TestEmailVerification:
    def test_verify_email_authenticates_the_session(self, client, mailoutbox):
        post_json(
            client, SIGNUP_URL, {"email": "verify.me@example.com", "password": STRONG_PASSWORD}
        )
        key = extract_key_from_email(mailoutbox[0].body)

        response = post_json(client, VERIFY_EMAIL_URL, {"key": key})

        assert response.status_code == 200
        body = response.json()
        assert body["meta"]["is_authenticated"] is True
        assert body["data"]["user"]["email"] == "verify.me@example.com"

        user = User.objects.get(email="verify.me@example.com")
        assert user.emailaddress_set.get(email__iexact=user.email).verified is True

    def test_invalid_verification_key_is_rejected(self, client):
        response = post_json(client, VERIFY_EMAIL_URL, {"key": "not-a-real-key"})

        assert response.status_code == 400


@pytest.mark.django_db
class TestLoginLogout:
    def test_login_with_verified_account_succeeds(self, client, mailoutbox):
        signup_and_verify(client, mailoutbox, "login.user@example.com")

        response = post_json(
            client, LOGIN_URL, {"email": "login.user@example.com", "password": STRONG_PASSWORD}
        )

        assert response.status_code == 200
        assert response.json()["meta"]["is_authenticated"] is True

    def test_login_with_wrong_password_fails(self, client, mailoutbox):
        signup_and_verify(client, mailoutbox, "wrong.pw@example.com")

        response = post_json(
            client, LOGIN_URL, {"email": "wrong.pw@example.com", "password": "totally-wrong-pass"}
        )

        assert response.status_code == 400
        assert any(e.get("param") == "password" for e in response.json()["errors"])
        assert client.get(ME_URL).status_code in (401, 403)

    def test_login_with_unverified_account_does_not_authenticate(self, client):
        post_json(
            client, SIGNUP_URL, {"email": "still.pending@example.com", "password": STRONG_PASSWORD}
        )
        client.logout()

        response = post_json(
            client, LOGIN_URL, {"email": "still.pending@example.com", "password": STRONG_PASSWORD}
        )

        assert response.json()["meta"]["is_authenticated"] is False

    def test_logout_clears_the_session(self, client, mailoutbox):
        signup_and_verify(client, mailoutbox, "logout.me@example.com")
        post_json(
            client, LOGIN_URL, {"email": "logout.me@example.com", "password": STRONG_PASSWORD}
        )
        assert client.get(ME_URL).status_code == 200

        response = client.delete(SESSION_URL)

        assert response.status_code == 401
        assert client.get(ME_URL).status_code == 401


@pytest.mark.django_db
class TestProtectedApiAccess:
    def test_unauthenticated_request_is_rejected(self, client):
        response = client.get(ME_URL)

        assert response.status_code == 401

    def test_unverified_signup_cannot_access_protected_endpoint(self, client):
        post_json(
            client, SIGNUP_URL, {"email": "no.access@example.com", "password": STRONG_PASSWORD}
        )

        response = client.get(ME_URL)

        assert response.status_code == 401

    def test_verified_authenticated_user_can_access_own_profile(self, client, mailoutbox):
        signup_and_verify(client, mailoutbox, "has.access@example.com")
        post_json(
            client, LOGIN_URL, {"email": "has.access@example.com", "password": STRONG_PASSWORD}
        )

        response = client.get(ME_URL)

        assert response.status_code == 200
        assert response.json()["email"] == "has.access@example.com"


@pytest.mark.django_db
class TestPasswordReset:
    def test_request_reset_for_existing_account_sends_email(self, client, mailoutbox):
        signup_and_verify(client, mailoutbox, "reset.me@example.com")
        mailoutbox.clear()

        response = post_json(client, REQUEST_RESET_URL, {"email": "reset.me@example.com"})

        assert response.status_code == 200
        assert len(mailoutbox) == 1
        assert "/auth/reset-password?key=" in mailoutbox[0].body

    def test_request_reset_for_unknown_email_does_not_leak_existence(self, client, mailoutbox):
        """The HTTP response must be indistinguishable from the known-email
        case (status 200 either way) — that's what "does not leak" means
        here. allauth still emails the address, but with an "unknown
        account" notice rather than a working reset link, so the address
        owner (if the input was just a typo by someone else) finds out
        without a reset key ever reaching an inbox that isn't theirs.
        """
        response = post_json(client, REQUEST_RESET_URL, {"email": "nobody.here@example.com"})

        assert response.status_code == 200
        assert len(mailoutbox) == 1
        assert "/auth/reset-password?key=" not in mailoutbox[0].body

    def test_reset_password_with_valid_key_then_login_with_new_password(self, client, mailoutbox):
        signup_and_verify(client, mailoutbox, "resetflow@example.com")
        mailoutbox.clear()
        post_json(client, REQUEST_RESET_URL, {"email": "resetflow@example.com"})
        key = extract_key_from_email(mailoutbox[0].body)

        response = post_json(
            client, RESET_PASSWORD_URL, {"key": key, "password": "brand-new-strong-pass-9"}
        )
        assert response.status_code == 200
        assert response.json()["meta"]["is_authenticated"] is True

        client.logout()
        login_response = post_json(
            client,
            LOGIN_URL,
            {"email": "resetflow@example.com", "password": "brand-new-strong-pass-9"},
        )
        assert login_response.json()["meta"]["is_authenticated"] is True

    def test_reset_password_with_invalid_key_is_rejected(self, client):
        response = post_json(
            client, RESET_PASSWORD_URL, {"key": "bogus-key", "password": "brand-new-strong-pass-9"}
        )

        assert response.status_code == 400


class TestCSRF:
    def test_post_without_csrf_token_is_rejected(self, client):
        strict_client = client
        strict_client.handler.enforce_csrf_checks = True

        response = post_json(
            strict_client, LOGIN_URL, {"email": "csrf@example.com", "password": STRONG_PASSWORD}
        )

        assert response.status_code == 403


@pytest.mark.django_db
class TestGoogleProviderBoundary:
    def test_provider_redirect_is_wired_to_google(self, client):
        response = client.post(
            PROVIDER_REDIRECT_URL,
            data={
                "provider": "google",
                "process": "login",
                "callback_url": "http://localhost:3000/auth/login",
            },
        )

        assert response.status_code == 302
        assert "accounts.google.com" in response["Location"]

    def test_provider_redirect_rejects_unknown_provider_without_leaking_to_google(self, client):
        response = client.post(
            PROVIDER_REDIRECT_URL,
            data={
                "provider": "not-a-real-provider",
                "process": "login",
                "callback_url": "http://localhost:3000/auth/login",
            },
        )

        assert response.status_code == 302
        assert "accounts.google.com" not in response["Location"]
        assert response["Location"].startswith("http://localhost:3000/auth/login")
