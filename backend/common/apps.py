from django.apps import AppConfig


class CommonConfig(AppConfig):
    """Registered so common/db/sequences.py's NumberSequence table can be
    migrated — everything else in common/ stays plain Python (no models),
    per docs/ARCHITECTURE.md's "infrastructure, not business rules" framing.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "common"
