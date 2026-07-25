import pytest
from django.db import IntegrityError, transaction

from apps.agreements.models import Agreement
from tests.factories import make_agreement, make_offer


@pytest.mark.django_db
class TestAgreementImmutability:
    def test_typed_legal_name_cannot_be_changed_after_creation(self):
        agreement = make_agreement(make_offer())

        agreement.typed_legal_name = "Someone Else"
        with pytest.raises(ValueError):
            agreement.save()

    def test_email_delivery_status_remains_editable_after_creation(self):
        agreement = make_agreement(make_offer())

        agreement.email_delivery_status = Agreement.EmailDeliveryStatus.FAILED
        agreement.save()  # must not raise

        agreement.refresh_from_db()
        assert agreement.email_delivery_status == Agreement.EmailDeliveryStatus.FAILED

    def test_email_provider_reference_remains_editable_after_creation(self):
        agreement = make_agreement(make_offer())

        agreement.email_provider_reference = "provider-ref-123"
        agreement.save()

        agreement.refresh_from_db()
        assert agreement.email_provider_reference == "provider-ref-123"

    def test_one_agreement_per_offer(self):
        offer = make_offer()
        make_agreement(offer)

        with transaction.atomic(), pytest.raises(IntegrityError):
            make_agreement(offer)
