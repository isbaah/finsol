from django.conf import settings
from django.db import models
from django.db.models import Q

from common.db.models import BaseModel


class CustomerProfile(BaseModel):
    """See docs/DATA_MODEL.md Section 2.2. One row per customer, created in
    full by the onboarding flow (apps/customers/views.py's MyProfileView) —
    there is no "empty draft" state reachable through the API, only through
    a direct ORM write, which is what the CHECK constraint below actually
    guards against.
    """

    class DisbursementMethod(models.TextChoices):
        MOBILE_MONEY = "MOBILE_MONEY", "Mobile Money"
        BANK = "BANK", "Bank"

    class MobileMoneyNetwork(models.TextChoices):
        MTN = "MTN", "MTN Mobile Money"
        TELECEL = "TELECEL", "Telecel Cash"
        AIRTELTIGO = "AIRTELTIGO", "AirtelTigo Money"
        OTHER = "OTHER", "Other"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="customer_profile"
    )
    phone_number_e164 = models.CharField(max_length=20)
    phone_country_code = models.CharField(max_length=4)
    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    # Ghana-only for the MVP (docs/PRODUCT_ASSUMPTIONS.md Section 1). Kept as
    # a real field rather than hard-coded so a later multi-country expansion
    # doesn't need a schema change, but the onboarding UI doesn't expose it.
    country = models.CharField(max_length=2, default="GH")
    preferred_disbursement_method = models.CharField(
        max_length=20, choices=DisbursementMethod.choices
    )
    mobile_money_network = models.CharField(
        max_length=20, choices=MobileMoneyNetwork.choices, blank=True
    )
    mobile_money_number = models.CharField(max_length=20, blank=True)
    bank_name = models.CharField(max_length=150, blank=True)
    bank_account_name = models.CharField(max_length=150, blank=True)
    bank_account_number = models.CharField(max_length=34, blank=True)
    profile_completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "customer profile"
        verbose_name_plural = "customer profiles"
        constraints = [
            # Once a profile is marked completed, the fields required by its
            # chosen payout method must be present — enforced at the
            # database level, not only in the serializer (Section 26: "DO
            # NOT rely only on application validation where a database
            # constraint can protect the invariant"). An incomplete row
            # (profile_completed_at IS NULL) is exempt, since the ORM has no
            # partial-save path today but a future one shouldn't need a
            # migration to be allowed.
            models.CheckConstraint(
                condition=(
                    Q(profile_completed_at__isnull=True)
                    | (
                        Q(preferred_disbursement_method="MOBILE_MONEY")
                        & ~Q(mobile_money_network="")
                        & ~Q(mobile_money_number="")
                    )
                    | (
                        Q(preferred_disbursement_method="BANK")
                        & ~Q(bank_name="")
                        & ~Q(bank_account_name="")
                        & ~Q(bank_account_number="")
                    )
                ),
                name="customerprofile_payout_fields_required_when_completed",
            ),
        ]

    def __str__(self) -> str:
        return f"CustomerProfile<{self.user_id}>"
