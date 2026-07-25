from django.conf import settings
from django.db import models

from apps.loan_requests.models import LoanRequest
from common.db.models import BaseModel

# Sanity upper bound for a single loan term, in the selected unit (60 weeks
# or 60 months) — not a business rule from the master prompt, a documented
# Stage 4 assumption guarding against fat-fingered input. See
# docs/BUILD_PROGRESS.md's Stage 4 notes.
MAX_TERM_COUNT = 60


class LoanOffer(BaseModel):
    """See docs/DATA_MODEL.md Section 2.4 and docs/STATUS_TRANSITIONS.md
    Section 2. Rows are only ever created/transitioned through
    apps/loan_offers/services.py.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SENT = "SENT", "Sent"
        SUPERSEDED = "SUPERSEDED", "Superseded"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"
        EXPIRED = "EXPIRED", "Expired"

    class InterestMethod(models.TextChoices):
        # Only strategy implemented in the MVP (ADR-003) — modelled as
        # choices, not hard-coded, so a second strategy is an additive
        # change later, not a schema rewrite.
        FLAT_TOTAL_TERM = "FLAT_TOTAL_TERM", "Flat Total-Term Interest"

    class TermUnit(models.TextChoices):
        WEEK = "WEEK", "Week"
        MONTH = "MONTH", "Month"

    loan_request = models.ForeignKey(LoanRequest, on_delete=models.PROTECT, related_name="offers")
    version_number = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    principal = models.DecimalField(max_digits=12, decimal_places=2)
    interest_method = models.CharField(
        max_length=20, choices=InterestMethod.choices, default=InterestMethod.FLAT_TOTAL_TERM
    )
    interest_rate_percent = models.DecimalField(max_digits=6, decimal_places=2)
    term_count = models.PositiveIntegerField()
    term_unit = models.CharField(max_length=10, choices=TermUnit.choices)
    first_due_date = models.DateField()
    total_interest = models.DecimalField(max_digits=12, decimal_places=2)
    total_repayable = models.DecimalField(max_digits=12, decimal_places=2)
    installment_count = models.PositiveIntegerField()
    offer_expiry_date = models.DateField(null=True, blank=True)
    customer_terms = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_offers"
    )
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sent_offers",
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    # Fields frozen once status == ACCEPTED (see save() below).
    _FINANCIAL_FIELDS = (
        "principal",
        "interest_method",
        "interest_rate_percent",
        "term_count",
        "term_unit",
        "first_due_date",
        "total_interest",
        "total_repayable",
        "installment_count",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["loan_request", "version_number"], name="loanoffer_unique_version"
            ),
            models.CheckConstraint(
                condition=models.Q(principal__gt=0), name="loanoffer_principal_gt_0"
            ),
            models.CheckConstraint(
                condition=models.Q(interest_rate_percent__gte=0),
                name="loanoffer_interest_rate_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(term_count__gt=0) & models.Q(term_count__lte=MAX_TERM_COUNT),
                name="loanoffer_term_count_bounds",
            ),
        ]
        indexes = [models.Index(fields=["loan_request", "status"])]
        ordering = ["loan_request", "-version_number"]

    def __str__(self) -> str:
        return f"{self.loan_request.request_number} v{self.version_number}"

    @property
    def customer(self):
        """Lets common/permissions/roles.py's IsOwner check offer ownership
        the same generic way it checks every other owned resource, without
        LoanOffer needing its own duplicate `customer` FK — the request it
        belongs to is the single source of truth for who owns it."""
        return self.loan_request.customer

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                current = LoanOffer.objects.get(pk=self.pk)
            except LoanOffer.DoesNotExist:
                current = None
            if current and current.status == self.Status.ACCEPTED:
                changed = [
                    field
                    for field in self._FINANCIAL_FIELDS
                    if getattr(current, field) != getattr(self, field)
                ]
                if changed:
                    raise ValueError(f"Accepted offers are immutable; cannot change {changed}.")
        super().save(*args, **kwargs)


class OfferInstallment(BaseModel):
    """The immutable proposed schedule for an offer (docs/DATA_MODEL.md
    Section 2.5). Always written in bulk by
    apps/loan_offers/services.py::create_offer_with_schedule() — the same
    persistence path used by both the Stage 5 preview-backed creation flow
    and any future direct creation, so numbers can never drift.
    """

    offer = models.ForeignKey(LoanOffer, on_delete=models.CASCADE, related_name="installments")
    sequence_number = models.PositiveIntegerField()
    due_date = models.DateField()
    principal_due = models.DecimalField(max_digits=12, decimal_places=2)
    interest_due = models.DecimalField(max_digits=12, decimal_places=2)
    total_due = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["offer", "sequence_number"], name="offerinstallment_unique_sequence"
            ),
        ]
        ordering = ["offer", "sequence_number"]

    def __str__(self) -> str:
        return f"{self.offer} #{self.sequence_number}"
