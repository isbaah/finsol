from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

import apps.agreements.services as agreement_services
from apps.agreements.models import Agreement
from apps.agreements.serializers import AgreementSerializer
from common.permissions import LOAN_OFFICER, STAFF_ROLES, SUPER_ADMIN, IsOwner, has_any_role
from integrations.storage.backends import get_storage


class AgreementDetailView(generics.RetrieveAPIView):
    """GET /api/v1/agreements/{id}/ — lets the frontend re-fetch an
    agreement's metadata (status, download link) after navigating away from
    the one-time acceptance response. Owner or any staff role (Section 10:
    auditors have read-only access to operational/audit records, which
    includes agreements)."""

    serializer_class = AgreementSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner | has_any_role(*STAFF_ROLES)]
    queryset = Agreement.objects.select_related("offer", "offer__loan_request")


class AgreementDownloadView(APIView):
    """GET /api/v1/agreements/{id}/download/ — Stage 8: "Add customer
    agreement download with permission checks." Streams the already-
    generated PDF from storage; never a public/guessable path
    (docs/ARCHITECTURE.md Section 11). Owner or any staff role."""

    permission_classes = [permissions.IsAuthenticated, IsOwner | has_any_role(*STAFF_ROLES)]

    def get(self, request, pk):
        agreement = get_object_or_404(
            Agreement.objects.select_related("offer", "offer__loan_request"), pk=pk
        )
        self.check_object_permissions(request, agreement)
        pdf_bytes = get_storage().read(agreement.agreement_pdf_path)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        filename = f"{agreement.offer.loan_request.request_number}-agreement.pdf"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class AdminAgreementRetryEmailView(APIView):
    """POST /api/v1/admin/agreements/{id}/retry-email/ — Stage 8: "Add
    admin retry for failed agreement email." Reuses the already-generated
    PDF; never regenerates the (immutable) agreement."""

    permission_classes = [permissions.IsAuthenticated, has_any_role(LOAN_OFFICER, SUPER_ADMIN)]

    def post(self, request, pk):
        agreement = get_object_or_404(Agreement, pk=pk)
        agreement = agreement_services.retry_agreement_email(agreement, actor=request.user)
        return Response(AgreementSerializer(agreement, context={"request": request}).data)
