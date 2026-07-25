import pytest

from apps.audit.models import AuditEvent
from apps.audit.services import record_event, redact
from tests.factories import make_loan_request, make_staff_user


def test_redact_masks_sensitive_keys_case_insensitively():
    data = {
        "email": "a@example.com",
        "password": "hunter2",
        "mobile_money_number": "0241234567",
        "bank_account_number": "1234567890",
        "SessionToken": "abc123",
        "nested": {"signature_image": b"...", "note": "fine"},
    }

    result = redact(data)

    assert result["email"] == "a@example.com"
    assert result["password"] == "[REDACTED]"
    assert result["mobile_money_number"] == "[REDACTED]"
    assert result["bank_account_number"] == "[REDACTED]"
    assert result["SessionToken"] == "[REDACTED]"
    assert result["nested"]["signature_image"] == "[REDACTED]"
    assert result["nested"]["note"] == "fine"


def test_redact_passes_through_non_dict_values():
    assert redact("plain string") == "plain string"
    assert redact([{"password": "x"}, {"ok": "y"}]) == [{"password": "[REDACTED]"}, {"ok": "y"}]


@pytest.mark.django_db
class TestRecordEvent:
    def test_record_event_captures_actor_role_snapshot(self):
        officer = make_staff_user("LOAN_OFFICER")
        loan_request = make_loan_request()

        event = record_event(actor=officer, action="loan_request.start_review", entity=loan_request)

        assert event.actor_role_snapshot == "LOAN_OFFICER"
        assert event.entity_type == "LoanRequest"
        assert event.entity_id == str(loan_request.pk)

    def test_record_event_allows_null_actor_for_system_events(self):
        loan_request = make_loan_request()

        event = record_event(actor=None, action="loan_request.offer_sent", entity=loan_request)

        assert event.actor is None
        assert event.actor_role_snapshot == ""

    def test_record_event_redacts_before_and_after(self):
        loan_request = make_loan_request()

        event = record_event(
            actor=None,
            action="test.redaction",
            entity=loan_request,
            before={"mobile_money_number": "0241234567"},
            after={"status": "SUBMITTED"},
        )

        assert event.before["mobile_money_number"] == "[REDACTED]"
        assert event.after["status"] == "SUBMITTED"

    def test_audit_event_cannot_be_updated(self):
        loan_request = make_loan_request()
        event = record_event(actor=None, action="test.immutable", entity=loan_request)

        event.action = "changed"
        with pytest.raises(ValueError):
            event.save()

    def test_audit_event_cannot_be_deleted(self):
        loan_request = make_loan_request()
        event = record_event(actor=None, action="test.immutable-delete", entity=loan_request)

        with pytest.raises(ValueError):
            event.delete()

        assert AuditEvent.objects.filter(pk=event.pk).exists()
