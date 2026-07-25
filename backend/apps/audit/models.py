from django.conf import settings
from django.db import models

from common.db.models import BaseModel


class AuditEvent(BaseModel):
    """Append-only (master prompt Section 12.14). Written only through
    apps/audit/services.py's record_event() — never edited or deleted, and
    the model itself refuses both (see save()/delete() below) as a second,
    code-level guarantee alongside "no update/delete endpoint is ever
    built".
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
        help_text="Null for system-triggered events (e.g. a scheduler).",
    )
    actor_role_snapshot = models.CharField(max_length=255, blank=True)
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=64)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    correlation_id = models.CharField(max_length=64, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    reason = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["action"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} on {self.entity_type}:{self.entity_id}"

    def save(self, *args, **kwargs):
        if self.pk and AuditEvent.objects.filter(pk=self.pk).exists():
            raise ValueError("AuditEvent rows are append-only and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("AuditEvent rows are append-only and cannot be deleted.")
