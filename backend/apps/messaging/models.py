from datetime import time

from django.conf import settings
from django.db import models

from apps.loans.models import Loan, RepaymentInstallment
from common.db.models import BaseModel


class SMSMessage(BaseModel):
    """See docs/DATA_MODEL.md Section 2.13 and docs/STATUS_TRANSITIONS.md
    Section 6. `message_type` is the full catalog required by master prompt
    Section 17, wired up in Stage 11 (superseding the Stage 4/7 provisional
    starter set).
    """

    class MessageType(models.TextChoices):
        LOAN_OFFER_READY = "LOAN_OFFER_READY", "Loan Offer Ready"
        OFFER_ACCEPTED_CUSTOMER = "OFFER_ACCEPTED_CUSTOMER", "Offer Accepted (Customer)"
        OFFER_ACCEPTED_ADMIN = "OFFER_ACCEPTED_ADMIN", "Offer Accepted (Admin)"
        LOAN_APPROVED = "LOAN_APPROVED", "Loan Approved"
        LOAN_DISBURSED_CUSTOMER = "LOAN_DISBURSED_CUSTOMER", "Loan Disbursed (Customer)"
        LOAN_DISBURSED_ADMIN = "LOAN_DISBURSED_ADMIN", "Loan Disbursed (Admin)"
        PAYMENT_RECEIVED_CUSTOMER = "PAYMENT_RECEIVED_CUSTOMER", "Payment Received (Customer)"
        PAYMENT_RECEIVED_ADMIN = "PAYMENT_RECEIVED_ADMIN", "Payment Received (Admin)"
        REPAYMENT_DUE_5_DAYS = "REPAYMENT_DUE_5_DAYS", "Repayment Due in 5 Days"
        REPAYMENT_DUE_3_DAYS = "REPAYMENT_DUE_3_DAYS", "Repayment Due in 3 Days"
        REPAYMENT_DUE_2_DAYS = "REPAYMENT_DUE_2_DAYS", "Repayment Due in 2 Days"
        REPAYMENT_DUE_1_DAY = "REPAYMENT_DUE_1_DAY", "Repayment Due in 1 Day"
        REPAYMENT_DUE_TODAY_MORNING = "REPAYMENT_DUE_TODAY_MORNING", "Repayment Due Today (Morning)"
        REPAYMENT_DUE_TODAY_AFTERNOON = (
            "REPAYMENT_DUE_TODAY_AFTERNOON",
            "Repayment Due Today (Afternoon)",
        )
        REPAYMENT_OVERDUE = "REPAYMENT_OVERDUE", "Repayment Overdue"
        LOAN_PAID_OFF_CUSTOMER = "LOAN_PAID_OFF_CUSTOMER", "Loan Paid Off (Customer)"
        LOAN_PAID_OFF_ADMIN = "LOAN_PAID_OFF_ADMIN", "Loan Paid Off (Admin)"
        MANUAL_REMINDER = "MANUAL_REMINDER", "Manual Reminder"

    # The five REPAYMENT_DUE_* slot types recognised by process_due_sms's
    # daily reminder pass (Stage 11) — a subset used to validate/iterate
    # reminder windows without hard-coding the list at each call site.
    REMINDER_MESSAGE_TYPES = (
        "REPAYMENT_DUE_5_DAYS",
        "REPAYMENT_DUE_3_DAYS",
        "REPAYMENT_DUE_2_DAYS",
        "REPAYMENT_DUE_1_DAY",
        "REPAYMENT_DUE_TODAY_MORNING",
        "REPAYMENT_DUE_TODAY_AFTERNOON",
        "REPAYMENT_OVERDUE",
    )

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        SENT = "SENT", "Sent"
        DELIVERED = "DELIVERED", "Delivered"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sms_messages",
    )
    loan = models.ForeignKey(
        Loan, null=True, blank=True, on_delete=models.SET_NULL, related_name="sms_messages"
    )
    installment = models.ForeignKey(
        RepaymentInstallment,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sms_messages",
    )
    message_type = models.CharField(max_length=30, choices=MessageType.choices)
    recipient_phone_e164 = models.CharField(max_length=20)
    # The exact rendered text sent, kept for audit — never a template
    # reference alone (Section 26 forbids ambiguity about what was actually sent).
    message_body = models.TextField()
    scheduled_for = models.DateTimeField(null=True, blank=True)
    # The business date + slot a scheduled reminder was generated for —
    # distinct from `scheduled_for` (a precise timestamp) so the uniqueness
    # constraint below survives retries at different exact times.
    reminder_business_date = models.DateField(null=True, blank=True)
    reminder_slot = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider_message_id = models.CharField(max_length=100, blank=True)
    provider_response_code = models.CharField(max_length=20, blank=True)
    attempt_count = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    last_error_summary = models.TextField(blank=True)

    class Meta:
        constraints = [
            # Prevents a repeated scheduler run from duplicating the same
            # reminder (docs/DATA_MODEL.md Section 2.13). Manual/immediate
            # messages (no installment or no reminder_business_date) are
            # exempt and may repeat freely.
            models.UniqueConstraint(
                fields=["installment", "message_type", "reminder_business_date", "reminder_slot"],
                name="smsmessage_unique_scheduled_reminder",
                condition=models.Q(installment__isnull=False)
                & models.Q(reminder_business_date__isnull=False),
            ),
        ]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["scheduled_for"])]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.message_type} -> {self.recipient_phone_e164} ({self.status})"


class SMSSettings(BaseModel):
    """Admin-dashboard-editable SMS controls (a single row, same singleton
    pattern as `apps.repayments.models.RepaymentAccount`).

    `hubtel_enabled` here is a day-to-day pause/resume switch layered on
    top of the `HUBTEL_ENABLED`/`SMS_DRY_RUN` environment variables in
    `integrations.hubtel.get_sms_provider()` — real sending requires BOTH
    those env vars AND this flag, so a bug or a compromised admin account
    can never turn on real (paid) SMS sending without a server-level
    config change too (master prompt Section 17/20's "real sending must be
    impossible unless explicit environment configuration enables it").
    `morning_reminder_time`/`afternoon_reminder_time` replace the
    `SMS_DUE_MORNING_TIME`/`SMS_DUE_AFTERNOON_TIME` env vars outright —
    scheduling has no safety implication, so it's fully admin-editable.
    """

    singleton_key = models.CharField(max_length=10, default="default", unique=True, editable=False)
    hubtel_enabled = models.BooleanField(default=True)
    morning_reminder_time = models.TimeField(default=time(8, 0))
    afternoon_reminder_time = models.TimeField(default=time(16, 0))

    def __str__(self) -> str:
        return "SMS settings"

    @classmethod
    def get_solo(cls) -> "SMSSettings":
        obj, _ = cls.objects.get_or_create(singleton_key="default")
        return obj
