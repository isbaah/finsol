from decimal import Decimal

from rest_framework import serializers

from apps.loans.models import Disbursement, Loan, RepaymentInstallment
from apps.repayments.serializers import CustomerPaymentSerializer, PaymentSerializer


class RepaymentInstallmentSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = RepaymentInstallment
        fields = [
            "id",
            "sequence_number",
            "due_date",
            "principal_due",
            "interest_due",
            "total_due",
            "amount_paid",
            "outstanding_amount",
            "status",
        ]
        read_only_fields = fields


class DisbursementSerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Disbursement
        fields = [
            "id",
            "amount",
            "method",
            "masked_payout_snapshot",
            "external_transaction_reference",
            "notes",
            "recorded_by_name",
            "recorded_at",
        ]
        read_only_fields = fields

    def get_recorded_by_name(self, obj: Disbursement) -> str:
        return obj.recorded_by.get_full_name()


class AdminLoanListSerializer(serializers.ModelSerializer):
    customer_email = serializers.EmailField(source="customer.email", read_only=True)
    customer_name = serializers.SerializerMethodField()
    request_number = serializers.CharField(source="loan_request.request_number", read_only=True)

    class Meta:
        model = Loan
        fields = [
            "id",
            "loan_number",
            "request_number",
            "customer_email",
            "customer_name",
            "status",
            "principal",
            "total_repayable",
            "amount_disbursed",
            "outstanding_balance",
            "approved_at",
            "disbursed_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_customer_name(self, obj: Loan) -> str:
        return obj.customer.get_full_name()


class AdminLoanDetailSerializer(serializers.ModelSerializer):
    """Staff-facing full detail — the masked payout snapshot only (Section
    26: unmasked payout digits are never returned by a general-purpose
    endpoint; use the dedicated reveal action for that, which is itself
    audited)."""

    customer_email = serializers.EmailField(source="customer.email", read_only=True)
    customer_name = serializers.SerializerMethodField()
    customer_phone = serializers.SerializerMethodField()
    request_number = serializers.CharField(source="loan_request.request_number", read_only=True)
    approved_by_name = serializers.SerializerMethodField()
    installments = RepaymentInstallmentSummarySerializer(many=True, read_only=True)
    disbursement = serializers.SerializerMethodField()
    agreement_id = serializers.UUIDField(source="agreement.id", read_only=True)
    payments = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = [
            "id",
            "loan_number",
            "request_number",
            "customer_email",
            "customer_name",
            "customer_phone",
            "status",
            "principal",
            "total_interest",
            "total_repayable",
            "amount_disbursed",
            "amount_repaid",
            "outstanding_balance",
            "approved_by_name",
            "approved_at",
            "disbursed_at",
            "closed_at",
            "agreement_id",
            "disbursement",
            "installments",
            "payments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_customer_name(self, obj: Loan) -> str:
        return obj.customer.get_full_name()

    def get_customer_phone(self, obj: Loan) -> str:
        profile = getattr(obj.customer, "customer_profile", None)
        return profile.phone_number_e164 if profile else ""

    def get_approved_by_name(self, obj: Loan) -> str:
        return obj.approved_by.get_full_name() if obj.approved_by else ""

    def get_disbursement(self, obj: Loan) -> dict | None:
        disbursement = obj.disbursements.first()
        return DisbursementSerializer(disbursement).data if disbursement else None

    def get_payments(self, obj: Loan) -> list[dict]:
        return PaymentSerializer(obj.payments.select_related("recorded_by"), many=True).data


class CustomerLoanSerializer(serializers.ModelSerializer):
    """GET /api/v1/customer/loans/{id}/ — never includes the payout
    snapshot or anything staff-only (internal notes, approver identity)."""

    request_number = serializers.CharField(source="loan_request.request_number", read_only=True)
    agreement_id = serializers.UUIDField(source="agreement.id", read_only=True)
    installments = RepaymentInstallmentSummarySerializer(many=True, read_only=True)
    payments = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = [
            "id",
            "loan_number",
            "request_number",
            "status",
            "principal",
            "total_interest",
            "total_repayable",
            "amount_disbursed",
            "amount_repaid",
            "outstanding_balance",
            "approved_at",
            "disbursed_at",
            "agreement_id",
            "installments",
            "payments",
            "created_at",
        ]
        read_only_fields = fields

    def get_payments(self, obj: Loan) -> list[dict]:
        return CustomerPaymentSerializer(obj.payments.filter(status="POSTED"), many=True).data


class DisbursementCreateSerializer(serializers.Serializer):
    """POST /api/v1/admin/loans/{id}/disburse/ — Stage 9's "disbursement
    modal". `amount`/`method` are validated against the loan itself (exact
    match to `Loan.principal`) in the service layer, not here — the
    serializer only checks shape."""

    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    method = serializers.ChoiceField(choices=Disbursement.Method.choices)
    external_transaction_reference = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    evidence_file = serializers.FileField(required=False, allow_null=True)
