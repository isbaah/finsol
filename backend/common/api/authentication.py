from rest_framework.authentication import SessionAuthentication as _SessionAuthentication


class SessionAuthentication(_SessionAuthentication):
    """DRF's SessionAuthentication returns 403 for unauthenticated requests,
    because it leaves `authenticate_header()` unset. That collapses "not
    authenticated" and "authenticated but forbidden" into the same status
    code. Overriding it to return a non-empty header restores the normal
    401/403 distinction (Section 14: "Return consistent JSON error
    objects") without changing CSRF enforcement or any other behavior.
    """

    def authenticate_header(self, request):
        return "Session"
