import pytest
from django.db import IntegrityError

from apps.accounts.models import User


@pytest.mark.django_db
def test_create_user_normalizes_email_and_sets_password():
    user = User.objects.create_user(email="Test@Example.com", password="s3cret-pass")

    assert user.email == "Test@example.com"
    assert user.check_password("s3cret-pass")
    assert user.is_staff is False
    assert user.is_superuser is False
    assert user.is_active is True


@pytest.mark.django_db
def test_create_superuser_sets_staff_and_superuser_flags():
    admin = User.objects.create_superuser(email="admin@example.com", password="s3cret-pass")

    assert admin.is_staff is True
    assert admin.is_superuser is True


@pytest.mark.django_db
def test_email_uniqueness_is_case_insensitive_at_database_level():
    User.objects.create_user(email="dup@example.com", password="s3cret-pass")

    with pytest.raises(IntegrityError):
        User.objects.create_user(email="DUP@EXAMPLE.COM", password="another-pass")


@pytest.mark.django_db
def test_user_has_uuid_primary_key():
    import uuid

    user = User.objects.create_user(email="uuid-check@example.com", password="s3cret-pass")

    assert isinstance(user.id, uuid.UUID)
