"""SMS record-writing, template rendering, and dispatch (master prompt
Section 17, Stage 11). Every caller across the codebase that wants to
notify someone by SMS goes through this module rather than writing an
SMSMessage row directly or importing a provider class ("route SMS through
the messaging application service"), so this is the one place that knows
how a PENDING row gets sent and how templates are worded.

Immediate-event messages (offer ready, loan approved, disbursement,
payment, payoff) are created inside the same DB transaction as the
financial/state change they describe, then dispatched via
`transaction.on_commit()` — this satisfies Section 17's "validate and
commit the financial transaction first, attempt Hubtel delivery outside
the critical financial transaction, never roll back a valid disbursement
or repayment because SMS failed" without needing a queue: the send only
ever fires after the row recording it is durably committed, and a send
failure only ever mutates the SMSMessage row itself.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.messaging.models import SMSMessage
from integrations.hubtel import get_sms_provider

logger = logging.getLogger(__name__)

MessageType = SMSMessage.MessageType

# Minutes to wait before each successive retry attempt (index 0 = wait
# before attempt 2, etc.) — a short, deliberately simple fixed backoff
# rather than exponential, since SMS_MAX_ATTEMPTS is small (default 3).
_RETRY_BACKOFF_MINUTES = [5, 30, 120]


def _gHS(amount: Decimal) -> str:
    return f"GHS {amount:,.2f}"


def _first_name(user) -> str:
    return (getattr(user, "first_name", "") or "Customer").strip() or "Customer"


def record_sms(
    *,
    message_type: str,
    recipient_phone_e164: str,
    message_body: str,
    customer=None,
    loan=None,
    installment=None,
    reminder_business_date=None,
    reminder_slot: str = "",
) -> SMSMessage:
    """Writes one PENDING SMSMessage. Nothing is sent here — call
    `dispatch_after_commit()` (immediate events) or let `process_due_sms`
    (scheduled reminders) pick it up."""
    return SMSMessage.objects.create(
        customer=customer,
        loan=loan,
        installment=installment,
        message_type=message_type,
        recipient_phone_e164=recipient_phone_e164,
        message_body=message_body,
        status=SMSMessage.Status.PENDING,
        reminder_business_date=reminder_business_date,
        reminder_slot=reminder_slot,
    )


def dispatch_after_commit(message: SMSMessage) -> None:
    """Registers the real send to happen once the current DB transaction
    commits. If called outside any atomic block, Django runs the callback
    immediately."""
    transaction.on_commit(lambda: dispatch_sms(message.pk))


def dispatch_sms(message_id) -> SMSMessage | None:
    """Sends one eligible (PENDING or retry-eligible FAILED) message
    through the configured provider and updates its status. Never raises —
    provider failures are recorded on the row, never propagated, so a
    caller invoking this from an on_commit hook or the scheduler can't have
    an already-committed financial action affected by an SMS failure."""
    try:
        message = SMSMessage.objects.get(pk=message_id)
    except SMSMessage.DoesNotExist:  # pragma: no cover - defensive
        return None
    if message.status not in {SMSMessage.Status.PENDING, SMSMessage.Status.FAILED}:
        return message

    message.status = SMSMessage.Status.PROCESSING
    message.attempt_count += 1
    message.save(update_fields=["status", "attempt_count", "updated_at"])

    provider = get_sms_provider()
    try:
        result = provider.send(
            recipient_phone_e164=message.recipient_phone_e164, message_body=message.message_body
        )
    except Exception as exc:  # pragma: no cover - defensive, providers shouldn't raise
        logger.exception("sms.dispatch.unexpected_error message_id=%s", message.pk)
        result = None
        error_summary = f"Unexpected error: {exc}"
    else:
        error_summary = result.error_summary

    if result is not None and result.success:
        message.status = SMSMessage.Status.SENT
        message.provider_message_id = result.provider_message_id
        message.provider_response_code = result.response_code
        message.sent_at = timezone.now()
        message.last_error_summary = ""
        message.next_attempt_at = None
        message.save(
            update_fields=[
                "status",
                "provider_message_id",
                "provider_response_code",
                "sent_at",
                "last_error_summary",
                "next_attempt_at",
                "updated_at",
            ]
        )
        return message

    message.status = SMSMessage.Status.FAILED
    message.failed_at = timezone.now()
    message.last_error_summary = (error_summary or "Unknown failure")[:2000]
    if message.attempt_count < settings.SMS_MAX_ATTEMPTS:
        backoff_index = min(message.attempt_count - 1, len(_RETRY_BACKOFF_MINUTES) - 1)
        message.next_attempt_at = timezone.now() + timedelta(
            minutes=_RETRY_BACKOFF_MINUTES[backoff_index]
        )
    else:
        message.next_attempt_at = None
    message.save(
        update_fields=["status", "failed_at", "last_error_summary", "next_attempt_at", "updated_at"]
    )
    return message


# ---------------------------------------------------------------------------
# Immediate-event templates (master prompt Section 27)
# ---------------------------------------------------------------------------


def record_offer_ready_sms(*, offer, customer, profile) -> SMSMessage:
    message = record_sms(
        message_type=MessageType.LOAN_OFFER_READY,
        recipient_phone_e164=profile.phone_number_e164,
        message_body=(
            f"{settings.LENDER_NAME}: Dear {_first_name(customer)}, your loan offer for "
            f"{_gHS(offer.principal)} is ready for review. Sign in to view the terms. "
            f"Ref: {offer.loan_request.request_number}."
        ),
        customer=customer,
    )
    dispatch_after_commit(message)
    return message


def record_offer_accepted_sms(*, offer, customer, profile) -> list[SMSMessage]:
    messages = [
        record_sms(
            message_type=MessageType.OFFER_ACCEPTED_CUSTOMER,
            recipient_phone_e164=profile.phone_number_e164,
            message_body=(
                f"{settings.LENDER_NAME}: Thank you {_first_name(customer)}, we received your "
                f"acceptance for request {offer.loan_request.request_number}. Your loan is now "
                f"pending approval."
            ),
            customer=customer,
        )
    ]
    if settings.HUBTEL_ADMIN_PHONE_E164:
        messages.append(
            record_sms(
                message_type=MessageType.OFFER_ACCEPTED_ADMIN,
                recipient_phone_e164=settings.HUBTEL_ADMIN_PHONE_E164,
                message_body=(
                    f"{settings.LENDER_NAME}: {customer.get_full_name() or customer.email} "
                    f"accepted the offer for request {offer.loan_request.request_number}. "
                    "Pending approval."
                ),
            )
        )
    for message in messages:
        dispatch_after_commit(message)
    return messages


def record_loan_approved_sms(*, loan) -> SMSMessage:
    profile = getattr(loan.customer, "customer_profile", None)
    phone = profile.phone_number_e164 if profile else ""
    message = record_sms(
        message_type=MessageType.LOAN_APPROVED,
        recipient_phone_e164=phone,
        message_body=(
            f"{settings.LENDER_NAME}: Dear {_first_name(loan.customer)}, your loan "
            f"{loan.loan_number} for {_gHS(loan.principal)} has been approved. Disbursement is "
            f"next."
        ),
        customer=loan.customer,
        loan=loan,
    )
    dispatch_after_commit(message)
    return message


def _next_installment_text(loan) -> str:
    next_installment = (
        loan.installments.exclude(status="PAID")
        .exclude(status="WAIVED")
        .order_by("sequence_number")
        .first()
    )
    if next_installment is None:
        return "No further payments are due."
    return (
        f"{_gHS(next_installment.outstanding_amount)} due {next_installment.due_date.isoformat()}"
    )


def record_disbursement_sms(*, loan, disbursement) -> list[SMSMessage]:
    profile = getattr(loan.customer, "customer_profile", None)
    next_due = _next_installment_text(loan)
    messages = []
    if profile is not None:
        messages.append(
            record_sms(
                message_type=MessageType.LOAN_DISBURSED_CUSTOMER,
                recipient_phone_e164=profile.phone_number_e164,
                message_body=(
                    f"{settings.LENDER_NAME}: {_gHS(disbursement.amount)} has been recorded as "
                    f"disbursed for loan {loan.loan_number}. First repayment: {next_due}."
                ),
                customer=loan.customer,
                loan=loan,
            )
        )
    if settings.HUBTEL_ADMIN_PHONE_E164:
        messages.append(
            record_sms(
                message_type=MessageType.LOAN_DISBURSED_ADMIN,
                recipient_phone_e164=settings.HUBTEL_ADMIN_PHONE_E164,
                message_body=(
                    f"{settings.LENDER_NAME}: Disbursement recorded for "
                    f"{loan.customer.get_full_name() or loan.customer.email}, loan "
                    f"{loan.loan_number}, amount {_gHS(disbursement.amount)}. Next due: {next_due}."
                ),
                loan=loan,
            )
        )
    for message in messages:
        dispatch_after_commit(message)
    return messages


def record_payment_sms(*, loan, payment) -> list[SMSMessage]:
    profile = getattr(loan.customer, "customer_profile", None)
    is_paid_off = loan.status == "PAID_OFF"
    messages = []
    if profile is not None:
        if is_paid_off:
            customer_body = (
                f"{settings.LENDER_NAME}: We received {_gHS(payment.amount)}. Loan "
                f"{loan.loan_number} is now fully repaid. Thank you."
            )
        else:
            next_due = _next_installment_text(loan)
            customer_body = (
                f"{settings.LENDER_NAME}: We received {_gHS(payment.amount)} for loan "
                f"{loan.loan_number}. Balance: {_gHS(loan.outstanding_balance)}. Next payment: "
                f"{next_due}."
            )
        messages.append(
            record_sms(
                message_type=(
                    MessageType.LOAN_PAID_OFF_CUSTOMER
                    if is_paid_off
                    else MessageType.PAYMENT_RECEIVED_CUSTOMER
                ),
                recipient_phone_e164=profile.phone_number_e164,
                message_body=customer_body,
                customer=loan.customer,
                loan=loan,
            )
        )
    if settings.HUBTEL_ADMIN_PHONE_E164:
        customer_label = loan.customer.get_full_name() or loan.customer.email
        if is_paid_off:
            admin_body = (
                f"{settings.LENDER_NAME}: Loan {loan.loan_number} ({customer_label}) is now "
                f"fully repaid. Final payment: {_gHS(payment.amount)}."
            )
            admin_type = MessageType.LOAN_PAID_OFF_ADMIN
        else:
            admin_body = (
                f"{settings.LENDER_NAME}: Payment received from {customer_label}, loan "
                f"{loan.loan_number}, amount {_gHS(payment.amount)}. Balance: "
                f"{_gHS(loan.outstanding_balance)}."
            )
            admin_type = MessageType.PAYMENT_RECEIVED_ADMIN
        messages.append(
            record_sms(
                message_type=admin_type,
                recipient_phone_e164=settings.HUBTEL_ADMIN_PHONE_E164,
                message_body=admin_body,
                loan=loan,
            )
        )
    for message in messages:
        dispatch_after_commit(message)
    return messages


# ---------------------------------------------------------------------------
# Scheduled reminder templates (Stage 11 / process_due_sms)
# ---------------------------------------------------------------------------

_REMINDER_LABELS = {
    MessageType.REPAYMENT_DUE_5_DAYS: "in 5 days",
    MessageType.REPAYMENT_DUE_3_DAYS: "in 3 days",
    MessageType.REPAYMENT_DUE_2_DAYS: "in 2 days",
    MessageType.REPAYMENT_DUE_1_DAY: "in 1 day",
    MessageType.REPAYMENT_DUE_TODAY_MORNING: "today",
    MessageType.REPAYMENT_DUE_TODAY_AFTERNOON: "today",
    MessageType.REPAYMENT_OVERDUE: "overdue",
}


def render_reminder_message(*, message_type: str, installment) -> str:
    customer = installment.loan.customer
    first_name = _first_name(customer)
    outstanding = _gHS(installment.outstanding_amount)
    loan_number = installment.loan.loan_number
    if message_type == MessageType.REPAYMENT_OVERDUE:
        return (
            f"{settings.LENDER_NAME}: Dear {first_name}, {outstanding} remains overdue on loan "
            f"{loan_number}. Due date was {installment.due_date.isoformat()}. Please pay using "
            f"the agreed channel."
        )
    if installment.amount_paid and installment.amount_paid > 0:
        return (
            f"{settings.LENDER_NAME}: Dear {first_name}, {outstanding} remains due on loan "
            f"{loan_number}. Due date: {installment.due_date.isoformat()}."
        )
    return (
        f"{settings.LENDER_NAME}: Dear {first_name}, {outstanding} is due on "
        f"{installment.due_date.isoformat()} for loan {loan_number}. Please pay using the agreed "
        f"channel."
    )


def record_manual_reminder_sms(*, installment, actor, reason: str = "") -> SMSMessage:
    """A manual reminder is exempt from the scheduled-reminder uniqueness
    constraint (no reminder_business_date is set) and may be sent more than
    once — but it must record the admin actor, done by the caller via
    apps.audit.services.record_event alongside this call."""
    profile = getattr(installment.loan.customer, "customer_profile", None)
    phone = profile.phone_number_e164 if profile else ""
    message = record_sms(
        message_type=MessageType.MANUAL_REMINDER,
        recipient_phone_e164=phone,
        message_body=render_reminder_message(
            message_type=MessageType.REPAYMENT_OVERDUE
            if installment.status == "OVERDUE"
            else MessageType.REPAYMENT_DUE_1_DAY,
            installment=installment,
        ),
        customer=installment.loan.customer,
        loan=installment.loan,
        installment=installment,
    )
    dispatch_after_commit(message)
    return message
