import pytest

from common.motor import MiniMotor, Motor


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


# --------------------------------------------------------------------------
# L298N mini: PWM directo en IN1/IN2
# --------------------------------------------------------------------------

def make_mini(inverted=False):
    in1, in2 = FakePWM(), FakePWM()
    return MiniMotor(in1, in2, max_speed=0.5, inverted=inverted), in1, in2


def test_mini_starts_stopped():
    _, in1, in2 = make_mini()
    assert (in1.duty, in2.duty) == (0, 0)


def test_mini_forward_puts_pwm_on_in1():
    motor, in1, in2 = make_mini()
    motor.set_speed(0.25)

    assert in1.duty == pytest.approx(65535 / 2, abs=1)
    assert in2.duty == 0


def test_mini_backward_puts_pwm_on_in2():
    motor, in1, in2 = make_mini()
    motor.set_speed(-0.25)

    assert in1.duty == 0
    assert in2.duty == pytest.approx(65535 / 2, abs=1)


def test_mini_inverted_swaps_the_pins():
    motor, in1, in2 = make_mini(inverted=True)
    motor.set_speed(0.25)
    assert in1.duty == 0 and in2.duty > 0


def test_mini_saturates_and_stops():
    motor, in1, in2 = make_mini()
    motor.set_speed(9.0)
    assert in1.duty == 65535

    motor.set_speed(0)
    assert (in1.duty, in2.duty) == (0, 0)
