import pytest

from apps.messaging import services
from apps.messaging.models import SMSMessage
from tests.factories import make_customer_profile, make_loan_request, make_offer


@pytest.mark.django_db
class TestRecordOfferReadySms:
    def test_writes_a_pending_offer_ready_record(self):
        profile = make_customer_profile()
        loan_request = make_loan_request(profile.user)
        offer = make_offer(loan_request)

        sms = services.record_offer_ready_sms(offer=offer, customer=profile.user, profile=profile)

        assert sms.status == SMSMessage.Status.PENDING
        assert sms.message_type == SMSMessage.MessageType.LOAN_OFFER_READY
        assert sms.recipient_phone_e164 == profile.phone_number_e164
        assert loan_request.request_number in sms.message_body
