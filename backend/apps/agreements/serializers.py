from django.urls import reverse
from rest_framework import serializers

from apps.agreements.models import Agreement


class AgreementSerializer(serializers.ModelSerializer):
    """Never includes the raw storage paths (`signature_image_path`,
    `agreement_pdf_path`) — the PDF is only ever reachable through the
    authorised download endpoint, never a public/guessable path
    (docs/ARCHITECTURE.md Section 11)."""

    offer_id = serializers.UUIDField(source="offer.id", read_only=True)
    request_number = serializers.CharField(
        source="offer.loan_request.request_number", read_only=True
    )
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Agreement
        fields = [
            "id",
            "offer_id",
            "request_number",
            "typed_legal_name",
            "acceptance_text_version",
            "agreement_pdf_sha256",
            "accepted_at",
            "email_delivery_status",
            "download_url",
            "created_at",
        ]
        read_only_fields = fields

    def get_download_url(self, obj: Agreement) -> str:
        path = reverse("agreement-download", kwargs={"pk": obj.pk})
        request = self.context.get("request")
        return request.build_absolute_uri(path) if request else path


class _AcceptedLoanSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    loan_number = serializers.CharField()
    status = serializers.CharField()
    principal = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_repayable = serializers.DecimalField(max_digits=12, decimal_places=2)


class AcceptOfferResultSerializer(serializers.Serializer):
    """Response shape for POST /api/v1/customer/offers/{id}/accept/ —
    everything the frontend's success screen needs (agreement + the new
    loan's identity) without a second round trip."""

    agreement = AgreementSerializer()
    loan = _AcceptedLoanSummarySerializer()
