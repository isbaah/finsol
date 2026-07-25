from django.db.models import F
from django.db.models.functions import Collate
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

import apps.loans.services as loan_services
from apps.audit.services import record_event
from apps.customers.serializers import CustomerProfileSerializer
from apps.loans.filters import LoanFilter
from apps.loans.models import Loan
from apps.loans.serializers import (
    AdminLoanDetailSerializer,
    AdminLoanListSerializer,
    CustomerLoanSerializer,
    DisbursementCreateSerializer,
)
from common.api.request import get_client_ip, get_user_agent
from common.permissions import (
    APPROVER,
    FINANCE_OFFICER,
    STAFF_ROLES,
    SUPER_ADMIN,
    IsOwner,
    has_any_role,
)
from integrations.storage.backends import get_storage


class AdminLoanListView(generics.ListAPIView):
    """GET /api/v1/admin/loans/ — read access for every staff role (Section
    10: auditors have read-only access to operational records); approval
    and disbursement actions below are restricted further."""

    serializer_class = AdminLoanListSerializer
    permission_classes = [permissions.IsAuthenticated, has_any_role(*STAFF_ROLES)]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = LoanFilter
    # Same nondeterministic-collation workaround as
    # apps/loan_requests/views.py::AdminLoanRequestListView.
    search_fields = [
        "loan_number",
        "customer_email_ci",
        "customer__first_name",
        "customer__last_name",
    ]
    ordering_fields = ["created_at", "approved_at", "disbursed_at", "principal"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Loan.objects.select_related("customer", "loan_request").annotate(
            customer_email_ci=Collate(F("customer__email"), "C")
        )


class AdminLoanDetailView(generics.RetrieveAPIView):
    serializer_class = AdminLoanDetailSerializer
    permission_classes = [permissions.IsAuthenticated, has_any_role(*STAFF_ROLES)]
    queryset = Loan.objects.select_related(
        "customer", "customer__customer_profile", "loan_request", "agreement", "approved_by"
    ).prefetch_related("installments", "disbursements")


class AdminLoanApproveView(generics.GenericAPIView):
    """POST /api/v1/admin/loans/{id}/approve/ — Stage 9: "Build approval
    action for authorised approvers." Role-separated from disbursement
    (Section 10: "Approvers can approve accepted loans" /
    "Finance officers can record disbursements")."""

    serializer_class = AdminLoanDetailSerializer
    permission_classes = [permissions.IsAuthenticated, has_any_role(APPROVER, SUPER_ADMIN)]
    queryset = Loan.objects.all()

    def post(self, request, pk):
        loan = self.get_object()
        loan = loan_services.approve_loan(loan, approver=request.user)
        return Response(AdminLoanDetailSerializer(loan).data)


class AdminLoanDisburseView(generics.GenericAPIView):
    """POST /api/v1/admin/loans/{id}/disburse/ — Stage 9's disbursement
    modal. Finance-officer-only; the amount/status/duplicate checks all
    live in apps/loans/services.py::record_disbursement() (a DomainError
    subclass -> 409 for every rejection reason, per this codebase's
    established pattern)."""

    serializer_class = DisbursementCreateSerializer
    permission_classes = [permissions.IsAuthenticated, has_any_role(FINANCE_OFFICER, SUPER_ADMIN)]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    queryset = Loan.objects.select_related("loan_request", "accepted_offer")

    def post(self, request, pk):
        loan = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        evidence_file = data.get("evidence_file")
        evidence_file_path = ""
        if evidence_file is not None:
            evidence_file_path = get_storage().save(
                evidence_file.read(),
                subdir="disbursement_evidence",
                original_name=evidence_file.name,
            )

        loan_services.record_disbursement(
            loan,
            recorded_by=request.user,
            amount=data["amount"],
            method=data["method"],
            external_transaction_reference=data.get("external_transaction_reference", ""),
            evidence_file_path=evidence_file_path,
            notes=data.get("notes", ""),
        )
        loan.refresh_from_db()
        return Response(AdminLoanDetailSerializer(loan).data)


class LoanPayoutDetailsRevealView(APIView):
    """GET /api/v1/admin/loans/{id}/payout-details/ — Stage 9: "Implement
    authorised payout-detail reveal and audit event." Finance-officer-only;
    every reveal is logged, without ever putting the raw account digits
    into the audit JSON itself (Section 20)."""

    permission_classes = [permissions.IsAuthenticated, has_any_role(FINANCE_OFFICER, SUPER_ADMIN)]

    def get(self, request, pk):
        loan = generics.get_object_or_404(
            Loan.objects.select_related("customer", "customer__customer_profile"), pk=pk
        )
        profile = getattr(loan.customer, "customer_profile", None)
        if profile is None:
            return Response({"detail": "No payout profile on file."}, status=404)

        record_event(
            actor=request.user,
            action="customer_profile.payout_details_reveal",
            entity=profile,
            after={"method": profile.preferred_disbursement_method, "loan_id": str(loan.pk)},
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        return Response(CustomerProfileSerializer(profile).data)


class CustomerLoanListView(generics.ListAPIView):
    """GET /api/v1/customer/loans/ — the customer's own loans, newest first.
    Added in Stage 12 for the customer dashboard's active-loan summary
    (Section 15), which needs to find the loan without already knowing its
    id. Reuses CustomerLoanSerializer (schedule + payments included) — a
    customer only ever has a handful of loans, so the payload stays small."""

    serializer_class = CustomerLoanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Loan.objects.filter(customer=self.request.user)
            .select_related("loan_request", "agreement")
            .prefetch_related("installments")
        )


class CustomerLoanDetailView(generics.RetrieveAPIView):
    """GET /api/v1/customer/loans/{id}/ — lets the customer track their
    loan's status/schedule after acceptance without exposing anything
    staff-only."""

    serializer_class = CustomerLoanSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    queryset = Loan.objects.select_related("loan_request", "agreement").prefetch_related(
        "installments"
    )
