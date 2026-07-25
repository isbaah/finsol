"""Request metadata extraction shared by anything that needs to record
"who did this, from where" (Section 18: agreement acceptance evidence;
Section 20: audit events). A single helper so every caller agrees on the
same header precedence.
"""

from __future__ import annotations

from rest_framework.request import Request


def get_client_ip(request: Request) -> str | None:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or None


def get_user_agent(request: Request) -> str:
    return request.META.get("HTTP_USER_AGENT", "")
