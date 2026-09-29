import pytest

from common.servo import Servo


class FakePWM:
    def __init__(self):
        self.duty = None

    def set_duty_u16(self, value: int) -> None:
        self.duty = value


@pytest.fixture
def pwm():
    return FakePWM()


@pytest.fixture
def servo(pwm):
    return Servo(
        pwm,
        min_angle=-90.0,
        max_angle=90.0,
        min_pulse_ms=0.5,
        max_pulse_ms=2.5,
        freq_hz=50.0,
    )


def test_min_angle_maps_to_min_pulse(servo, pwm):
    servo.set_angle(-90.0)

    period_ms = 1000.0 / 50.0
    expected = round((0.5 / period_ms) * 65535)
    assert pwm.duty == expected


def test_max_angle_maps_to_max_pulse(servo, pwm):
    servo.set_angle(90.0)

    period_ms = 1000.0 / 50.0
    expected = round((2.5 / period_ms) * 65535)
    assert pwm.duty == expected


def test_midpoint_angle_maps_to_midpoint_pulse(servo, pwm):
    servo.set_angle(0.0)

    period_ms = 1000.0 / 50.0
    expected = round((1.5 / period_ms) * 65535)  # (0.5 + 2.5) / 2
    assert pwm.duty == expected


def test_angle_above_range_is_clamped(servo, pwm):
    servo.set_angle(200.0)

    assert servo.angle == 90.0
    period_ms = 1000.0 / 50.0
    assert pwm.duty == round((2.5 / period_ms) * 65535)


def test_angle_below_range_is_clamped(servo, pwm):
    servo.set_angle(-200.0)

    assert servo.angle == -90.0


def test_set_angle_records_the_clamped_angle(servo):
    servo.set_angle(45.0)
    assert servo.angle == 45.0


def test_min_angle_must_be_less_than_max_angle(pwm):
    with pytest.raises(ValueError):
        Servo(pwm, min_angle=90.0, max_angle=90.0, min_pulse_ms=0.5, max_pulse_ms=2.5, freq_hz=50.0)


def test_a_different_angle_range_still_maps_correctly(pwm):
    # Rango 0-180, como un servo típico, en vez de -90..90.
    servo = Servo(pwm, min_angle=0.0, max_angle=180.0, min_pulse_ms=1.0, max_pulse_ms=2.0, freq_hz=50.0)

    servo.set_angle(0.0)
    period_ms = 1000.0 / 50.0
    assert pwm.duty == round((1.0 / period_ms) * 65535)

    servo.set_angle(180.0)
    assert pwm.duty == round((2.0 / period_ms) * 65535)
