from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

import apps.agreements.services as agreement_services
import apps.loan_offers.services as offer_services
from apps.agreements.serializers import AcceptOfferResultSerializer
from apps.loan_offers.amortization import AmortizationError, AmortizationInput, calculate
from apps.loan_offers.models import LoanOffer
from apps.loan_offers.serializers import (
    AcceptOfferSerializer,
    AdminOfferDetailSerializer,
    AmortizationPreviewRequestSerializer,
    AmortizationPreviewResponseSerializer,
    CustomerOfferSerializer,
    OfferWriteSerializer,
    RejectOfferSerializer,
    RequestRevisionSerializer,
)
from apps.loan_requests.models import LoanRequest
from common.api.request import get_client_ip, get_user_agent
from common.permissions import LOAN_OFFICER, SUPER_ADMIN, IsOwner, has_any_role


def _run_calculation(data: dict):
    """Shared by every view that creates or edits a real offer — the exact
    same calculate() the /preview/ endpoint uses, so a persisted offer can
    never diverge from what an officer saw on screen (Stage 5's "preview
    and persist parity" guarantee, extended to real creation/editing).
    """
    try:
        return calculate(
            AmortizationInput(
                principal=data["principal"],
                interest_rate_percent=data["interest_rate_percent"],
                term_count=data["term_count"],
                term_unit=data["term_unit"],
                first_due_date=data["first_due_date"],
            )
        )
    except AmortizationError as exc:
        raise serializers.ValidationError({"detail": str(exc)}) from exc


def _installments_payload(result) -> list[dict]:
    return [
        {
            "sequence_number": line.sequence_number,
            "due_date": line.due_date,
            "principal_due": line.principal_due,
            "interest_due": line.interest_due,
            "total_due": line.total_due,
        }
        for line in result.installments
    ]


class AmortizationPreviewView(APIView):
    """POST /api/v1/admin/offers/preview/ — authorised admins only (Section
    24, Stage 5: "Create an API preview endpoint for authorised admins").

    Calls the exact same calculate() function that
    apps/loan_offers/services.py::create_offer_with_schedule() uses to
    persist a real offer, so preview and persisted numbers can never drift
    apart (Stage 5's acceptance criterion). Nothing is written to the
    database here — no LoanOffer, no OfferInstallment.
    """

    permission_classes = [permissions.IsAuthenticated, has_any_role(LOAN_OFFICER, SUPER_ADMIN)]

    def post(self, request):
        request_serializer = AmortizationPreviewRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        data = request_serializer.validated_data

        try:
            result = calculate(
                AmortizationInput(
                    principal=data["principal"],
                    interest_rate_percent=data["interest_rate_percent"],
                    term_count=data["term_count"],
                    term_unit=data["term_unit"],
                    first_due_date=data["first_due_date"],
                )
            )
        except AmortizationError as exc:
            return Response({"detail": str(exc)}, status=400)

        payload = {
            "total_interest": result.total_interest,
            "total_repayable": result.total_repayable,
            "installment_count": result.installment_count,
            "installments": [
                {
                    "sequence_number": line.sequence_number,
                    "due_date": line.due_date,
                    "principal_due": line.principal_due,
                    "interest_due": line.interest_due,
                    "total_due": line.total_due,
                }
                for line in result.installments
            ],
        }
        return Response(AmortizationPreviewResponseSerializer(payload).data)


class AdminOfferCreateView(generics.GenericAPIView):
    """POST /api/v1/admin/loan-requests/{id}/offers/ — Stage 7: "Build offer
    form using the amortization preview service. Persist offer and offer
    installments atomically." Always creates the next DRAFT version; see
    apps/loan_offers/services.py::create_offer_with_schedule()."""

    serializer_class = OfferWriteSerializer
    permission_classes = [permissions.IsAuthenticated, has_any_role(LOAN_OFFICER, SUPER_ADMIN)]

    def post(self, request, pk):
        loan_request = get_object_or_404(LoanRequest, pk=pk)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result = _run_calculation(data)
        offer = offer_services.create_offer_with_schedule(
            loan_request,
            officer=request.user,
            principal=data["principal"],
            interest_rate_percent=data["interest_rate_percent"],
            term_count=data["term_count"],
            term_unit=data["term_unit"],
            first_due_date=data["first_due_date"],
            total_interest=result.total_interest,
            total_repayable=result.total_repayable,
            installment_count=result.installment_count,
            installments=_installments_payload(result),
            offer_expiry_date=data.get("offer_expiry_date"),
            customer_terms=data.get("customer_terms", ""),
            internal_notes=data.get("internal_notes", ""),
        )
        return Response(AdminOfferDetailSerializer(offer).data, status=status.HTTP_201_CREATED)


