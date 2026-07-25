from allauth.account.models import EmailAddress
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F
from django.db.models.functions import Collate
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from apps.loan_requests import services
from apps.loan_requests.filters import LoanRequestFilter
from apps.loan_requests.models import LoanRequest
from apps.loan_requests.serializers import (
    AdminLoanRequestDetailSerializer,
    AdminLoanRequestListSerializer,
    DeclineLoanRequestSerializer,
    LoanRequestCreateSerializer,
    LoanRequestSerializer,
    build_payout_snapshot,
)
from common.permissions import LOAN_OFFICER, SUPER_ADMIN, IsOwner, has_any_role


def _check_customer_eligible(user) -> None:
    """Stage 6: "Require verified email and completed profile." A verified
    session is already a structural precondition of reaching any
    IsAuthenticated view at all (ACCOUNT_EMAIL_VERIFICATION="mandatory",
    Stage 2) — this check is defense-in-depth for that (Section 10), and
    the one that actually matters here is the profile-completion gate,
    since a customer can be fully authenticated with no profile at all
    (that's exactly what CustomerAreaGuard/onboarding exists for on the
    frontend).
    """
    if not EmailAddress.objects.filter(user=user, verified=True).exists():
        raise PermissionDenied("Verify your email before requesting a loan.")
    try:
        profile = user.customer_profile
    except ObjectDoesNotExist:
        profile = None
    if profile is None or profile.profile_completed_at is None:
        raise PermissionDenied("Complete your profile before requesting a loan.")


class LoanRequestListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/v1/customer/loan-requests/ — the caller's own requests
    only (Stage 6 acceptance: "Customer sees only their requests"). Read
    and write use different serializers (Section 14), so `create()` is
    overridden outright rather than forced through the single-serializer
    generic flow.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LoanRequestSerializer

    def get_queryset(self):
        return (
            LoanRequest.objects.filter(customer=self.request.user)
            .select_related("customer", "loan")
            .prefetch_related("offers")
        )

    def create(self, request, *args, **kwargs):
        _check_customer_eligible(request.user)
        serializer = LoanRequestCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        profile = request.user.customer_profile
        loan_request = services.create_loan_request(
            customer=request.user,
            requested_amount=data["requested_amount"],
            purpose=data["purpose"],
            requested_term_count=data.get("requested_term_count"),
            requested_term_unit=data.get("requested_term_unit", ""),
            payout_snapshot=build_payout_snapshot(profile),
            customer_notes=data.get("customer_notes", ""),
        )
        output = LoanRequestSerializer(loan_request).data
        return Response(output, status=status.HTTP_201_CREATED)


class LoanRequestDetailView(generics.RetrieveAPIView):
    """GET /api/v1/customer/loan-requests/{id}/ — unscoped queryset + IsOwner
    so ownership is enforced at the object-permission layer, not merely by
    queryset scoping (Section 10 defense-in-depth; see common/permissions/
    roles.py's IsOwner)."""

    serializer_class = LoanRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    queryset = LoanRequest.objects.select_related("customer", "loan").prefetch_related("offers")


class LoanRequestCancelView(generics.GenericAPIView):
    """POST /api/v1/customer/loan-requests/{id}/cancel/ — Stage 6: "Prevent
    editing after submission except through an explicit cancellation." The
    domain guard (which source statuses may cancel) lives in
    apps/loan_requests/services.py::cancel(), not here.
    """

    serializer_class = LoanRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    queryset = LoanRequest.objects.all()

    def post(self, request, *args, **kwargs):
        loan_request = self.get_object()
        loan_request = services.cancel(loan_request, actor=request.user)
        return Response(LoanRequestSerializer(loan_request).data)


class AdminLoanRequestListView(generics.ListAPIView):
    """GET /api/v1/admin/loan-requests/ — the request queue (Stage 7:
    "Build admin request queue, filters, search")."""

    serializer_class = AdminLoanRequestListSerializer
    permission_classes = [permissions.IsAuthenticated, has_any_role(LOAN_OFFICER, SUPER_ADMIN)]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = LoanRequestFilter
    # `customer__email` can't be searched directly: User.email uses a
    # nondeterministic ICU collation for case-insensitive uniqueness
    # (apps/accounts/models.py), and Postgres refuses LIKE against that
    # collation outright (docs/BUILD_PROGRESS.md's Stage 4 "incidental
    # finding"). Re-collating it deterministically for this query only is
    # the documented fix, not a schema change.
    search_fields = [
        "request_number",
        "customer_email_ci",
        "customer__first_name",
        "customer__last_name",
    ]
    ordering_fields = ["submitted_at", "created_at", "requested_amount"]
    ordering = ["-submitted_at"]

    def get_queryset(self):
        return LoanRequest.objects.select_related("customer", "assigned_to").annotate(
            customer_email_ci=Collate(F("customer__email"), "C")
        )


class AdminLoanRequestDetailView(generics.RetrieveAPIView):
    """GET /api/v1/admin/loan-requests/{id}/ — full detail including the
    complete offer version history (Stage 7 acceptance: "Previous versions
    are retained for audit")."""

    serializer_class = AdminLoanRequestDetailSerializer
    permission_classes = [permissions.IsAuthenticated, has_any_role(LOAN_OFFICER, SUPER_ADMIN)]
    queryset = LoanRequest.objects.select_related("customer", "assigned_to").prefetch_related(
        "offers"
    )


class AdminLoanRequestStartReviewView(generics.GenericAPIView):
    """POST /api/v1/admin/loan-requests/{id}/start-review/ — Stage 7:
    "Implement assignment and under-review transition." The calling officer
    is assigned to the request and it moves to UNDER_REVIEW in one atomic
    step (apps/loan_requests/services.py::start_review()) — there's no
    separate "assign to someone else" action in the MVP; the officer who
    picks up a request from the queue is its assignee.
    """

    serializer_class = AdminLoanRequestDetailSerializer
    permission_classes = [permissions.IsAuthenticated, has_any_role(LOAN_OFFICER, SUPER_ADMIN)]
    queryset = LoanRequest.objects.all()

    def post(self, request, *args, **kwargs):
        loan_request = self.get_object()
        loan_request = services.start_review(loan_request, officer=request.user)
        return Response(AdminLoanRequestDetailSerializer(loan_request).data)


class AdminLoanRequestDeclineView(generics.GenericAPIView):
    """POST /api/v1/admin/loan-requests/{id}/decline/ — a reason is
    required (apps/loan_requests/services.py::decline())."""

    serializer_class = DeclineLoanRequestSerializer
    permission_classes = [permissions.IsAuthenticated, has_any_role(LOAN_OFFICER, SUPER_ADMIN)]
    queryset = LoanRequest.objects.all()

    def post(self, request, *args, **kwargs):
        loan_request = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        loan_request = services.decline(
            loan_request, actor=request.user, reason=serializer.validated_data["reason"]
        )
        return Response(AdminLoanRequestDetailSerializer(loan_request).data)
