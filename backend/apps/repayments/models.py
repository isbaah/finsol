from django.conf import settings
from django.db import models

from apps.loans.models import Loan, RepaymentInstallment
from common.db.models import BaseModel


class Payment(BaseModel):
    """See docs/DATA_MODEL.md Section 2.10 and docs/STATUS_TRANSITIONS.md
    Section 5. Never edited to "correct" a mistake — see
    apps/repayments/services.py::reverse_payment().
    """

    class Status(models.TextChoices):
        POSTED = "POSTED", "Posted"
        REVERSED = "REVERSED", "Reversed"

    class Method(models.TextChoices):
        MOBILE_MONEY = "MOBILE_MONEY", "Mobile Money"
        BANK = "BANK", "Bank"
        CASH = "CASH", "Cash"
        OTHER = "OTHER", "Other"

    receipt_number = models.CharField(max_length=32, unique=True, editable=False)
    loan = models.ForeignKey(Loan, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=Method.choices)
    external_transaction_reference = models.CharField(max_length=100, blank=True)
    evidence_file_path = models.CharField(max_length=500, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.POSTED)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recorded_payments"
    )
    recorded_at = models.DateTimeField()
    # Points from a brand-new corrective Payment back to the one it
    # supersedes ("A corrected payment is posted as a brand-new Payment
    # record" — Section 12.10). Left null by reverse_payment() itself,
    # which only flips the original's own status; populated later, by
    # Stage 10, when/if a correcting payment is actually posted.
    reversal_of = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="reversal"
    )
    reversal_reason = models.TextField(blank=True)
    # Server-side duplicate-submission protection (Section 14/26) — the
    # client-supplied or request-derived key that makes a retried POST a
    # no-op instead of a second payment.
    idempotency_key = models.CharField(max_length=100, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="payment_amount_gt_0"),
            models.UniqueConstraint(
                fields=["external_transaction_reference"],
                name="payment_unique_reference_when_set",
                condition=~models.Q(external_transaction_reference=""),
            ),
            models.UniqueConstraint(
                fields=["idempotency_key"],
                name="payment_unique_idempotency_key_when_set",
                condition=~models.Q(idempotency_key=""),
            ),
        ]
        indexes = [models.Index(fields=["loan", "status"])]
        ordering = ["-recorded_at"]

    def __str__(self) -> str:
        return self.receipt_number


class PaymentAllocation(BaseModel):
    """See docs/DATA_MODEL.md Section 2.11. Populated by the Stage 10
    payment-recording workflow's allocation algorithm — this stage only
    defines the schema and its structural constraint.
    """

    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="allocations")
    installment = models.ForeignKey(
        RepaymentInstallment, on_delete=models.PROTECT, related_name="allocations"
    )
    principal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_amount = models.DecimalField(max_digits=12, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["payment", "installment"], name="paymentallocation_unique_pair"
            ),
            models.CheckConstraint(
                condition=models.Q(total_amount__gt=0), name="paymentallocation_total_gt_0"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.payment.receipt_number} -> installment #{self.installment.sequence_number}"


class RepaymentAccount(BaseModel):
    """The company's collection account — where customers send repayments
    (post-Stage-12 user-requested feature). A single row, maintained by the
    SUPER_ADMIN on the admin settings page and shown (with copy actions) in
    the customer's installment-detail dialog. These are *receiving* details,
    deliberately unmasked: customers need the full number to pay into it.
    """

    singleton_key = models.CharField(max_length=10, default="default", unique=True, editable=False)
    mobile_money_network = models.CharField(max_length=20, blank=True)
    mobile_money_number = models.CharField(max_length=20, blank=True)
    mobile_money_account_name = models.CharField(max_length=150, blank=True)
    bank_name = models.CharField(max_length=150, blank=True)
    bank_account_name = models.CharField(max_length=150, blank=True)
    bank_account_number = models.CharField(max_length=50, blank=True)
    payment_instructions = models.TextField(blank=True)

    def __str__(self) -> str:
        return "Repayment collection account"

    @classmethod
    def get_solo(cls) -> "RepaymentAccount":
        obj, _ = cls.objects.get_or_create(singleton_key="default")
        return obj


class PaymentClaim(BaseModel):
    """A customer's "I've paid this installment" notice (post-Stage-12
    user-requested feature). Purely informational — it never mutates any
    financial state. The claim surfaces in the admin dashboard/claims queue;
    money only ever moves through services.record_payment(), which also
    auto-resolves claims whose installment ends up fully PAID.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RESOLVED = "RESOLVED", "Resolved"

    loan = models.ForeignKey(Loan, on_delete=models.PROTECT, related_name="payment_claims")
    installment = models.ForeignKey(
        RepaymentInstallment, on_delete=models.PROTECT, related_name="payment_claims"
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payment_claims"
    )
    note = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="resolved_payment_claims",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            # One open claim per installment — a second "I've paid" while the
            # first is still unreviewed is a duplicate, not new information.
            models.UniqueConstraint(
                fields=["installment"],
                condition=models.Q(status="PENDING"),
                name="paymentclaim_one_pending_per_installment",
            ),
        ]
        indexes = [models.Index(fields=["status", "created_at"])]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Claim<{self.loan.loan_number} #{self.installment.sequence_number} {self.status}>"


class LoanTransaction(BaseModel):
    """Append-only ledger (docs/DATA_MODEL.md Section 2.12). No update/delete
    API surface is ever exposed — enforced here too, the same way as
    apps/audit's AuditEvent, as a second guarantee independent of "we just
    never built that endpoint".
    """

    class TransactionType(models.TextChoices):
        DISBURSEMENT = "DISBURSEMENT", "Disbursement"
        REPAYMENT = "REPAYMENT", "Repayment"
        REVERSAL = "REVERSAL", "Reversal"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"
        WRITE_OFF = "WRITE_OFF", "Write Off"

    loan = models.ForeignKey(Loan, on_delete=models.PROTECT, related_name="transactions")
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    # Signed for REPAYMENT/REVERSAL/ADJUSTMENT/WRITE_OFF, which post through
    # apps/repayments/services.py::post_ledger_entry() and do mutate
    # Loan.outstanding_balance by this amount. DISBURSEMENT is the one
    # exception (Stage 9 design decision, docs/BUILD_PROGRESS.md): it's
    # recorded as a positive, purely informational amount via
    # apps/loans/services.py::_post_disbursement_ledger_entry() and never
    # changes outstanding_balance — create_loan() already sets
    # outstanding_balance = total_repayable at PENDING_APPROVAL time, and
    # Section 19's reconciliation formula is defined purely in terms of
    # repayment (outstanding == total_repayable - amount_repaid).
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    effective_date = models.DateField()
    source_object_type = models.CharField(max_length=100)
    source_object_id = models.CharField(max_length=64)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.PROTECT,
        related_name="recorded_ledger_entries",
    )
    reason = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["loan", "created_at"]),
            models.Index(fields=["source_object_type", "source_object_id"]),
        ]
        ordering = ["loan", "created_at"]

    def __str__(self) -> str:
        return f"{self.loan.loan_number} {self.transaction_type} {self.amount}"

    def save(self, *args, **kwargs):
        if self.pk and LoanTransaction.objects.filter(pk=self.pk).exists():
            raise ValueError("LoanTransaction rows are append-only and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("LoanTransaction rows are append-only and cannot be deleted.")
