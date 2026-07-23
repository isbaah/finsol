"""Production settings.

Fails startup loudly when a mandatory secret/config value is missing,
rather than falling back to an insecure default (docs/SECURITY.md).
"""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import env, env_bool

DEBUG = False


def require_env(name: str) -> str:
    value = env(name)
    if not value:
        raise ImproperlyConfigured(f"{name} must be set in the production environment.")
    return value


SECRET_KEY = require_env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = [h for h in require_env("DJANGO_ALLOWED_HOSTS").split(",") if h]

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = int(env("SECURE_HSTS_SECONDS", "31536000") or "31536000")
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True

AGREEMENT_ACTION_EMAIL = require_env("AGREEMENT_ACTION_EMAIL")
