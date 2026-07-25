"""Plain factory functions (not pytest fixtures, not a test module — this
file matches none of pytest's python_files patterns) shared by Stage 4's
app test suites, so each app doesn't hand-roll its own "build a
request -> offer -> agreement -> loan" chain.
"""

from datetime import date, timedelta
from decimal import Decimal

from allauth.account.models import EmailAddress
from django.contrib.auth.models import Group
from django.utils import timezone

from apps.accounts.models import User
from apps.agreements.models import Agreement
from apps.customers.models import CustomerProfile
from apps.loan_offers.models import LoanOffer, OfferInstallment
from apps.loan_requests.models import LoanRequest
from apps.loans.models import Loan

_counter = {"n": 0}


def _unique(prefix: str) -> str:
    _counter["n"] += 1
    return f"{prefix}{_counter['n']}"


def make_user(email: str | None = None) -> User:
    return User.objects.create_user(
        email=email or f"{_unique('user')}@example.com",
        password="s3cret-pass",  # nosec
    )


def make_staff_user(role: str, email: str | None = None) -> User:
    user = make_user(email)
    group, _ = Group.objects.get_or_create(name=role)
    user.groups.add(group)
    return user


def make_verified_email(user: User) -> EmailAddress:
    return EmailAddress.objects.update_or_create(
        user=user, email=user.email, defaults={"verified": True, "primary": True}
    )[0]


def make_customer_profile(
    user: User | None = None, *, completed: bool = True, **overrides
) -> CustomerProfile:
    """A Stage 6+ eligible customer: verified email + completed profile.
    `completed=False` builds a profile deliberately missing
    `profile_completed_at`, for eligibility-gate tests."""
    user = user or make_user()
    make_verified_email(user)
    defaults = {
        "user": user,
        "phone_number_e164": "+233241234567",
        "phone_country_code": "233",
        "preferred_disbursement_method": CustomerProfile.DisbursementMethod.MOBILE_MONEY,
        "mobile_money_network": CustomerProfile.MobileMoneyNetwork.MTN,
        "mobile_money_number": "0241234567",
        "profile_completed_at": timezone.now() if completed else None,
    }
    defaults.update(overrides)
    return CustomerProfile.objects.create(**defaults)


def make_loan_request(customer: User | None = None, **overrides) -> LoanRequest:
    from common.db.sequences import next_reference_number

    customer = customer or make_user()
    defaults = {
        # Same sequence key as apps/loan_requests/services.py::create_loan_request()
        # — Stage 6's API tests mix factory-built and real service-created
        # LoanRequests in the same test, and request_number is globally
        # unique, so a separate counter risks both producing "REQ-2026-000001"
        # independently and colliding.
        "request_number": next_reference_number(
            "loan_request", prefix="REQ", period=str(timezone.now().year)
        ),
        "customer": customer,
        "requested_amount": Decimal("5000.00"),
        "purpose": "Working capital",
        "status": LoanRequest.Status.SUBMITTED,
        "submitted_at": timezone.now(),
    }
    defaults.update(overrides)
    return LoanRequest.objects.create(**defaults)


def make_offer_installments(
    principal: Decimal, total_interest: Decimal, count: int, first_due_date: date
) -> list[dict]:
    """A simple even split — good enough for fixture data; Stage 5's real
    calculator has its own dedicated, exhaustively-tested logic."""
    principal_each = (principal / count).quantize(Decimal("0.01"))
    interest_each = (total_interest / count).quantize(Decimal("0.01"))
    rows = []
    for i in range(1, count + 1):
        rows.append(
            {
                "sequence_number": i,
                "due_date": first_due_date + timedelta(days=30 * (i - 1)),
                "principal_due": principal_each,
                "interest_due": interest_each,
                "total_due": principal_each + interest_each,
            }
        )
    return rows


