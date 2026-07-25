from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from common.domain import DomainError


def exception_handler(exc, context):
    """Global DRF exception handler (Section 14: "Return consistent JSON
    error objects"). Maps any DomainError — state-transition guards from
    common/domain.py plus per-app business-rule violations that subclass
    it (e.g. apps/loan_offers/services.py's OfferNotEditableError) — to 409
    Conflict: the request itself was well-formed, but the action doesn't
    apply to the resource's current state. Everything else falls through
    to DRF's default handler unchanged.
    """
    if isinstance(exc, DomainError):
        return Response({"detail": str(exc), "code": "conflict"}, status=status.HTTP_409_CONFLICT)
    return drf_exception_handler(exc, context)
