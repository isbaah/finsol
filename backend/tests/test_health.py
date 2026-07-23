import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_liveness_endpoint_returns_ok(client):
    response = client.get(reverse("health-live"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_readiness_endpoint_confirms_database_connectivity(client):
    response = client.get(reverse("health-ready"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "up"}
