from decimal import Decimal

from rest_framework import serializers

from apps.loan_requests.models import LoanRequest
from common.masking import mask_tail

# In-flight statuses that block a second simultaneous request (Stage 6's
# "duplicate-submit protection"). Terminal statuses (rejected/declined/
# cancelled/converted) are deliberately excluded — a customer whose last
# request concluded is free to submit a new one.
_OPEN_REQUEST_STATUSES = (
    LoanRequest.Status.SUBMITTED,
    LoanRequest.Status.UNDER_REVIEW,
    LoanRequest.Status.OFFER_SENT,
    LoanRequest.Status.REVISION_REQUESTED,
    LoanRequest.Status.CUSTOMER_ACCEPTED,
)


class LoanRequestCreateSerializer(serializers.Serializer):
    """POST /api/v1/customer/loan-requests/ — write-only input shape.
    Eligibility (verified email, completed profile) and the payout snapshot
    are handled by the view, not here: they depend on request.user, not on
    anything in the request body (Section 14: "Use separate serializers for
    customer views, admin list views, admin details, and write actions").
    """

    requested_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01")
    )
    purpose = serializers.CharField()
    requested_term_count = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    requested_term_unit = serializers.ChoiceField(
        choices=LoanRequest.TermUnit.choices, required=False, allow_blank=True, default=""
    )
    customer_notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        customer = self.context["request"].user
        if LoanRequest.objects.filter(
            customer=customer, status__in=_OPEN_REQUEST_STATUSES
        ).exists():
            raise serializers.ValidationError(
                "You already have a loan request in progress. "
                "Cancel it before submitting a new one."
            )
        return attrs


class _CurrentOfferSummarySerializer(serializers.Serializer):
    """Minimal nested summary — the full offer (with its schedule) is only
    ever served by its own detail endpoint, never inlined wholesale here."""

    id = serializers.UUIDField()
    version_number = serializers.IntegerField()
    status = serializers.CharField()
    principal = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_repayable = serializers.DecimalField(max_digits=12, decimal_places=2)
    installment_count = serializers.IntegerField()
    sent_at = serializers.DateTimeField()


class _LoanSummarySerializer(serializers.Serializer):
    """Stage 8/9: once a request converts, the customer's own detail page
    links onward to `/loans/{id}` instead of showing offer/status chrome
    that no longer applies."""

    id = serializers.UUIDField()
    loan_number = serializers.CharField()
    status = serializers.CharField()


class LoanRequestSerializer(serializers.ModelSerializer):
    """Customer-facing list/detail serializer. Never includes
    `internal_notes` or `assigned_to` — those are staff-only (Section 12.3:
    "internal admin notes, never exposed to customers")."""

    current_offer = serializers.SerializerMethodField()
    loan = serializers.SerializerMethodField()

    class Meta:
        model = LoanRequest
        fields = [
            "id",
            "request_number",
            "requested_amount",
            "purpose",
            "requested_term_count",
            "requested_term_unit",
            "status",
            "submitted_at",
            "customer_notes",
            "current_offer",
            "loan",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_current_offer(self, obj: LoanRequest) -> dict | None:
        current = next((offer for offer in obj.offers.all() if offer.status == "SENT"), None)
        if current is None:
            return None
        return _CurrentOfferSummarySerializer(current).data

    def get_loan(self, obj: LoanRequest) -> dict | None:
        loan = getattr(obj, "loan", None)
        return _LoanSummarySerializer(loan).data if loan else None


class AdminLoanRequestListSerializer(serializers.ModelSerializer):
    """Staff queue serializer — matches the "New loan requests table" column
    spec (master prompt Section 16): request number, customer, amount,
    submission date, purpose, status, assigned officer."""

    customer_email = serializers.EmailField(source="customer.email", read_only=True)
    customer_name = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = LoanRequest
        fields = [
            "id",
            "request_number",
            "customer_email",
            "customer_name",
            "requested_amount",
            "purpose",
            "status",
            "submitted_at",
            "assigned_to_name",
            "created_at",
        ]
        read_only_fields = fields

    def get_customer_name(self, obj: LoanRequest) -> str:
        return obj.customer.get_full_name()

    def get_assigned_to_name(self, obj: LoanRequest) -> str:
        return obj.assigned_to.get_full_name() if obj.assigned_to else ""


class _OfferVersionSummarySerializer(serializers.Serializer):
    """One row of an admin's version history list — Stage 7's "previous
    versions are retained for audit" acceptance criterion."""

    id = serializers.UUIDField()
    version_number = serializers.IntegerField()
    status = serializers.CharField()
    principal = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_repayable = serializers.DecimalField(max_digits=12, decimal_places=2)
    created_at = serializers.DateTimeField()
    sent_at = serializers.DateTimeField(allow_null=True)


class AdminLoanRequestDetailSerializer(serializers.ModelSerializer):
    """Full staff view — includes internal_notes, payout_snapshot, and the
    complete offer version history (newest first, per LoanOffer.Meta.ordering)."""

    customer_email = serializers.EmailField(source="customer.email", read_only=True)
    customer_name = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()
    offers = _OfferVersionSummarySerializer(many=True, read_only=True)

    class Meta:
        model = LoanRequest
        fields = [
            "id",
            "request_number",
            "customer_email",
            "customer_name",
            "customer_phone",
            "requested_amount",
            "purpose",
            "requested_term_count",
            "requested_term_unit",
            "payout_snapshot",
            "status",
            "submitted_at",
            "assigned_to_name",
            "customer_notes",
            "internal_notes",
            "offers",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_customer_name(self, obj: LoanRequest) -> str:
        return obj.customer.get_full_name()

    def get_customer_phone(self, obj: LoanRequest) -> str:
        profile = getattr(obj.customer, "customer_profile", None)
        return profile.phone_number_e164 if profile else ""

    def get_assigned_to_name(self, obj: LoanRequest) -> str:
        return obj.assigned_to.get_full_name() if obj.assigned_to else ""


class DeclineLoanRequestSerializer(serializers.Serializer):
    reason = serializers.CharField()


def build_payout_snapshot(profile) -> dict:
    """Section 12.3: "payout details snapshot ... safely". Captures method +
    a masked destination only — the authoritative, unmasked details always
    live on CustomerProfile (Section 26: never duplicate a sensitive value
    into a second place at rest)."""
    if profile.preferred_disbursement_method == profile.DisbursementMethod.MOBILE_MONEY:
        destination = mask_tail(profile.mobile_money_number)
    else:
        destination = mask_tail(profile.bank_account_number)
    return {
        "method": profile.preferred_disbursement_method,
        "destination_masked": destination,
    }
