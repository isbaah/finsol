import django_filters

from apps.loan_requests.models import LoanRequest


class LoanRequestFilter(django_filters.FilterSet):
    """Backs the admin queue's filter controls (master prompt Section 14:
    "Support filtering, search, and ordering on admin tables"). `status`
    accepts repeated query params (?status=SUBMITTED&status=UNDER_REVIEW)
    so the queue can show "everything awaiting action" in one call."""

    status = django_filters.MultipleChoiceFilter(choices=LoanRequest.Status.choices)

    class Meta:
        model = LoanRequest
        fields = ["status", "assigned_to"]
