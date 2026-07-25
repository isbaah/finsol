from django.conf import settings
from django.db import models

from common.db.models import BaseModel


class LoanRequest(BaseModel):
    """See docs/DATA_MODEL.md Section 2.3 and docs/STATUS_TRANSITIONS.md
    Section 1. Rows are only ever created/transitioned through
    apps/loan_requests/services.py — never a generic CRUD write (Section 26).
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
        OFFER_SENT = "OFFER_SENT", "Offer Sent"
        CUSTOMER_ACCEPTED = "CUSTOMER_ACCEPTED", "Customer Accepted"
        CUSTOMER_REJECTED = "CUSTOMER_REJECTED", "Customer Rejected"
        REVISION_REQUESTED = "REVISION_REQUESTED", "Revision Requested"
        APPROVED = (
            "APPROVED",
            "Approved",
        )  # reserved/unused — see STATUS_TRANSITIONS.md open decision
        DECLINED = "DECLINED", "Declined"
        CANCELLED = "CANCELLED", "Cancelled"
        CONVERTED_TO_LOAN = "CONVERTED_TO_LOAN", "Converted to Loan"

    class TermUnit(models.TextChoices):
        WEEK = "WEEK", "Week"
        MONTH = "MONTH", "Month"

    request_number = models.CharField(max_length=32, unique=True, editable=False)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="loan_requests"
    )
    requested_amount = models.DecimalField(max_digits=12, decimal_places=2)
    purpose = models.TextField()
    requested_term_count = models.PositiveIntegerField(null=True, blank=True)
    requested_term_unit = models.CharField(max_length=10, choices=TermUnit.choices, blank=True)
    # A masked-safe snapshot of payout intent at submission time (method +
    # masked destination only — never raw account digits, per Section 26).
    # The authoritative, current payout details always live on
    # CustomerProfile; this is a point-in-time reference, not a duplicate
    # source of truth.
    payout_snapshot = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    submitted_at = models.DateTimeField(null=True, blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_loan_requests",
    )
    customer_notes = models.TextField(blank=True)
    # Never exposed to customers — enforced at the serializer layer (Stage 6+).
    internal_notes = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["status"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.request_number
