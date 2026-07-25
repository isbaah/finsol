"""Storage abstraction for agreement PDFs, signature images, and (Stage
9/10) payment/disbursement evidence uploads (docs/ARCHITECTURE.md Section
11 / master prompt Section 18): local filesystem in development, an
S3-compatible backend in production. Callers never touch
`django.core.files.storage` directly, so switching `STORAGE_BACKEND` later
is a one-file change, not a call-site rewrite.

Every saved file gets a randomised name — caller-supplied names are only
ever used to recover an extension, never placed in the storage path
(docs/SECURITY.md Section 4: "user input never becomes part of a storage
path").
"""

from __future__ import annotations

import uuid
from pathlib import PurePosixPath

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import storages


def _random_name(subdir: str, original_name: str) -> str:
    suffix = PurePosixPath(original_name).suffix.lower()
    return f"{subdir}/{uuid.uuid4().hex}{suffix}"


class Storage:
    """Thin wrapper around Django's configured "default" file storage
    backend. Only `STORAGE_BACKEND=local` (Django's own `FileSystemStorage`,
    rooted at `MEDIA_ROOT`) is implemented today — an S3-compatible backend
    is a production-launch task, added when it's actually needed rather
    than built speculatively now.
    """

    def __init__(self):
        if settings.STORAGE_BACKEND != "local":
            raise NotImplementedError(
                f"STORAGE_BACKEND={settings.STORAGE_BACKEND!r} is not implemented; "
                "only 'local' is supported in this build."
            )
        self._backend = storages["default"]

    def save(self, content: bytes, *, subdir: str, original_name: str) -> str:
        return self._backend.save(_random_name(subdir, original_name), ContentFile(content))

    def read(self, path: str) -> bytes:
        with self._backend.open(path, "rb") as fh:
            return fh.read()

    def exists(self, path: str) -> bool:
        return self._backend.exists(path)


def get_storage() -> Storage:
    return Storage()