def make_offer(
    loan_request: LoanRequest | None = None, *, officer: User | None = None, **overrides
) -> LoanOffer:
    loan_request = loan_request or make_loan_request()
    officer = officer or make_staff_user("LOAN_OFFICER")
    principal = overrides.pop("principal", Decimal("5000.00"))
    total_interest = overrides.pop("total_interest", Decimal("600.00"))
    installment_count = overrides.pop("installment_count", 6)
    first_due_date = overrides.pop("first_due_date", date(2026, 9, 1))
    defaults = {
        "loan_request": loan_request,
        "version_number": 1,
        "status": LoanOffer.Status.DRAFT,
        "principal": principal,
        "interest_method": LoanOffer.InterestMethod.FLAT_TOTAL_TERM,
        "interest_rate_percent": Decimal("12.00"),
        "term_count": installment_count,
        "term_unit": LoanOffer.TermUnit.MONTH,
        "first_due_date": first_due_date,
        "total_interest": total_interest,
        "total_repayable": principal + total_interest,
        "installment_count": installment_count,
        "created_by": officer,
    }
    defaults.update(overrides)
    offer = LoanOffer.objects.create(**defaults)
    OfferInstallment.objects.bulk_create(
        [
            OfferInstallment(offer=offer, **row)
            for row in make_offer_installments(
                offer.principal, offer.total_interest, offer.installment_count, offer.first_due_date
            )
        ]
    )

    # Keep the parent LoanRequest's own status consistent with the offer
    # being created, so a test exercising loan_offers.services (which also
    # drives the parent request's transition) starts from a valid state
    # without every test having to manage that plumbing by hand.
    if offer.status == LoanOffer.Status.DRAFT:
        if loan_request.status == LoanRequest.Status.SUBMITTED:
            loan_request.status = LoanRequest.Status.UNDER_REVIEW
            loan_request.save(update_fields=["status"])
    elif offer.status in (
        LoanOffer.Status.SENT,
        LoanOffer.Status.ACCEPTED,
        LoanOffer.Status.REJECTED,
        LoanOffer.Status.SUPERSEDED,
        LoanOffer.Status.EXPIRED,
    ):
        loan_request.status = LoanRequest.Status.OFFER_SENT
        loan_request.save(update_fields=["status"])

    return offer


def make_agreement(offer: LoanOffer, **overrides) -> Agreement:
    defaults = {
        "offer": offer,
        "customer": offer.loan_request.customer,
        "typed_legal_name": "Test Customer",
        "acceptance_text_version": "v1",
        "acceptance_text_snapshot": "I agree to the terms.",
        "accepted_at": timezone.now(),
    }
    defaults.update(overrides)
    return Agreement.objects.create(**defaults)


def make_loan(**overrides) -> Loan:
    """Stage 8/9: an accepted offer + agreement + PENDING_APPROVAL loan, all
    built through the real service functions (apps/loan_offers/services.py::
    accept_offer(), apps/loans/services.py::create_loan()) rather than a
    raw ORM shortcut, so the parent LoanOffer/LoanRequest end up in the
    correct ACCEPTED/CONVERTED_TO_LOAN states a Stage 9 test can rely on.
    The customer always has a completed profile (`make_customer_profile()`)
    — Stage 9's payout-detail reveal needs one to exist."""
    from apps.loan_offers import services as offer_services
    from apps.loans import services as loan_services

    loan_request = overrides.pop("loan_request", None) or make_loan_request(
        make_customer_profile().user
    )
    offer_kwargs = {
        key: overrides.pop(key)
        for key in ("principal", "total_interest", "installment_count", "first_due_date")
        if key in overrides
    }
    offer = make_offer(loan_request, status=LoanOffer.Status.SENT, **offer_kwargs)
    offer = offer_services.accept_offer(offer, customer=offer.loan_request.customer)
    agreement = make_agreement(offer)
    loan = loan_services.create_loan(offer.loan_request, offer, agreement)
    if overrides:
        for field, value in overrides.items():
            setattr(loan, field, value)
        loan.save(update_fields=list(overrides.keys()))
    return loan


def make_active_loan(**overrides) -> Loan:
    """Stage 10: a loan taken all the way through the real
    approve_loan()/record_disbursement() service functions, so it has
    genuine RepaymentInstallment rows (copied from the accepted offer) and
    correct outstanding_balance/amount_repaid — what every repayment-
    allocation test needs to allocate against. `principal`/`total_interest`/
    `installment_count`/`first_due_date` are forwarded to make_offer();
    anything else is applied to the Loan row after disbursement."""
    from apps.loans import services as loan_services

    loan_kwargs = {
        key: overrides.pop(key)
        for key in (
            "loan_request",
            "principal",
            "total_interest",
            "installment_count",
            "first_due_date",
        )
        if key in overrides
    }
    loan = make_loan(**loan_kwargs)
    loan = loan_services.approve_loan(loan, approver=make_staff_user("APPROVER"))
    loan_services.record_disbursement(
        loan,
        recorded_by=make_staff_user("FINANCE_OFFICER"),
        amount=loan.principal,
        method="MOBILE_MONEY",
    )
    loan.refresh_from_db()
    if overrides:
        for field, value in overrides.items():
            setattr(loan, field, value)
        loan.save(update_fields=list(overrides.keys()))
    return loan
