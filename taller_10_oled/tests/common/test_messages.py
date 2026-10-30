import pytest

from common import messages


def test_defaults_are_applied():
    assert messages.validate_text({"text": "hola"}) == ("hola", 0, 0, 1, False)


def test_build_text_round_trips_through_validate():
    msg = messages.build_text("hola", 16, 24, 0, True)
    assert messages.validate_text(msg) == ("hola", 16, 24, 0, True)


def test_empty_text_is_only_valid_with_clear():
    assert messages.validate_text({"text": "", "clear": True}) == ("", 0, 0, 1, True)
    with pytest.raises(ValueError):
        messages.validate_text({"text": ""})


@pytest.mark.parametrize(
    "bad",
    [
        None,
        [],
        "hola",
        {},
        {"text": 5},
        {"text": "a", "x": -1},
        {"text": "a", "x": 128},
        {"text": "a", "y": 64},
        {"text": "a", "x": "0"},
        {"text": "a", "x": 1.5},
        {"text": "a", "x": True},
        {"text": "a", "color": 2},
        {"text": "a", "color": True},
        {"text": "a", "clear": "si"},
    ],
)
def test_malformed_messages_are_rejected(bad):
    with pytest.raises(ValueError):
        messages.validate_text(bad)
