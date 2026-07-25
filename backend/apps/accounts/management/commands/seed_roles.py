from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from common.permissions import STAFF_ROLES


class Command(BaseCommand):
    """Idempotently create the internal business-role Groups (Section 10).

    Model-level Django permissions aren't attached to these groups: role
    enforcement in this codebase is done through explicit DRF permission
    classes and queryset filtering (common/permissions), not Django's
    built-in per-model permission system — see docs/BUILD_PROGRESS.md's
    Stage 3 notes. Group membership itself is what these classes check.
    """

    help = "Create or update the internal business role groups (idempotent)."

    def handle(self, *args, **options):
        for name in STAFF_ROLES:
            _, created = Group.objects.get_or_create(name=name)
            verb = "Created" if created else "Already exists"
            self.stdout.write(f"{verb}: {name}")
