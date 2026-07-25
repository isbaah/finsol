"""Signature validation, PDF generation/hashing, and the acceptance
orchestration for Stage 8 (master prompt Section 18 / Section 24 Stage 8).

`accept_offer_and_create_agreement()` is the one place that turns a
customer's signature into: an ACCEPTED LoanOffer, an immutable Agreement,
and a PENDING_APPROVAL Loan — all inside one transaction, so a failure at
any point (invalid signature, PDF generation error) leaves nothing
half-created. Emailing the generated PDF happens *outside* that
transaction (in the view, after it commits) — Section 18: "If email fails,
do not undo the customer's valid acceptance."
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import io

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from PIL import Image, UnidentifiedImageError
from weasyprint import HTML

import apps.loan_offers.services as offer_services
import apps.loans.services as loan_services
from apps.agreements.models import Agreement
from apps.loan_offers.models import LoanOffer
from common.domain import DomainError
from integrations.storage.backends import get_storage

ACCEPTANCE_TEXT_VERSION = "v1"


def _acceptance_text() -> str:
    return (
        "I confirm that I have reviewed the full offer summary above, including "
        "the principal, interest, total repayable amount, and repayment "
        "schedule. I agree to repay this loan according to these terms and "
        f"authorise {settings.LENDER_NAME} to proceed."
    )


# Signature images arrive as a data URL (e.g. "data:image/png;base64,...."),
# the shape a browser <canvas>/signature_pad export produces.
_MAX_SIGNATURE_BYTES = 1_000_000  # 1 MB — a drawn signature is small; guards fat-fingered uploads
_ALLOWED_SIGNATURE_FORMATS = {"PNG", "JPEG"}


class InvalidSignatureError(DomainError):
    pass


def validate_signature_image(data_url: str) -> bytes:
    """Decodes and validates a signature image data URL. Raises
    InvalidSignatureError (mapped to 409 by the global DomainError handler)
    for anything malformed, oversized, or not a real image — Stage 8's
    "Invalid signature" test."""
    if not data_url or "," not in data_url:
        raise InvalidSignatureError("Signature image is missing or malformed.")
    header, _, encoded = data_url.partition(",")
    if "base64" not in header:
        raise InvalidSignatureError("Signature image must be base64-encoded.")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise InvalidSignatureError("Signature image could not be decoded.") from exc
    if not raw:
        raise InvalidSignatureError("Signature image is empty.")
    if len(raw) > _MAX_SIGNATURE_BYTES:
        raise InvalidSignatureError("Signature image is too large.")
    try:
        image = Image.open(io.BytesIO(raw))
        image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidSignatureError("Signature image is not a valid image file.") from exc
    if image.format not in _ALLOWED_SIGNATURE_FORMATS:
        raise InvalidSignatureError("Signature image must be PNG or JPEG.")
    return raw


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _build_pdf_context(
    offer: LoanOffer, *, typed_legal_name: str, accepted_at, signature_bytes: bytes
) -> dict:
    loan_request = offer.loan_request
    customer = loan_request.customer
    installments = list(offer.installments.order_by("sequence_number"))
    return {
        "lender_name": settings.LENDER_NAME,
        "signature_base64": base64.b64encode(signature_bytes).decode("ascii"),
        "customer_name": customer.get_full_name(),
        "customer_email": customer.email,
        "request_number": loan_request.request_number,
        "offer_version": offer.version_number,
        "principal": offer.principal,
        "interest_method": offer.get_interest_method_display(),
        "interest_rate_percent": offer.interest_rate_percent,
        "total_interest": offer.total_interest,
        "total_repayable": offer.total_repayable,
        "term_count": offer.term_count,
        "term_unit": offer.get_term_unit_display(),
        "first_due_date": offer.first_due_date,
        "final_due_date": installments[-1].due_date if installments else None,
        "installments": installments,
        "customer_terms": offer.customer_terms,
        "acceptance_text": _acceptance_text(),
        "acceptance_text_version": ACCEPTANCE_TEXT_VERSION,
        "typed_legal_name": typed_legal_name,
        "accepted_at": accepted_at,
        "document_reference": f"{loan_request.request_number}-AGR-v{offer.version_number}",
    }


def render_agreement_pdf(
    offer: LoanOffer, *, typed_legal_name: str, accepted_at, signature_bytes: bytes
) -> bytes:
    context = _build_pdf_context(
        offer,
        typed_legal_name=typed_legal_name,
        accepted_at=accepted_at,
        signature_bytes=signature_bytes,
    )
    html = render_to_string("agreements/agreement_pdf.html", context)
    return HTML(string=html).write_pdf()


def accept_offer_and_create_agreement(
    offer: LoanOffer,
    *,
    customer,
    typed_legal_name: str,
    signature_bytes: bytes,
    ip_address: str | None,
    user_agent: str,
):
    """Returns (Agreement, Loan). Raises whatever accept_offer() raises
    (OfferExpiredError / InvalidTransitionError, both DomainError
    subclasses -> 409) for an offer that isn't currently acceptable —
    covers Stage 8's "non-current offer acceptance" and "double
    acceptance" tests without any extra logic here."""
    from apps.audit.services import record_event

    storage = get_storage()
    with transaction.atomic():
        accepted_offer = offer_services.accept_offer(offer, customer=customer)
        accepted_at = accepted_offer.accepted_at or timezone.now()

        signature_hash = sha256_hex(signature_bytes)
        signature_path = storage.save(
            signature_bytes, subdir="signatures", original_name="signature.png"
        )

        pdf_bytes = render_agreement_pdf(
            accepted_offer,
            typed_legal_name=typed_legal_name,
            accepted_at=accepted_at,
            signature_bytes=signature_bytes,
        )
        pdf_hash = sha256_hex(pdf_bytes)
        pdf_path = storage.save(pdf_bytes, subdir="agreements", original_name="agreement.pdf")

        agreement = Agreement.objects.create(
            offer=accepted_offer,
            customer=customer,
            typed_legal_name=typed_legal_name,
            acceptance_text_version=ACCEPTANCE_TEXT_VERSION,
            acceptance_text_snapshot=_acceptance_text(),
            signature_image_path=signature_path,
            signature_image_sha256=signature_hash,
            agreement_pdf_path=pdf_path,
            agreement_pdf_sha256=pdf_hash,
            accepted_ip_address=ip_address,
            accepted_user_agent=user_agent,
            accepted_at=accepted_at,
            email_delivery_status=Agreement.EmailDeliveryStatus.NOT_SENT,
        )
        record_event(
            actor=customer,
            action="agreement.create",
            entity=agreement,
            after={
                "offer_id": str(accepted_offer.pk),
                "agreement_pdf_sha256": pdf_hash,
                "signature_image_sha256": signature_hash,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )

        loan = loan_services.create_loan(accepted_offer.loan_request, accepted_offer, agreement)

        # Stage 11: OFFER_ACCEPTED_CUSTOMER/ADMIN — recorded in the same
        # transaction as everything else above, dispatched after commit
        # (apps/messaging/services.py::dispatch_after_commit()).
        import apps.messaging.services as messaging_services

        profile = getattr(customer, "customer_profile", None)
        if profile is not None:
            messaging_services.record_offer_accepted_sms(
                offer=accepted_offer, customer=customer, profile=profile
            )

        return agreement, loan


def send_agreement_email(agreement: Agreement) -> str:
    """Emails the generated PDF to AGREEMENT_ACTION_EMAIL and returns the
    resulting `Agreement.EmailDeliveryStatus` value. Never called inside the
    acceptance transaction — a failure here only ever updates the two
    mutable-after-create bookkeeping fields on `agreement`, never rolls
    back the acceptance itself (Section 18)."""
    storage = get_storage()
    recipient = settings.AGREEMENT_ACTION_EMAIL
    try:
        if not recipient:
            raise RuntimeError("AGREEMENT_ACTION_EMAIL is not configured.")
        pdf_bytes = storage.read(agreement.agreement_pdf_path)
        message = EmailMessage(
            subject=f"Signed loan agreement — {agreement.offer.loan_request.request_number}",
            body=(
                f"The attached agreement was signed by {agreement.typed_legal_name} "
                f"({agreement.customer.email}) at {agreement.accepted_at.isoformat()}.\n\n"
                f"Document reference: {agreement.offer.loan_request.request_number}-AGR-v"
                f"{agreement.offer.version_number}\n"
                f"PDF SHA-256: {agreement.agreement_pdf_sha256}"
            ),
            to=[recipient],
        )
        message.attach(
            f"{agreement.offer.loan_request.request_number}-agreement.pdf",
            pdf_bytes,
            "application/pdf",
        )
        sent_count = message.send(fail_silently=False)
        if not sent_count:
            raise RuntimeError("Email backend reported zero messages sent.")
    except Exception:  # noqa: BLE001 — any failure here must never propagate
        status = Agreement.EmailDeliveryStatus.FAILED
    else:
        status = Agreement.EmailDeliveryStatus.SENT

    Agreement.objects.filter(pk=agreement.pk).update(email_delivery_status=status)
    agreement.email_delivery_status = status
    return status


def retry_agreement_email(agreement: Agreement, *, actor) -> Agreement:
    """Admin retry action (Stage 8: "Add admin retry for failed agreement
    email"). Reuses the already-generated PDF — never regenerates it, since
    the agreement itself is immutable once created."""
    from apps.audit.services import record_event

    before_status = agreement.email_delivery_status
    status = send_agreement_email(agreement)
    record_event(
        actor=actor,
        action="agreement.email_retry",
        entity=agreement,
        before={"email_delivery_status": before_status},
        after={"email_delivery_status": status},
    )
    return agreement
