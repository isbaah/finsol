"""Settings shared by every environment.

Environment-specific settings (local, test, production) import from this
module and override only what genuinely differs. See docs/ARCHITECTURE.md
for the reasoning behind the split-settings layout.
"""

from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def env(name: str, default: str | None = None) -> str | None:
    import os

    return os.environ.get(name, default)


def env_bool(name: str, default: bool) -> bool:
    value = env(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    value = env(name, default) or ""
    return [item.strip() for item in value.split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

APP_NAME = env("APP_NAME", "Loan Management System")
APP_ENV = env("APP_ENV", "local")
APP_BASE_URL = env("APP_BASE_URL", "http://localhost:3000")
API_BASE_URL = env("API_BASE_URL", "http://localhost:8000")

SECRET_KEY = env("DJANGO_SECRET_KEY", "")

DEBUG = False

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    # Headless-only (no django.contrib.sites; no allauth server-rendered
    # templates) — see docs/ARCHITECTURE.md's authentication section.
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.headless",
]

LOCAL_APPS = [
    "common",
    "apps.accounts",
    "apps.customers",
    "apps.audit",
    "apps.loan_requests",
    "apps.loan_offers",
    "apps.agreements",
    "apps.loans",
    "apps.repayments",
    "apps.messaging",
    "apps.dashboards",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database
#
# PostgreSQL is the sole authoritative database (see docs/SECURITY.md /
# master-prompt Section 26: "DO NOT use SQLite outside isolated unit tests").
# Test settings point at the same PostgreSQL instance via a Django-managed
# test database, rather than substituting SQLite, to avoid ORM/feature drift
# (e.g. the citext extension used for case-insensitive email uniqueness).
# ---------------------------------------------------------------------------

DATABASES = {
    "default": dj_database_url.parse(
        env(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/loan_management",
        ),
        conn_max_age=60,
    ),
}

# ---------------------------------------------------------------------------
# Auth / passwords
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("APP_TIME_ZONE", "Africa/Accra")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static / media
# ---------------------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", str(BASE_DIR / "media")))

# Selects integrations/storage's backend (docs/ARCHITECTURE.md Section 11).
# Only "local" is implemented — an S3-compatible backend is added when
# production actually needs one (master prompt Section 18).
STORAGE_BACKEND = env("STORAGE_BACKEND", "local")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# CORS / CSRF
#
# Never a wildcard origin combined with credentials (docs/SECURITY.md).
# ---------------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS", "http://localhost:3000,http://localhost:8000"
)

SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", False)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# ---------------------------------------------------------------------------
# Authentication (django-allauth headless browser flows)
#
# Verified against the installed django-allauth==65.18.0 source directly
# (not from training-data memory) — see docs/BUILD_PROGRESS.md Stage 2 notes.
# ---------------------------------------------------------------------------

HEADLESS_ONLY = True
# Browser client only (session cookie + CSRF) — the "app" client uses a
# bearer session token, which we do not want (Section 9: no auth token in
# localStorage, and no reason to support native-app token auth in the MVP).
HEADLESS_CLIENTS = ["browser"]

# allauth sends verification/reset emails with links that point at the
# Next.js frontend, not at Django. The frontend page then calls the
# corresponding headless JSON endpoint with the key. Keys placed in the
# query string (not a path segment) to match docs/ARCHITECTURE.md's frontend
# route list (`/auth/verify-email`, `/auth/reset-password`).
HEADLESS_FRONTEND_URLS = {
    "account_confirm_email": f"{APP_BASE_URL}/auth/verify-email?key={{key}}",
    "account_reset_password": f"{APP_BASE_URL}/auth/forgot-password",
    "account_reset_password_from_key": f"{APP_BASE_URL}/auth/reset-password?key={{key}}",
    "account_signup": f"{APP_BASE_URL}/auth/signup",
    "socialaccount_login_error": f"{APP_BASE_URL}/auth/login?error=social",
}

ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*"]
# Our custom User model (apps/accounts/models.py) has no `username` column at
# all — email is the sole identifier. Without this, allauth's signup form
# still tries to introspect a "username" field on the model and crashes.
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
# Mandatory: signup does not fully authenticate the session until the user
# verifies — enforced by allauth's own login-stage system, so an unverified
# user's session never reaches request.user.is_authenticated = True and every
# DRF endpoint (default IsAuthenticated) rejects it automatically.
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED = False
ACCOUNT_PASSWORD_RESET_BY_CODE_ENABLED = False
# Both default to False upstream, which would otherwise dead-end the user on
# a "please log in" screen immediately after they just proved who they are.
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGIN_ON_PASSWORD_RESET = True
# Phone belongs to CustomerProfile (Stage 3), not allauth's own account flow.
ACCOUNT_PHONE_VERIFICATION_ENABLED = False
# Built-in login/signup/password-reset rate limiting (Section 9: "Add login
# throttling/rate limits using supported framework mechanisms"). Defaults are
# 10/min/ip plus 5 attempts per 5 minutes per account for login; left at
# allauth's documented defaults rather than overridden.

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": env("GOOGLE_CLIENT_ID", ""),
            "secret": env("GOOGLE_CLIENT_SECRET", ""),
            "key": "",
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    }
}

