import json

from django.core.management.base import BaseCommand

from apps.repayments.services import reconcile_all_loans


class Command(BaseCommand):
    """Reports Section 19 reconciliation differences without changing any
    records ("Add a management command to report reconciliation
    differences without changing records automatically")."""

    help = "Report loans whose ledger/installment totals don't reconcile. Read-only."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json", action="store_true", help="Emit machine-readable JSON instead of text."
        )

    def handle(self, *args, **options):
        results = reconcile_all_loans()

        if options["json"]:
            self.stdout.write(json.dumps(results, indent=2))
        elif not results:
            self.stdout.write(self.style.SUCCESS("All loans reconcile cleanly."))
        else:
            self.stdout.write(
                self.style.WARNING(f"{len(results)} loan(s) have reconciliation differences:")
            )
            for loan_number, differences in results.items():
                self.stdout.write(f"\n{loan_number}:")
                for difference in differences:
                    self.stdout.write(f"  - {difference}")

        # Non-zero exit only communicates "differences found" to CI/cron
        # callers — this command never mutates data either way.
        if results:
            self.stdout.write("")
            raise SystemExit(1)
