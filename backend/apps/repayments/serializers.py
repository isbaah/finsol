from decimal import Decimal

from rest_framework import serializers

from apps.repayments.models import Payment, PaymentAllocation, PaymentClaim, RepaymentAccount


class PaymentAllocationSerializer(serializers.ModelSerializer):
    installment_sequence_number = serializers.IntegerField(
        source="installment.sequence_number", read_only=True
    )

    class Meta:
        model = PaymentAllocation
        fields = [
            "installment_sequence_number",
            "principal_amount",
            "interest_amount",
            "total_amount",
        ]
        read_only_fields = fields


class PaymentSerializer(serializers.ModelSerializer):
    """Staff-facing payment history row — includes who recorded it and any
    reversal detail. `CustomerPaymentSerializer` below is the same shape
    minus staff-only identity fields."""

    recorded_by_name = serializers.SerializerMethodField()
    allocations = PaymentAllocationSerializer(many=True, read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "receipt_number",
            "amount",
            "payment_date",
            "payment_method",
            "external_transaction_reference",
            "notes",
            "status",
            "reversal_reason",
            "recorded_by_name",
            "recorded_at",
            "allocations",
            "created_at",
        ]
        read_only_fields = fields

    def get_recorded_by_name(self, obj: Payment) -> str:
        return obj.recorded_by.get_full_name()


class CustomerPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "receipt_number",
            "amount",
            "payment_date",
            "payment_method",
            "status",
            "created_at",
        ]
        read_only_fields = fields


class RecordPaymentSerializer(serializers.Serializer):
    """POST /api/v1/admin/loans/{id}/repayments/ — Section 16's "Payment
    modal". The backend recalculates the authoritative allocation/balance;
    this only validates shape (amount vs. outstanding balance is a
    service-layer check, since it needs a locked, current read of the
    loan)."""

    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    payment_date = serializers.DateField()
    payment_method = serializers.ChoiceField(choices=Payment.Method.choices)
    external_transaction_reference = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    evidence_file = serializers.FileField(required=False, allow_null=True)
    # Client-generated (e.g. a UUID minted once per form submission) so a
    # double-click or retried request is a no-op rather than a second
    # payment — Section 20/26's "double-submit protection".
    idempotency_key = serializers.CharField(required=False, allow_blank=True, default="")


class ReversePaymentSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=1)


class RepaymentAccountSerializer(serializers.ModelSerializer):
    """The company collection account. Same shape for the customer's
    read-only view and the super admin's settings form."""

    class Meta:
        model = RepaymentAccount
        fields = [
            "mobile_money_network",
            "mobile_money_number",
            "mobile_money_account_name",
            "bank_name",
            "bank_account_name",
            "bank_account_number",
            "payment_instructions",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]


class ClaimPaymentSerializer(serializers.Serializer):
    """POST /api/v1/customer/installments/{id}/claim-payment/ body."""

    note = serializers.CharField(required=False, allow_blank=True, default="", max_length=500)


class PaymentClaimSerializer(serializers.ModelSerializer):
    """Both the customer's confirmation response and the staff claims-queue
    row — nothing here is sensitive beyond what each side already sees."""

    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.EmailField(source="customer.email", read_only=True)
    loan_number = serializers.CharField(source="loan.loan_number", read_only=True)
    sequence_number = serializers.IntegerField(source="installment.sequence_number", read_only=True)
    due_date = serializers.DateField(source="installment.due_date", read_only=True)
    outstanding_amount = serializers.DecimalField(
        source="installment.outstanding_amount", max_digits=12, decimal_places=2, read_only=True
    )
    resolved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PaymentClaim
        fields = [
            "id",
            "loan_id",
            "loan_number",
            "sequence_number",
            "due_date",
            "outstanding_amount",
            "customer_name",
            "customer_email",
            "note",
            "status",
            "resolved_by_name",
            "resolved_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_customer_name(self, obj: PaymentClaim) -> str:
        return obj.customer.get_full_name()

    def get_resolved_by_name(self, obj: PaymentClaim) -> str:
        return obj.resolved_by.get_full_name() if obj.resolved_by else ""
