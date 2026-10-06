import pytest

from common.motor import Motor


class FakePWM:
    def __init__(self):
        self.duty = None

    def duty_u16(self, value):
        self.duty = value


class FakePin:
    def __init__(self):
        self.level = None

    def value(self, level):
        self.level = level


def make(inverted=False):
    pwm, in1, in2 = FakePWM(), FakePin(), FakePin()
    return Motor(pwm, in1, in2, max_speed=0.5, inverted=inverted), pwm, in1, in2


def test_starts_stopped():
    _, pwm, in1, in2 = make()
    assert (pwm.duty, in1.level, in2.level) == (0, 0, 0)


def test_forward_sets_direction_and_proportional_duty():
    motor, pwm, in1, in2 = make()
    motor.set_speed(0.25)  # mitad de max_speed

    assert (in1.level, in2.level) == (1, 0)
    assert pwm.duty == pytest.approx(65535 / 2, abs=1)


def test_backward_flips_the_direction_pins():
    motor, pwm, in1, in2 = make()
    motor.set_speed(-0.25)

    assert (in1.level, in2.level) == (0, 1)
    assert pwm.duty == pytest.approx(65535 / 2, abs=1)


def test_inverted_motor_swaps_the_meaning_of_forward():
    motor, _, in1, in2 = make(inverted=True)
    motor.set_speed(0.25)
    assert (in1.level, in2.level) == (0, 1)


def test_speed_above_max_saturates_at_full_duty():
    motor, pwm, _, _ = make()
    motor.set_speed(2.0)
    assert pwm.duty == 65535


def test_zero_speed_stops():
    motor, pwm, in1, in2 = make()
    motor.set_speed(0.3)
    motor.set_speed(0)

    assert (pwm.duty, in1.level, in2.level) == (0, 0, 0)
    assert motor.speed == 0.0
