from django.contrib import admin

from apps.audit.models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    """Read-only technical-support view — the model itself refuses updates
    and deletes (see models.py), and this admin doesn't offer them either.
    """

    list_display = ["created_at", "action", "entity_type", "entity_id", "actor"]
    list_filter = ["action", "entity_type"]
    search_fields = ["entity_id", "action", "actor__email"]
    readonly_fields = [f.name for f in AuditEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
