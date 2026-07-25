"""AuditEvent write path (master prompt Section 12.14 / Section 20). Every
domain transition service across loan_requests/loan_offers/loans/repayments
calls record_event() in the same atomic block as the state change it's
recording, so an event is never written for a transition that didn't
actually happen (and vice versa).
"""

from __future__ import annotations

from typing import Any

from apps.audit.models import AuditEvent

# Keys that must never appear in before/after JSON, regardless of which
# model the caller serialized (Section 26: "DO NOT log passwords, API
# secrets, session identifiers, full account numbers, signature images, or
# private document contents"). Matched case-insensitively against dict keys
# at any nesting depth.
_REDACTED_KEY_FRAGMENTS = (
    "password",
    "secret",
    "token",
    "session",
    "mobile_money_number",
    "bank_account_number",
    "signature",
    "credential",
)

REDACTED_VALUE = "[REDACTED]"


def redact(data: Any) -> Any:
    """Recursively redacts dict values whose key matches a sensitive
    fragment. Lists/tuples are walked; other value types pass through
    unchanged (they aren't dicts, so nothing under them could be a
    sensitive key/value pair)."""
    if isinstance(data, dict):
        return {
            key: (
                REDACTED_VALUE
                if any(fragment in key.lower() for fragment in _REDACTED_KEY_FRAGMENTS)
                else redact(value)
            )
            for key, value in data.items()
        }
    if isinstance(data, (list, tuple)):
        return [redact(item) for item in data]
    return data


def record_event(
    *,
    actor,
    action: str,
    entity,
    before: dict | None = None,
    after: dict | None = None,
    reason: str = "",
    correlation_id: str = "",
    ip_address: str | None = None,
    user_agent: str = "",
) -> AuditEvent:
    """Writes one AuditEvent. `entity` is a model instance — its class name
    and primary key become entity_type/entity_id. `before`/`after` are
    passed through redact() unconditionally; callers never need to
    remember to redact themselves.
    """
    actor_role_snapshot = ""
    if actor is not None:
        actor_role_snapshot = ", ".join(actor.groups.values_list("name", flat=True))

    return AuditEvent.objects.create(
        actor=actor,
        actor_role_snapshot=actor_role_snapshot,
        action=action,
        entity_type=entity.__class__.__name__,
        entity_id=str(entity.pk),
        before=redact(before) if before is not None else None,
        after=redact(after) if after is not None else None,
        reason=reason,
        correlation_id=correlation_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
