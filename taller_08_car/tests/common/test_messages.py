import pytest

from common import messages


def test_build_cmd():
    assert messages.build_cmd(0.2, -0.2, 7.85) == {"v": 0.2, "w": -0.2, "t": 7.85}


def test_valid_cmd_passes():
    messages.validate_cmd(messages.build_cmd(0.2, 0.0, 5.0))
    messages.validate_cmd(messages.build_cmd(-0.1, 1, 2))


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {},
        {"v": 0.2, "w": 0.0},
        {"v": "0.2", "w": 0.0, "t": 5},
        {"v": True, "w": 0.0, "t": 5},
        {"v": 0.2, "w": 0.0, "t": 0},
        {"v": 0.2, "w": 0.0, "t": -1},
        {"v": float("nan"), "w": 0.0, "t": 5},
        {"v": 0.2, "w": float("inf"), "t": 5},
    ],
)
def test_invalid_cmd_is_rejected(payload):
    with pytest.raises(ValueError):
        messages.validate_cmd(payload)


def test_state_round_trip():
    messages.validate_state(messages.build_state(True, 0.2, 0.0, 5.0, 0.2, 0.2))


@pytest.mark.parametrize("payload", [None, {}, {"moving": 1}, {"moving": True, "v": 0.2}])
def test_invalid_state_is_rejected(payload):
    with pytest.raises(ValueError):
        messages.validate_state(payload)
