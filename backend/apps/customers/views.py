from django.core.exceptions import ObjectDoesNotExist
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.customers.models import CustomerProfile
from apps.customers.serializers import CustomerProfileSerializer, MaskedCustomerProfileSerializer
from common.permissions import STAFF_ROLES, IsOwner, has_any_role


class MyProfileView(APIView):
    """GET/PUT /api/v1/profile/ — the caller's own CustomerProfile.

    No `pk` in the URL: the only object reachable through this endpoint is
    always request.user's own profile, which is the ownership-isolation
    guarantee itself. IsOwner is still applied as defense-in-depth per
    Section 10 ("Critical actions must be checked in both the API
    permission layer and the domain service layer").

    PUT both creates (first-time onboarding) and replaces (later edits) —
    there is no partial-update endpoint; the onboarding form always submits
    the complete profile.
    """

    permission_classes = [permissions.IsAuthenticated]

    def _get_profile(self, request) -> CustomerProfile | None:
        try:
            profile = request.user.customer_profile
        except ObjectDoesNotExist:
            return None
        if not IsOwner().has_object_permission(request, self, profile):
            raise PermissionDenied()
        return profile

    def get(self, request):
        profile = self._get_profile(request)
        if profile is None:
            return Response(
                {"detail": "Profile not yet completed.", "code": "profile_not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(CustomerProfileSerializer(profile, context={"request": request}).data)

    def put(self, request):
        profile = self._get_profile(request)
        serializer = CustomerProfileSerializer(
            instance=profile, data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            serializer.data,
            status=status.HTTP_200_OK if profile else status.HTTP_201_CREATED,
        )


class CustomerListView(generics.ListAPIView):
    """Staff-only masked customer directory. Every internal role (Section
    10) needs at least read access somewhere in its workflow — loan
    officers review, approvers approve, finance officers disburse, auditors
    read, super admins manage — so any of the five staff Groups is
    sufficient here; finer per-role restriction arrives with the domain
    models that actually differentiate their access in Stage 4+.
    """

    serializer_class = MaskedCustomerProfileSerializer
    permission_classes = [permissions.IsAuthenticated, has_any_role(*STAFF_ROLES)]
    queryset = CustomerProfile.objects.select_related("user").order_by("-created_at")


class CustomerDetailView(generics.RetrieveAPIView):
    serializer_class = MaskedCustomerProfileSerializer
    permission_classes = [permissions.IsAuthenticated, has_any_role(*STAFF_ROLES)]
    queryset = CustomerProfile.objects.select_related("user")
