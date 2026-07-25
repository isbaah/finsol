from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from apps.accounts.models import User
from common.permissions import STAFF_ROLES


class UserSerializer(serializers.ModelSerializer):
    """Self-profile serializer for GET /api/v1/me/.

    `roles`, `is_customer`, and `profile_completed` let the frontend decide,
    immediately after login, whether to route a customer through
    /onboarding/profile — see docs/BUILD_PROGRESS.md's Stage 3 notes.
    """

    roles = serializers.SerializerMethodField()
    is_customer = serializers.SerializerMethodField()
    profile_completed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "date_joined",
            "roles",
            "is_customer",
            "profile_completed",
        ]
        read_only_fields = fields

    def get_roles(self, obj: User) -> list[str]:
        return list(obj.groups.values_list("name", flat=True))

    def get_is_customer(self, obj: User) -> bool:
        # The CUSTOMER logical role (Section 10) is deliberately not a
        # Django Group: it's just the absence of every internal staff role.
        return not obj.is_staff and not obj.groups.filter(name__in=STAFF_ROLES).exists()

    def get_profile_completed(self, obj: User) -> bool:
        try:
            profile = obj.customer_profile
        except ObjectDoesNotExist:
            return False
        return profile.profile_completed_at is not None
