"""Shared state-transition guard for domain models (master prompt Section 11
/ docs/STATUS_TRANSITIONS.md). Used by every app with an explicit status
field — loan_requests, loan_offers, loans — so the "reject invalid
transitions with a domain-specific error" rule (Section 11) is enforced
identically everywhere instead of re-implemented per app.

Callers are responsible for locking the row first (`select_for_update()`
inside `transaction.atomic()`) — this helper only validates and applies the
transition; it doesn't manage the transaction itself, since callers often
need to do more work (e.g. set `assigned_to`, write an AuditEvent) in the
same atomic block.
"""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """Base class for domain-rule violations that should surface as a 409
    Conflict, not an unhandled 500 — see common/api/exceptions.py's global
    DRF exception handler. Subclassed per-app for specific violations (e.g.
    InvalidTransitionError here, OfferNotEditableError in
    apps/loan_offers/services.py) rather than centralizing every subtype in
    this app-agnostic module.
    """


class InvalidTransitionError(DomainError):
    def __init__(self, model_label: str, from_status: str, to_status: str):
        self.model_label = model_label
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(f"Cannot transition {model_label} from {from_status!r} to {to_status!r}.")


def apply_transition(
    instance: Any,
    *,
    to: str,
    allowed_from: frozenset[str] | set[str],
    field: str = "status",
) -> Any:
    """Validate and apply a single status transition on an already-locked
    instance. Raises InvalidTransitionError if the current value of `field`
    isn't in `allowed_from`. Does not save — callers save alongside whatever
    other fields they're setting in the same operation, so this never
    issues a redundant extra UPDATE.
    """
    current = getattr(instance, field)
    if current not in allowed_from:
        raise InvalidTransitionError(instance.__class__.__name__, current, to)
    setattr(instance, field, to)
    return instance
