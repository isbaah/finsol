import phonenumbers
from django.utils import timezone
from rest_framework import serializers

from apps.customers.models import CustomerProfile
from common.masking import mask_tail

_PAYOUT_METHOD = CustomerProfile.DisbursementMethod


class CustomerProfileSerializer(serializers.ModelSerializer):
    """Full, unmasked serializer for GET/PUT /api/v1/profile/ — the caller's
    own profile only. Never reused for a staff-facing endpoint; see
    MaskedCustomerProfileSerializer for every other consumer.
    """

    # Stored on the User row (accounts.User already has these columns) but
    # collected here, at onboarding: a customer must give their legal name
    # before they can request a loan, so staff never see a bare email where
    # a name belongs.
    first_name = serializers.CharField(source="user.first_name", max_length=150)
    last_name = serializers.CharField(source="user.last_name", max_length=150)

    class Meta:
        model = CustomerProfile
        fields = [
            "id",
            "first_name",
            "last_name",
            "phone_number_e164",
            "phone_country_code",
            "address_line_1",
            "address_line_2",
            "city",
            "country",
            "preferred_disbursement_method",
            "mobile_money_network",
            "mobile_money_number",
            "bank_name",
            "bank_account_name",
            "bank_account_number",
            "profile_completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "phone_country_code",
            "profile_completed_at",
            "created_at",
            "updated_at",
        ]

    def validate_phone_number_e164(self, value: str) -> str:
        try:
            # Region hint only matters for numbers without a leading "+";
            # GH is a safe default given the single-country MVP scope.
            parsed = phonenumbers.parse(value, "GH")
        except phonenumbers.NumberParseException as exc:
            raise serializers.ValidationError("Enter a valid phone number.") from exc
        if not phonenumbers.is_valid_number(parsed):
            raise serializers.ValidationError("Enter a valid phone number.")
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)

    def validate(self, attrs):
        def field(name):
            return attrs.get(name, getattr(self.instance, name, ""))

        method = field("preferred_disbursement_method")
        if method == _PAYOUT_METHOD.MOBILE_MONEY:
            for name, label in [
                ("mobile_money_network", "Mobile money network"),
                ("mobile_money_number", "Mobile money number"),
            ]:
                if not field(name):
                    message = f"{label} is required for mobile money payouts."
                    raise serializers.ValidationError({name: message})
        elif method == _PAYOUT_METHOD.BANK:
            for name, label in [
                ("bank_name", "Bank name"),
                ("bank_account_name", "Account name"),
                ("bank_account_number", "Account number"),
            ]:
                if not field(name):
                    message = f"{label} is required for bank payouts."
                    raise serializers.ValidationError({name: message})
        return attrs

    def _with_country_code(self, validated_data: dict) -> dict:
        if "phone_number_e164" in validated_data:
            parsed = phonenumbers.parse(validated_data["phone_number_e164"])
            validated_data["phone_country_code"] = str(parsed.country_code)
        return validated_data

    def _apply_user_names(self, user, validated_data: dict) -> dict:
        # source="user.first_name" nests the names under a "user" key —
        # they belong to the User row, not the profile row.
        user_data = validated_data.pop("user", None)
        if user_data:
            user.first_name = user_data.get("first_name", user.first_name)
            user.last_name = user_data.get("last_name", user.last_name)
            user.save(update_fields=["first_name", "last_name"])
        return validated_data

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data = self._apply_user_names(user, validated_data)
        validated_data = self._with_country_code(validated_data)
        validated_data["profile_completed_at"] = timezone.now()
        return CustomerProfile.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        validated_data = self._apply_user_names(instance.user, validated_data)
        validated_data = self._with_country_code(validated_data)
        validated_data["profile_completed_at"] = timezone.now()
        return super().update(instance, validated_data)


class MaskedCustomerProfileSerializer(serializers.ModelSerializer):
    """Staff-facing serializer. Payout account numbers are always masked —
    there is currently no authorised reveal action anywhere in the system
    (that arrives in Stage 9 alongside the disbursement workflow and the
    Stage 4 AuditEvent model it must log to), so full exposure is simply
    impossible today rather than gated behind an incomplete control.
    `phone_number_e164` is left unmasked: it's a contact channel staff
    legitimately need, not a payout account identifier.
    """

    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.SerializerMethodField()
    mobile_money_number = serializers.SerializerMethodField()
    bank_account_number = serializers.SerializerMethodField()

    class Meta:
        model = CustomerProfile
        fields = [
            "id",
            "email",
            "full_name",
            "phone_number_e164",
            "city",
            "country",
            "preferred_disbursement_method",
            "mobile_money_network",
            "mobile_money_number",
            "bank_name",
            "bank_account_name",
            "bank_account_number",
            "profile_completed_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_full_name(self, obj: CustomerProfile) -> str:
        return obj.user.get_full_name()

    def get_mobile_money_number(self, obj: CustomerProfile) -> str:
        return mask_tail(obj.mobile_money_number)

    def get_bank_account_number(self, obj: CustomerProfile) -> str:
        return mask_tail(obj.bank_account_number)
