"""Business role membership and ownership checks (master prompt Section 10).

Business roles are represented as Django Groups, seeded idempotently by
`python manage.py seed_roles` (apps/accounts/management/commands). This is
deliberately independent of Django's `is_staff`/`is_superuser` flags, which
gate the technical Django admin site only:

    "Django `is_superuser` is reserved for controlled technical
    administration and is not the only business authorisation mechanism."

So a Django technical superuser is not automatically a business SUPER_ADMIN,
and vice versa — group membership is checked explicitly, with no shortcut.
"""

from rest_framework.permissions import BasePermission

LOAN_OFFICER = "LOAN_OFFICER"
APPROVER = "APPROVER"
FINANCE_OFFICER = "FINANCE_OFFICER"
AUDITOR = "AUDITOR"
SUPER_ADMIN = "SUPER_ADMIN"

# The internal/staff roles. CUSTOMER is deliberately not a Group here — it's
# modelled as the absence of any staff role (see UserSerializer.get_is_customer).
STAFF_ROLES = (LOAN_OFFICER, APPROVER, FINANCE_OFFICER, AUDITOR, SUPER_ADMIN)


def user_has_any_role(user, *roles: str) -> bool:
    if not (user and user.is_authenticated):
        return False
    return user.groups.filter(name__in=roles).exists()


def has_any_role(*roles: str):
    """DRF permission-class factory, e.g. `has_any_role(APPROVER, SUPER_ADMIN)`."""

    class _HasAnyRole(BasePermission):
        def has_permission(self, request, view) -> bool:
            return user_has_any_role(request.user, *roles)

    return _HasAnyRole


class IsOwner(BasePermission):
    """Object-level check: the target object's `user` (or `customer`) FK is
    the caller. `customer` is checked too since that's the owning field's
    name on LoanRequest/LoanOffer (Section 12.3/12.4) — `user` remains
    first since it's CustomerProfile's own field name (Section 12.2).

    Applied as defense-in-depth (Section 10: "Critical actions must be
    checked in both the API permission layer and the domain service
    layer") even where the surrounding view already scopes lookups to
    request.user by construction.
    """

    def has_object_permission(self, request, view, obj) -> bool:
        owner = getattr(obj, "user", None) or getattr(obj, "customer", None)
        return owner is not None and owner == request.user
