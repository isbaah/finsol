from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.agreements.models import Agreement
from apps.loan_offers.models import LoanOffer
from apps.loan_requests.models import LoanRequest
from common.db.models import BaseModel

ZERO = Decimal("0.00")


class Loan(BaseModel):
    """See docs/DATA_MODEL.md Section 2.7 and docs/STATUS_TRANSITIONS.md
    Section 3. Created (in PENDING_APPROVAL) only by
    apps/loans/services.py::create_loan(), atomically alongside the
    LoanRequest's CONVERTED_TO_LOAN transition (Stage 8's acceptance flow).
    """

    class Status(models.TextChoices):
        PENDING_APPROVAL = "PENDING_APPROVAL", "Pending Approval"
        APPROVED_FOR_DISBURSEMENT = "APPROVED_FOR_DISBURSEMENT", "Approved for Disbursement"
        DISBURSED = "DISBURSED", "Disbursed"
        ACTIVE = "ACTIVE", "Active"
        PAID_OFF = "PAID_OFF", "Paid Off"
        OVERDUE = "OVERDUE", "Overdue"
        RESTRUCTURED = "RESTRUCTURED", "Restructured"  # reserved — not implemented in MVP
        DEFAULTED = "DEFAULTED", "Defaulted"  # reserved — not implemented in MVP
        CANCELLED = "CANCELLED", "Cancelled"

    loan_number = models.CharField(max_length=32, unique=True, editable=False)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="loans"
    )
    loan_request = models.OneToOneField(LoanRequest, on_delete=models.PROTECT, related_name="loan")
    accepted_offer = models.OneToOneField(LoanOffer, on_delete=models.PROTECT, related_name="loan")
    agreement = models.OneToOneField(Agreement, on_delete=models.PROTECT, related_name="loan")
    status = models.CharField(
        max_length=25, choices=Status.choices, default=Status.PENDING_APPROVAL
    )
    principal = models.DecimalField(max_digits=12, decimal_places=2)
    total_interest = models.DecimalField(max_digits=12, decimal_places=2)
    total_repayable = models.DecimalField(max_digits=12, decimal_places=2)
    # Authoritative, ledger-derived (apps/repayments's LoanTransaction is the
    # source of truth) — never trusted from a frontend-submitted value.
    amount_disbursed = models.DecimalField(max_digits=12, decimal_places=2, default=ZERO)
    amount_repaid = models.DecimalField(max_digits=12, decimal_places=2, default=ZERO)
    outstanding_balance = models.DecimalField(max_digits=12, decimal_places=2, default=ZERO)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_loans",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    disbursed_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(principal__gt=0), name="loan_principal_gt_0"),
            models.CheckConstraint(
                condition=models.Q(outstanding_balance__gte=0), name="loan_outstanding_gte_0"
            ),
            models.CheckConstraint(
                condition=models.Q(amount_disbursed__gte=0), name="loan_amount_disbursed_gte_0"
            ),
            models.CheckConstraint(
                condition=models.Q(amount_repaid__gte=0), name="loan_amount_repaid_gte_0"
            ),
        ]
        indexes = [models.Index(fields=["customer", "status"]), models.Index(fields=["status"])]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.loan_number


class RepaymentInstallment(BaseModel):
    """The active servicing schedule, copied from the accepted offer's
    OfferInstallment rows at loan-activation time (docs/DATA_MODEL.md
    Section 2.8). See apps/loans/services.py::copy_schedule_from_offer().
    """

    class Status(models.TextChoices):
        UPCOMING = "UPCOMING", "Upcoming"
        DUE = "DUE", "Due"
        PARTIALLY_PAID = "PARTIALLY_PAID", "Partially Paid"
        PAID = "PAID", "Paid"
        OVERDUE = "OVERDUE", "Overdue"
        WAIVED = "WAIVED", "Waived"

    loan = models.ForeignKey(Loan, on_delete=models.PROTECT, related_name="installments")
    sequence_number = models.PositiveIntegerField()
    due_date = models.DateField()
    principal_due = models.DecimalField(max_digits=12, decimal_places=2)
    interest_due = models.DecimalField(max_digits=12, decimal_places=2)
    total_due = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=ZERO)
    outstanding_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPCOMING)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["loan", "sequence_number"], name="repaymentinstallment_unique_sequence"
            ),
        ]
        indexes = [models.Index(fields=["loan", "status"]), models.Index(fields=["due_date"])]
        ordering = ["loan", "sequence_number"]

    def __str__(self) -> str:
        return f"{self.loan.loan_number} #{self.sequence_number}"


class Disbursement(BaseModel):
    """MVP supports exactly one disbursement per loan, but modelled with a
    plain FK + a removable unique constraint (not OneToOneField) so a
    future partial/staged disbursement feature only needs to drop the
    constraint, not restructure the relationship (docs/DATA_MODEL.md
    Section 2.9).
    """

    class Method(models.TextChoices):
        MOBILE_MONEY = "MOBILE_MONEY", "Mobile Money"
        BANK = "BANK", "Bank"

    loan = models.ForeignKey(Loan, on_delete=models.PROTECT, related_name="disbursements")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=20, choices=Method.choices)
    # Masked method + destination only — never raw account digits (Section 26).
    masked_payout_snapshot = models.JSONField(default=dict, blank=True)
    external_transaction_reference = models.CharField(max_length=100, blank=True)
    evidence_file_path = models.CharField(max_length=500, blank=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recorded_disbursements"
    )
    recorded_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["loan"], name="disbursement_one_per_loan_mvp"),
            models.UniqueConstraint(
                fields=["external_transaction_reference"],
                name="disbursement_unique_reference_when_set",
                condition=~models.Q(external_transaction_reference=""),
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="disbursement_amount_gt_0"
            ),
        ]

    def __str__(self) -> str:
        return f"Disbursement<{self.loan.loan_number}>"
