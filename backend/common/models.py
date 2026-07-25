from django.db import models


class NumberSequence(models.Model):
    """One row per (scope, period) — e.g. ("loan_request", "2026"). See
    common/db/sequences.py's next_reference_number() for how this is used to
    generate race-condition-safe human-readable reference numbers.
    """

    scope = models.CharField(max_length=40)
    period = models.CharField(max_length=8)
    last_value = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["scope", "period"], name="numbersequence_scope_period"),
        ]

    def __str__(self) -> str:
        return f"{self.scope}/{self.period} -> {self.last_value}"
