import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.loan_offers import services as offer_services
from apps.loan_offers.models import LoanOffer
from apps.loans import services as loan_services
from apps.loans.models import RepaymentInstallment
from apps.messaging.models import SMSMessage
from tests.factories import make_agreement, make_offer


def _make_installment() -> RepaymentInstallment:
    offer = make_offer(status=LoanOffer.Status.SENT)
    offer_services.accept_offer(offer, customer=offer.loan_request.customer)
    offer.refresh_from_db()
    agreement = make_agreement(offer)
    loan = loan_services.create_loan(offer.loan_request, offer, agreement)
    loan_services.copy_schedule_from_offer(loan, offer)
    return loan.installments.get(sequence_number=1)


@pytest.mark.django_db
class TestSMSMessageReminderUniqueness:
    def _reminder_kwargs(self, installment, **overrides):
        defaults = {
            "installment": installment,
            "customer": installment.loan.customer,
            "loan": installment.loan,
            "message_type": SMSMessage.MessageType.REPAYMENT_DUE_1_DAY,
            "recipient_phone_e164": "+233241234567",
            "message_body": "Your payment is due soon.",
            "reminder_business_date": timezone.localdate(),
            "reminder_slot": "MORNING",
            "status": SMSMessage.Status.PENDING,
        }
        defaults.update(overrides)
        return defaults

    def test_duplicate_reminder_for_same_slot_is_rejected(self):
        installment = _make_installment()
        SMSMessage.objects.create(**self._reminder_kwargs(installment))

        with transaction.atomic(), pytest.raises(IntegrityError):
            SMSMessage.objects.create(**self._reminder_kwargs(installment))

    def test_different_slot_same_day_is_allowed(self):
        installment = _make_installment()
        SMSMessage.objects.create(**self._reminder_kwargs(installment, reminder_slot="MORNING"))

        # Must not raise — a distinct slot is a distinct reminder.
        SMSMessage.objects.create(**self._reminder_kwargs(installment, reminder_slot="AFTERNOON"))

    def test_manual_messages_are_exempt_and_may_repeat(self):
        installment = _make_installment()
        kwargs = {
            "customer": installment.loan.customer,
            "loan": installment.loan,
            "message_type": SMSMessage.MessageType.MANUAL_REMINDER,
            "recipient_phone_e164": "+233241234567",
            "message_body": "Please call the office.",
            "status": SMSMessage.Status.PENDING,
        }

        SMSMessage.objects.create(**kwargs)
        SMSMessage.objects.create(
            **kwargs
        )  # must not raise — no installment/reminder_business_date

        assert (
            SMSMessage.objects.filter(message_type=SMSMessage.MessageType.MANUAL_REMINDER).count()
            == 2
        )
