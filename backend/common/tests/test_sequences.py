import threading

import pytest
from django.db import connection

from common.db.sequences import next_reference_number
from common.models import NumberSequence


@pytest.mark.django_db
def test_next_reference_number_format_and_increment():
    first = next_reference_number("widget", prefix="WID", period="2026")
    second = next_reference_number("widget", prefix="WID", period="2026")

    assert first == "WID-2026-000001"
    assert second == "WID-2026-000002"


@pytest.mark.django_db
def test_next_reference_number_scopes_are_independent():
    a = next_reference_number("scope_a", prefix="A", period="2026")
    b = next_reference_number("scope_b", prefix="B", period="2026")

    assert a == "A-2026-000001"
    assert b == "B-2026-000001"


@pytest.mark.django_db
def test_next_reference_number_scopes_by_period():
    this_year = next_reference_number("annual", prefix="ANN", period="2026")
    next_year = next_reference_number("annual", prefix="ANN", period="2027")

    assert this_year == "ANN-2026-000001"
    assert next_year == "ANN-2027-000001"


@pytest.mark.django_db(transaction=True)
def test_next_reference_number_is_race_free_under_concurrency():
    """Fires many concurrent callers at the same (scope, period) and proves
    no two get the same number and none are skipped — the concrete
    "reference uniqueness... without race conditions" requirement from
    Section 12."""
    results: list[str] = []
    errors: list[Exception] = []
    lock = threading.Lock()

    def worker():
        try:
            value = next_reference_number("concurrent", prefix="CNC", period="2026")
            connection.close()  # each thread gets its own DB connection
            with lock:
                results.append(value)
        except Exception as exc:  # pragma: no cover - failure path only
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert len(results) == 20
    assert len(set(results)) == 20  # no duplicates
    assert NumberSequence.objects.get(scope="concurrent", period="2026").last_value == 20
