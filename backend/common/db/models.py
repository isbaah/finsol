"""Shared abstract base for domain models.

Every externally-referenced entity gets a UUID primary key plus
created_at/updated_at timestamps (master prompt Section 12) — defined once
here rather than repeated on each model as they arrive from Stage 3 onward.
"""

import uuid

from django.db import models


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
