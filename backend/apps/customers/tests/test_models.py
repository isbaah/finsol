import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.customers.models import CustomerProfile


def make_user(email="customer@example.com") -> User:
    return User.objects.create_user(email=email, password="s3cret-pass")  # nosec


@pytest.mark.django_db
class TestCustomerProfileConstraint:
    def test_incomplete_profile_may_have_blank_payout_fields(self):
        profile = CustomerProfile.objects.create(
            user=make_user(),
            phone_number_e164="+233241234567",
            phone_country_code="233",
            preferred_disbursement_method=CustomerProfile.DisbursementMethod.MOBILE_MONEY,
        )

        assert profile.profile_completed_at is None
        assert profile.mobile_money_number == ""

    def test_completed_mobile_money_profile_requires_network_and_number(self):
        with transaction.atomic(), pytest.raises(IntegrityError):
            CustomerProfile.objects.create(
                user=make_user(),
                phone_number_e164="+233241234567",
                phone_country_code="233",
                preferred_disbursement_method=CustomerProfile.DisbursementMethod.MOBILE_MONEY,
                profile_completed_at=timezone.now(),
            )

    def test_completed_bank_profile_requires_bank_fields(self):
        with transaction.atomic(), pytest.raises(IntegrityError):
            CustomerProfile.objects.create(
                user=make_user(),
                phone_number_e164="+233241234567",
                phone_country_code="233",
                preferred_disbursement_method=CustomerProfile.DisbursementMethod.BANK,
                profile_completed_at=timezone.now(),
            )

    def test_completed_mobile_money_profile_with_all_fields_saves(self):
        profile = CustomerProfile.objects.create(
            user=make_user(),
            phone_number_e164="+233241234567",
            phone_country_code="233",
            preferred_disbursement_method=CustomerProfile.DisbursementMethod.MOBILE_MONEY,
            mobile_money_network=CustomerProfile.MobileMoneyNetwork.MTN,
            mobile_money_number="0241234567",
            profile_completed_at=timezone.now(),
        )

        assert profile.profile_completed_at is not None