# ---------------------------------------------------------------------------
# DRF / OpenAPI
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "common.api.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_RATES": {
        "login": "10/min",
    },
    "EXCEPTION_HANDLER": "common.api.exceptions.exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Loan Management System API",
    "DESCRIPTION": (
        "API for the Loan Management Web Application. "
        "See docs/API.md for endpoint-by-endpoint documentation."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ---------------------------------------------------------------------------
# Email (default: console backend; overridden per environment)
# ---------------------------------------------------------------------------

EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = int(env("EMAIL_PORT", "587") or "587")
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "no-reply@localhost")

# Never hard-coded — configurable action mailbox for signed agreements
# (docs/PRODUCT_ASSUMPTIONS.md Section 7; wired up in Stage 8).
AGREEMENT_ACTION_EMAIL = env("AGREEMENT_ACTION_EMAIL", "")

# ---------------------------------------------------------------------------
# Agreement PDF (Stage 8)
#
# A placeholder legal identity only — master prompt Section 18: "Do not
# claim that the implementation has legal validity or regulatory approval."
# Real entity details are a production-launch task, not a code change.
# ---------------------------------------------------------------------------

LENDER_NAME = env("LENDER_NAME", "[Lender Legal Name Placeholder]")

# ---------------------------------------------------------------------------
# Messaging / Hubtel SMS (Stage 11 — see integrations/sms/ for the provider
# interface). Real sending is impossible unless BOTH HUBTEL_ENABLED=true AND
# SMS_DRY_RUN=false are explicitly set (master prompt Section 17/20's "real
# sending must be impossible by default" requirement) — see
# integrations/sms/__init__.py::get_sms_provider().
# ---------------------------------------------------------------------------

HUBTEL_ENABLED = env_bool("HUBTEL_ENABLED", False)
HUBTEL_BASE_URL = env("HUBTEL_BASE_URL", "https://smsc.hubtel.com")
HUBTEL_CLIENT_ID = env("HUBTEL_CLIENT_ID", "")
HUBTEL_CLIENT_SECRET = env("HUBTEL_CLIENT_SECRET", "")
HUBTEL_SENDER_ID = env("HUBTEL_SENDER_ID", "")
HUBTEL_ADMIN_PHONE_E164 = env("HUBTEL_ADMIN_PHONE_E164", "")
HUBTEL_CONNECT_TIMEOUT_SECONDS = float(env("HUBTEL_CONNECT_TIMEOUT_SECONDS", "5") or "5")
HUBTEL_READ_TIMEOUT_SECONDS = float(env("HUBTEL_READ_TIMEOUT_SECONDS", "10") or "10")
HUBTEL_MAX_REQUESTS_PER_MINUTE = int(env("HUBTEL_MAX_REQUESTS_PER_MINUTE", "60") or "60")
SMS_DRY_RUN = env_bool("SMS_DRY_RUN", True)
SMS_MAX_ATTEMPTS = int(env("SMS_MAX_ATTEMPTS", "3") or "3")
# Reminder times moved to the DB-backed apps.messaging.models.SMSSettings
# singleton, editable from /admin/settings — no env var equivalent anymore.

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("DJANGO_LOG_LEVEL", "INFO"),
    },
}
