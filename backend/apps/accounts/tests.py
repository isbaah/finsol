import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.db import IntegrityError

from apps.accounts.models import User
from common.permissions import STAFF_ROLES


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


@pytest.mark.django_db
def test_seed_roles_creates_all_staff_role_groups():
    call_command("seed_roles")

    assert set(Group.objects.filter(name__in=STAFF_ROLES).values_list("name", flat=True)) == set(
        STAFF_ROLES
    )


@pytest.mark.django_db
def test_seed_roles_is_idempotent():
    call_command("seed_roles")
    call_command("seed_roles")

    assert Group.objects.filter(name__in=STAFF_ROLES).count() == len(STAFF_ROLES)


@pytest.mark.django_db
def test_me_serializer_reports_roles_and_customer_status(client):
    user = User.objects.create_user(email="officer@example.com", password="s3cret-pass")  # nosec
    group, _ = Group.objects.get_or_create(name="LOAN_OFFICER")
    user.groups.add(group)
    client.force_login(user)

    response = client.get("/api/v1/me/")

    body = response.json()
    assert body["roles"] == ["LOAN_OFFICER"]
    assert body["is_customer"] is False
    assert body["profile_completed"] is False


@pytest.mark.django_db
def test_me_serializer_reports_plain_user_as_customer_with_no_roles(client):
    user = User.objects.create_user(email="plain@example.com", password="s3cret-pass")  # nosec
    client.force_login(user)

    response = client.get("/api/v1/me/")

    body = response.json()
    assert body["roles"] == []
    assert body["is_customer"] is True
    assert body["profile_completed"] is False