class AdminOfferDetailView(generics.GenericAPIView):
    """GET /api/v1/admin/offers/{id}/ — full detail for the offer-edit form.
    PATCH — Stage 7: "Allow draft editing before send"; only reachable while
    the offer is still DRAFT (apps/loan_offers/services.py::update_draft_offer()
    raises OfferNotEditableError otherwise, mapped to 409 by the global
    exception handler)."""

    serializer_class = AdminOfferDetailSerializer
    permission_classes = [permissions.IsAuthenticated, has_any_role(LOAN_OFFICER, SUPER_ADMIN)]
    queryset = LoanOffer.objects.select_related("loan_request", "created_by").prefetch_related(
        "installments"
    )

    def get(self, request, pk):
        return Response(AdminOfferDetailSerializer(self.get_object()).data)

    def patch(self, request, pk):
        offer = self.get_object()
        serializer = OfferWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result = _run_calculation(data)
        offer = offer_services.update_draft_offer(
            offer,
            officer=request.user,
            principal=data["principal"],
            interest_rate_percent=data["interest_rate_percent"],
            term_count=data["term_count"],
            term_unit=data["term_unit"],
            first_due_date=data["first_due_date"],
            total_interest=result.total_interest,
            total_repayable=result.total_repayable,
            installment_count=result.installment_count,
            installments=_installments_payload(result),
            offer_expiry_date=data.get("offer_expiry_date"),
            customer_terms=data.get("customer_terms", ""),
            internal_notes=data.get("internal_notes", ""),
        )
        return Response(AdminOfferDetailSerializer(offer).data)


class AdminOfferSendView(generics.GenericAPIView):
    """POST /api/v1/admin/offers/{id}/send/ — Stage 7: "Send offer to
    customer through an explicit transition. Supersede previous sent offer
    when a revision is sent." Both effects, plus the LOAN_OFFER_READY SMS
    record, happen atomically inside
    apps/loan_offers/services.py::send_offer()."""

    serializer_class = AdminOfferDetailSerializer
    permission_classes = [permissions.IsAuthenticated, has_any_role(LOAN_OFFICER, SUPER_ADMIN)]
    queryset = LoanOffer.objects.all()

    def post(self, request, pk):
        offer = offer_services.send_offer(self.get_object(), officer=request.user)
        return Response(AdminOfferDetailSerializer(offer).data)


class CustomerOfferDetailView(generics.RetrieveAPIView):
    """GET /api/v1/customer/offers/{id}/ — Stage 7: "Build customer
    offer-review page." Read-only this stage: accept/reject/request-revision
    actions are Stage 8's "Customer Decision, Signature, PDF" work. Ownership
    is enforced by IsOwner via LoanOffer.customer (a property delegating to
    loan_request.customer — see apps/loan_offers/models.py)."""

    serializer_class = CustomerOfferSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    queryset = LoanOffer.objects.select_related(
        "loan_request", "loan_request__customer"
    ).prefetch_related("installments")


class CustomerOfferAcceptView(generics.GenericAPIView):
    """POST /api/v1/customer/offers/{id}/accept/ — Stage 8's "final
    acceptance flow": typed name + checkbox + drawn signature, PDF
    generation, immutable Agreement, and a PENDING_APPROVAL Loan, all
    created atomically by
    apps/agreements/services.py::accept_offer_and_create_agreement(). The
    confirmation email is sent only *after* that transaction commits, so an
    email failure can never undo a valid acceptance (Section 18)."""

    serializer_class = AcceptOfferSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    queryset = LoanOffer.objects.select_related("loan_request", "loan_request__customer")

    def post(self, request, pk):
        offer = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        signature_bytes = agreement_services.validate_signature_image(data["signature_image"])

        agreement, loan = agreement_services.accept_offer_and_create_agreement(
            offer,
            customer=request.user,
            typed_legal_name=data["typed_legal_name"],
            signature_bytes=signature_bytes,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )

        agreement_services.send_agreement_email(agreement)

        return Response(
            AcceptOfferResultSerializer(
                {"agreement": agreement, "loan": loan}, context={"request": request}
            ).data,
            status=status.HTTP_201_CREATED,
        )


class CustomerOfferRejectView(generics.GenericAPIView):
    """POST /api/v1/customer/offers/{id}/reject/ — Stage 8: "Implement
    reject ... actions." Terminal for this offer version; the loan officer
    may still send a new one (docs/STATUS_TRANSITIONS.md Section 2)."""

    serializer_class = RejectOfferSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    queryset = LoanOffer.objects.select_related("loan_request", "loan_request__customer")

    def post(self, request, pk):
        offer = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        offer = offer_services.reject_offer(
            offer, customer=request.user, reason=serializer.validated_data["reason"]
        )
        return Response(CustomerOfferSerializer(offer).data)


class CustomerOfferRequestRevisionView(generics.GenericAPIView):
    """POST /api/v1/customer/offers/{id}/request-revision/ — Stage 8:
    "Implement ... request-revision actions." Modelled as the offer moving
    to REJECTED while the parent LoanRequest moves to REVISION_REQUESTED
    (docs/STATUS_TRANSITIONS.md's Stage 4 design decision)."""

    serializer_class = RequestRevisionSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    queryset = LoanOffer.objects.select_related("loan_request", "loan_request__customer")

    def post(self, request, pk):
        offer = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        offer = offer_services.request_revision(
            offer, customer=request.user, reason=serializer.validated_data["reason"]
        )
        return Response(CustomerOfferSerializer(offer).data)
