"""Best-effort delivery-status query for SENT-but-not-yet-final messages
(master prompt Section 17: "a second command or optional mode to query
final Hubtel delivery status for messages that have a provider ID but are
not yet final").

**Known limitation** (see integrations/hubtel/hubtel.py's module docstring
and docs/BUILD_PROGRESS.md's Stage 11 section): Hubtel's public SMS product
has no confirmed pull/status-query REST endpoint, so
`HubtelSMSProvider.get_status()` always returns `UNKNOWN` today. This
command is still built and wired so the moment a real endpoint is
confirmed and `get_status()` is updated, delivery confirmation "just
works" — nothing about this command's shape needs to change.
"""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.messaging.models import SMSMessage
from integrations.hubtel import get_sms_provider


class Command(BaseCommand):
    help = "Query provider delivery status for SENT messages that aren't yet DELIVERED/FAILED."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=200)

    def handle(self, *args, **options):
        provider = get_sms_provider()
        candidates = SMSMessage.objects.filter(
            status=SMSMessage.Status.SENT, provider_message_id__gt=""
        ).order_by("sent_at")[: options["limit"]]

        updated = unknown = 0
        for message in candidates:
            result = provider.get_status(message.provider_message_id)
            if result.status == "DELIVERED":
                message.status = SMSMessage.Status.DELIVERED
                message.delivered_at = timezone.now()
                message.save(update_fields=["status", "delivered_at", "updated_at"])
                updated += 1
            elif result.status == "FAILED":
                message.status = SMSMessage.Status.FAILED
                message.failed_at = timezone.now()
                message.last_error_summary = "Reported failed by delivery-status query."
                message.save(
                    update_fields=["status", "failed_at", "last_error_summary", "updated_at"]
                )
                updated += 1
            else:
                unknown += 1

        self.stdout.write(
            json.dumps({"checked": len(candidates), "updated": updated, "still_unknown": unknown})
        )
