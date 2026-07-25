from rest_framework import generics, permissions
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

import apps.repayments.services as repayment_services
from apps.audit.services import record_event
from apps.loans.models import Loan, RepaymentInstallment
from apps.repayments.models import Payment, PaymentClaim, RepaymentAccount
from apps.repayments.serializers import (
    ClaimPaymentSerializer,
    PaymentClaimSerializer,
    PaymentSerializer,
    RecordPaymentSerializer,
    RepaymentAccountSerializer,
    ReversePaymentSerializer,
)
from common.permissions import (
    FINANCE_OFFICER,
    LOAN_OFFICER,
    STAFF_ROLES,
    SUPER_ADMIN,
    has_any_role,
)
from integrations.storage.backends import get_storage


class AdminLoanRepaymentListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/v1/admin/loans/{id}/repayments/ — Stage 10's "repayment
    entry modal and API" plus payment history. Read is open to every staff
    role (Section 10: auditors are read-only); recording a payment is
    finance-officer-only, matching docs/STATUS_TRANSITIONS.md's Payment
    table."""

    serializer_class = PaymentSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), has_any_role(FINANCE_OFFICER, SUPER_ADMIN)()]
        return [permissions.IsAuthenticated(), has_any_role(*STAFF_ROLES)()]

    def get_queryset(self):
        return Payment.objects.filter(loan_id=self.kwargs["pk"]).select_related("recorded_by")

    def post(self, request, pk):
        loan = generics.get_object_or_404(Loan, pk=pk)
        serializer = RecordPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        evidence_file = data.get("evidence_file")
        evidence_file_path = ""
        if evidence_file is not None:
            evidence_file_path = get_storage().save(
                evidence_file.read(), subdir="payment_evidence", original_name=evidence_file.name
            )

        payment = repayment_services.record_payment(
            loan,
            amount=data["amount"],
            payment_date=data["payment_date"],
            payment_method=data["payment_method"],
            recorded_by=request.user,
            external_transaction_reference=data.get("external_transaction_reference", ""),
            evidence_file_path=evidence_file_path,
            notes=data.get("notes", ""),
            idempotency_key=data.get("idempotency_key", ""),
        )
        return Response(PaymentSerializer(payment).data, status=201)


class AdminPaymentReverseView(APIView):
    """POST /api/v1/admin/repayments/{id}/reverse/ — Stage 10: "Implement
    payment reversal with reason and role protection."""

    permission_classes = [permissions.IsAuthenticated, has_any_role(FINANCE_OFFICER, SUPER_ADMIN)]

    def post(self, request, pk):
        payment = generics.get_object_or_404(Payment, pk=pk)
        serializer = ReversePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment = repayment_services.reverse_payment(
            payment, actor=request.user, reason=serializer.validated_data["reason"]
        )
        return Response(PaymentSerializer(payment).data)


class CustomerInstallmentClaimView(APIView):
    """POST /api/v1/customer/installments/{id}/claim-payment/ — the customer
    "I've paid" action. Informational only; ownership is filtered into the
    lookup itself (a foreign installment 404s, never 403s — no existence
    leak)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        installment = generics.get_object_or_404(
            RepaymentInstallment.objects.select_related("loan").filter(loan__customer=request.user),
            pk=pk,
        )
        serializer = ClaimPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        claim = repayment_services.claim_payment(
            installment, customer=request.user, note=serializer.validated_data["note"]
        )
        return Response(PaymentClaimSerializer(claim).data, status=201)


class AdminPaymentClaimListView(generics.ListAPIView):
    """GET /api/v1/admin/payment-claims/?status=PENDING — the claims queue
    behind the dashboard's "Customer payment claims" card."""

    serializer_class = PaymentClaimSerializer
    permission_classes = [permissions.IsAuthenticated, has_any_role(*STAFF_ROLES)]
    filterset_fields = ["status"]

    def get_queryset(self):
        return PaymentClaim.objects.select_related("customer", "loan", "installment", "resolved_by")


class AdminPaymentClaimResolveView(APIView):
    """POST /api/v1/admin/payment-claims/{id}/resolve/ — manual close-out
    for claims with no matching payment (recording the real payment
    auto-resolves instead)."""

    permission_classes = [
        permissions.IsAuthenticated,
        has_any_role(LOAN_OFFICER, FINANCE_OFFICER, SUPER_ADMIN),
    ]

    def post(self, request, pk):
        claim = generics.get_object_or_404(
            PaymentClaim.objects.select_related("customer", "loan", "installment"), pk=pk
        )
        claim = repayment_services.resolve_payment_claim(claim, actor=request.user)
        return Response(PaymentClaimSerializer(claim).data)


class RepaymentAccountView(APIView):
    """GET /api/v1/repayment-account/ — the company collection account any
    signed-in customer can read (they need the full number to pay into it)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(RepaymentAccountSerializer(RepaymentAccount.get_solo()).data)


class AdminRepaymentAccountView(APIView):
    """GET/PUT /api/v1/admin/repayment-account/ — the settings form behind
    /admin/settings. Any staff role may read; only the SUPER_ADMIN may
    change where customer money is directed (and every change is audited)."""

    def get_permissions(self):
        if self.request.method == "PUT":
            return [permissions.IsAuthenticated(), has_any_role(SUPER_ADMIN)()]
        return [permissions.IsAuthenticated(), has_any_role(*STAFF_ROLES)()]

    def get(self, request):
        return Response(RepaymentAccountSerializer(RepaymentAccount.get_solo()).data)

    def put(self, request):
        account = RepaymentAccount.get_solo()
        serializer = RepaymentAccountSerializer(instance=account, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        record_event(
            actor=request.user,
            action="repayment_account.update",
            entity=account,
            after={
                "mobile_money_number": account.mobile_money_number,
                "bank_account_number": account.bank_account_number,
            },
        )
        return Response(serializer.data)
