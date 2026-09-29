import pytest

from common import messages


def test_build_angle():
    assert messages.build_angle(20.0) == {"angle": 20.0}
    assert messages.build_angle(-45) == {"angle": -45}


def test_valid_angle_passes_validation():
    messages.validate_angle(messages.build_angle(20.0))
    messages.validate_angle(messages.build_angle(-45))
    messages.validate_angle({"angle": 0})


@pytest.mark.parametrize("payload", [None, [], "20", {}, {"angle": "20"}, {"angle": True}, {"angle": None}])
def test_invalid_angle_is_rejected(payload):
    with pytest.raises(ValueError):
        messages.validate_angle(payload)


def test_build_duty():
    assert messages.build_duty(4000) == {"duty_u16": 4000}


def test_valid_duty_passes_validation():
    messages.validate_duty(messages.build_duty(0))
    messages.validate_duty(messages.build_duty(65535))
    messages.validate_duty(messages.build_duty(4000))


@pytest.mark.parametrize(
    "payload",
    [None, [], "4000", {}, {"duty_u16": "4000"}, {"duty_u16": True}, {"duty_u16": -1}, {"duty_u16": 65536}],
)
def test_invalid_duty_is_rejected(payload):
    with pytest.raises(ValueError):
        messages.validate_duty(payload)
