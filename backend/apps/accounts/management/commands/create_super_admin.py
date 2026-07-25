import os

from allauth.account.models import EmailAddress
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User
from common.permissions import SUPER_ADMIN


class Command(BaseCommand):
    """Creates a Django technical superuser and adds them to the SUPER_ADMIN
    business-role Group in one step.

    Section 10 deliberately keeps Django's `is_superuser` (technical admin
    site access) and the business `SUPER_ADMIN` role (full access to staff
    business endpoints) independent — see common/permissions/roles.py — so
    plain `createsuperuser` alone does not grant access to
    has_any_role(*STAFF_ROLES)-gated endpoints. This command does both,
    since in practice the first technical superuser almost always needs
    both.

    It also marks the account's allauth EmailAddress as verified/primary.
    ACCOUNT_EMAIL_VERIFICATION is "mandatory" (Stage 2), so a raw
    `createsuperuser` — which creates the User via the ORM, not allauth's
    signup flow — is left with an unverified EmailAddress and can never
    fully authenticate through /auth/login, even with is_superuser=True.
    This command exists specifically to hand back an account usable end to
    end, not just in Django admin.

    Supports the same non-interactive convention as Django's own
    `createsuperuser`: pass `--noinput` and set `DJANGO_SUPERUSER_EMAIL` /
    `DJANGO_SUPERUSER_PASSWORD` in the environment (our custom User model's
    USERNAME_FIELD is "email" with no REQUIRED_FIELDS, so nothing else is
    needed — see apps/accounts/models.py).
    """

    help = "Create a superuser and add them to the SUPER_ADMIN business role group."

    def add_arguments(self, parser):
        parser.add_argument("--email", help="Email address for the new superuser.")
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Non-interactive: reads DJANGO_SUPERUSER_EMAIL/DJANGO_SUPERUSER_PASSWORD.",
        )

    def handle(self, *args, **options):
        interactive = options["interactive"]
        email = options.get("email") or os.environ.get("DJANGO_SUPERUSER_EMAIL")

        if interactive and not email:
            email = input("Email address: ").strip()
        if not email:
            raise CommandError("An email is required — pass --email or set DJANGO_SUPERUSER_EMAIL.")

        call_command("createsuperuser", email=email, interactive=interactive)

        user = User.objects.get(email__iexact=email)
        group, _ = Group.objects.get_or_create(name=SUPER_ADMIN)
        user.groups.add(group)

        EmailAddress.objects.update_or_create(
            user=user, email=user.email, defaults={"verified": True, "primary": True}
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"{user.email} is now a Django superuser, in the SUPER_ADMIN group, "
                "and has a verified email — able to log in via /auth/login."
            )
        )
