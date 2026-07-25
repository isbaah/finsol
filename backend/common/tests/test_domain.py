import pytest

from common.domain import InvalidTransitionError, apply_transition


class _Fake:
    def __init__(self, status: str):
        self.status = status


def test_apply_transition_succeeds_for_allowed_from():
    obj = _Fake("DRAFT")

    apply_transition(obj, to="SENT", allowed_from={"DRAFT"})

    assert obj.status == "SENT"


def test_apply_transition_rejects_disallowed_from():
    obj = _Fake("SENT")

    with pytest.raises(InvalidTransitionError) as exc_info:
        apply_transition(obj, to="ACCEPTED", allowed_from={"DRAFT"})

    assert exc_info.value.from_status == "SENT"
    assert exc_info.value.to_status == "ACCEPTED"
    assert obj.status == "SENT"  # unchanged on rejection


def test_apply_transition_uses_custom_field_name():
    class _Custom:
        stage = "UPCOMING"

    obj = _Custom()
    apply_transition(obj, to="DUE", allowed_from={"UPCOMING"}, field="stage")

    assert obj.stage == "DUE"
