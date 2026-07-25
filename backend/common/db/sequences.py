"""Race-condition-safe human-readable reference number generator (master
prompt Section 12: request/loan/receipt references "without race
conditions"). One small counter table (common.models.NumberSequence),
incremented under a row lock inside its own transaction — this is the
standard way to get gap-tolerant, monotonic, human-readable numbers out of
PostgreSQL without relying on a raw sequence's formatting (which can't
easily produce e.g. `REQ-2026-000001`) and without a naive `count() + 1`
race.
"""

from django.db import transaction

from common.models import NumberSequence


def next_reference_number(scope: str, *, prefix: str, period: str, width: int = 6) -> str:
    """Atomically increments the (scope, period) counter and returns a
    formatted reference, e.g. next_reference_number("loan_request",
    prefix="REQ", period="2026") -> "REQ-2026-000001".

    Runs its own `transaction.atomic()` block — nests safely (as a savepoint)
    if the caller is already inside one, so this can be called from within a
    larger service-level transaction without any special handling.
    """
    with transaction.atomic():
        seq, _ = NumberSequence.objects.select_for_update().get_or_create(
            scope=scope, period=period
        )
        seq.last_value += 1
        seq.save(update_fields=["last_value"])
        return f"{prefix}-{period}-{seq.last_value:0{width}d}"
