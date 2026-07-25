from decimal import Decimal

from rest_framework import serializers

from apps.loan_offers.models import MAX_TERM_COUNT, LoanOffer, OfferInstallment


class AmortizationPreviewRequestSerializer(serializers.Serializer):
    """Input shape for POST /api/v1/admin/offers/preview/. Mirrors
    AmortizationInput — a second, HTTP-layer validation pass in front of
    the domain-authoritative checks in apps/loan_offers/amortization.py's
    calculate() (Section 14: "Validate on both frontend and backend, with
    backend authoritative" — here both layers are backend, since
    calculate() is also called from non-HTTP contexts).
    """

    principal = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    interest_rate_percent = serializers.DecimalField(
        max_digits=6, decimal_places=2, min_value=Decimal("0")
    )
    term_count = serializers.IntegerField(min_value=1, max_value=MAX_TERM_COUNT)
    term_unit = serializers.ChoiceField(choices=LoanOffer.TermUnit.choices)
    first_due_date = serializers.DateField()


class AmortizationInstallmentSerializer(serializers.Serializer):
    sequence_number = serializers.IntegerField()
    due_date = serializers.DateField()
    principal_due = serializers.DecimalField(max_digits=12, decimal_places=2)
    interest_due = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_due = serializers.DecimalField(max_digits=12, decimal_places=2)


class AmortizationPreviewResponseSerializer(serializers.Serializer):
    total_interest = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_repayable = serializers.DecimalField(max_digits=12, decimal_places=2)
    installment_count = serializers.IntegerField()
    installments = AmortizationInstallmentSerializer(many=True)


class OfferWriteSerializer(AmortizationPreviewRequestSerializer):
    """POST /api/v1/admin/loan-requests/{id}/offers/ and PATCH
    /api/v1/admin/offers/{id}/ — deliberately the same input shape as the
    Stage 5 preview request plus the fields the preview never needed. Totals
    and installments are never accepted from the client: the view always
    recomputes them by calling the same calculate() the preview endpoint
    uses, so a persisted offer can never drift from what an officer saw on
    screen (Stage 5's "preview and persist parity" guarantee, extended to
    real creation).
    """

    offer_expiry_date = serializers.DateField(required=False, allow_null=True)
    customer_terms = serializers.CharField(required=False, allow_blank=True, default="")
    internal_notes = serializers.CharField(required=False, allow_blank=True, default="")


class OfferInstallmentModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfferInstallment
        fields = ["sequence_number", "due_date", "principal_due", "interest_due", "total_due"]
        read_only_fields = fields


class AdminOfferDetailSerializer(serializers.ModelSerializer):
    """Staff-facing offer serializer — every field, including
    `internal_notes` (never sent to a customer)."""

    installments = OfferInstallmentModelSerializer(many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = LoanOffer
        fields = [
            "id",
            "loan_request",
            "version_number",
            "status",
            "principal",
            "interest_method",
            "interest_rate_percent",
            "term_count",
            "term_unit",
            "first_due_date",
            "total_interest",
            "total_repayable",
            "installment_count",
            "offer_expiry_date",
            "customer_terms",
            "internal_notes",
            "created_by_name",
            "sent_at",
            "accepted_at",
            "installments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_created_by_name(self, obj: LoanOffer) -> str:
        return obj.created_by.get_full_name()


class AcceptOfferSerializer(serializers.Serializer):
    """POST /api/v1/customer/offers/{id}/accept/ — Stage 8's signature
    experience (master prompt Section 15): typed legal name, a versioned
    acceptance checkbox, and a drawn signature image. The signature itself
    is decoded/validated by apps/agreements/services.py::
    validate_signature_image(), not here — that validation raises a
    DomainError (409), consistent with every other business-rule check in
    this codebase, rather than a plain 400 field error.
    """

    typed_legal_name = serializers.CharField(min_length=2, max_length=255, trim_whitespace=True)
    declaration_accepted = serializers.BooleanField()
    signature_image = serializers.CharField()

    def validate_declaration_accepted(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError("You must confirm the acceptance declaration.")
        return value


class RejectOfferSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class RequestRevisionSerializer(serializers.Serializer):
    """A revision request without a reason gives the officer nothing to act
    on, so — unlike a plain rejection — a reason is required here."""

    reason = serializers.CharField(min_length=1)


class CustomerOfferSerializer(serializers.ModelSerializer):
    """Customer-facing offer serializer (Stage 7's read-only "offer review
    page" — see master prompt Section 15's field list). Never includes
    `internal_notes`, `created_by`, or `sent_by`."""

    installments = OfferInstallmentModelSerializer(many=True, read_only=True)
    request_number = serializers.CharField(source="loan_request.request_number", read_only=True)
    loan_request_id = serializers.UUIDField(source="loan_request.id", read_only=True)

    class Meta:
        model = LoanOffer
        fields = [
            "id",
            "request_number",
            "loan_request_id",
            "version_number",
            "status",
            "principal",
            "interest_rate_percent",
            "term_count",
            "term_unit",
            "first_due_date",
            "total_interest",
            "total_repayable",
            "installment_count",
            "offer_expiry_date",
            "customer_terms",
            "sent_at",
            "installments",
        ]
        read_only_fields = fields
