from common.masking import mask_tail


def test_mask_tail_keeps_last_four_digits_by_default():
    assert mask_tail("0241234567") == "•••• 4567"


def test_mask_tail_returns_empty_string_for_blank_input():
    assert mask_tail("") == ""


def test_mask_tail_returns_whole_value_when_shorter_than_visible_length():
    assert mask_tail("123") == "•••• 123"
