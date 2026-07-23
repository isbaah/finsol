"""Settings for the automated test suite.

Uses the same PostgreSQL database engine as every other environment
(Django creates/tears down a dedicated `test_<name>` database) rather than
substituting SQLite — see the note in base.py's Database section.
"""

from .base import *  # noqa: F403

DEBUG = False

ALLOWED_HOSTS = ["*"]

SECRET_KEY = "test-secret-key-not-for-production-use"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

AGREEMENT_ACTION_EMAIL = "agreement-action-test@example.com"
