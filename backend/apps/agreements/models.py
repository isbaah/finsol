from django.conf import settings
from django.db import models

from apps.loan_offers.models import LoanOffer
from common.db.models import BaseModel


class Agreement(BaseModel):
    """See docs/DATA_MODEL.md Section 2.6. Model shape only this stage —
    signature capture, PDF generation (WeasyPrint), and hashing are Stage 8
    tasks; this stage just proves the schema and its immutability guarantee.

    Immutable after creation, with one deliberate exception: the email
    delivery bookkeeping fields (`email_delivery_status`,
    `email_provider_reference`) are updatable, since Stage 8 explicitly adds
    an admin retry action for a failed agreement email — everything else
    (the actual acceptance evidence) never changes once recorded.
    """

    class EmailDeliveryStatus(models.TextChoices):
        NOT_SENT = "NOT_SENT", "Not Sent"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"

    offer = models.OneToOneField(LoanOffer, on_delete=models.PROTECT, related_name="agreement")
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="agreements"
    )
    typed_legal_name = models.CharField(max_length=255)
    acceptance_text_version = models.CharField(max_length=20)
    acceptance_text_snapshot = models.TextField()
    signature_image_path = models.CharField(max_length=500, blank=True)
    signature_image_sha256 = models.CharField(max_length=64, blank=True)
    agreement_pdf_path = models.CharField(max_length=500, blank=True)
    agreement_pdf_sha256 = models.CharField(max_length=64, blank=True)
    accepted_ip_address = models.GenericIPAddressField(null=True, blank=True)
    accepted_user_agent = models.TextField(blank=True)
    accepted_at = models.DateTimeField()
    email_delivery_status = models.CharField(
        max_length=10, choices=EmailDeliveryStatus.choices, default=EmailDeliveryStatus.NOT_SENT
    )
    email_provider_reference = models.CharField(max_length=255, blank=True)

    _MUTABLE_AFTER_CREATE = {"email_delivery_status", "email_provider_reference", "updated_at"}

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Agreement<{self.offer_id}>"

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                current = Agreement.objects.get(pk=self.pk)
            except Agreement.DoesNotExist:
                current = None
            if current is not None:
                immutable_fields = [
                    field.name
                    for field in self._meta.fields
                    if field.name not in self._MUTABLE_AFTER_CREATE and field.name != "id"
                ]
                changed = [
                    field
                    for field in immutable_fields
                    if getattr(current, field) != getattr(self, field)
                ]
                if changed:
                    raise ValueError(
                        f"Agreement records are immutable except delivery-status "
                        f"fields; cannot change {changed}."
                    )
        super().save(*args, **kwargs)
