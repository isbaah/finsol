"""Settings for the automated test suite.

Uses the same PostgreSQL database engine as every other environment
(Django creates/tears down a dedicated `test_<name>` database) rather than
substituting SQLite — see the note in base.py's Database section.
"""

import tempfile
from pathlib import Path

from .base import *  # noqa: F403

DEBUG = False

# Isolated from the real MEDIA_ROOT so a test run's generated agreement
# PDFs/signature images never land in (or pollute) the dev media volume.
MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="lms-test-media-"))

ALLOWED_HOSTS = ["*"]

SECRET_KEY = "test-secret-key-not-for-production-use"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

AGREEMENT_ACTION_EMAIL = "agreement-action-test@example.com"

# Disable allauth's built-in rate limiting in tests — a test run legitimately
# makes many rapid login/signup attempts against the same email/IP, which
# would otherwise trip the same limits real abuse is meant to trip.
ACCOUNT_RATE_LIMITS = False

# Dummy but well-formed credentials so the Google provider-redirect boundary
# is actually exercised by tests (Stage 2 test list: "Google provider
# boundary configuration") without depending on real Google credentials.
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": "test-google-client-id.apps.googleusercontent.com",
            "secret": "test-google-client-secret",  # nosec
            "key": "",
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    }
}
