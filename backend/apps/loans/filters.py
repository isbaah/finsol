import django_filters

from apps.loans.models import Loan


class LoanFilter(django_filters.FilterSet):
    status = django_filters.MultipleChoiceFilter(choices=Loan.Status.choices)

    class Meta:
        model = Loan
        fields = ["status"]
