"""Servo, brazo y tracción con dobles (sin machine)."""

import pytest

from common.arm import Arm
from common.drive import DiffDrive
from common.servo import Servo


class FakePWM:
    def __init__(self):
        self.duty = None

    def duty_u16(self, value):
        self.duty = value


def duty_for_pulse(ms, freq=50):
    return int(ms * freq / 1000 * 65535 + 0.5)


@pytest.mark.parametrize("angle, pulse", [(-90, 0.5), (0, 1.5), (90, 2.5), (45, 2.0)])
def test_servo_maps_angle_to_pulse(angle, pulse):
    pwm = FakePWM()
    Servo(pwm).set_angle(angle)
    assert pwm.duty == duty_for_pulse(pulse)


def test_servo_is_clamped_to_its_limit():
    pwm = FakePWM()
    Servo(pwm, limit_deg=60).set_angle(200)
    assert pwm.duty == duty_for_pulse(1.5 + 60 / 90)


def test_servo_offset_and_inversion():
    pwm = FakePWM()
    Servo(pwm, offset_deg=10).set_angle(0)
    assert pwm.duty == Servo(FakePWM()).angle_to_duty_u16(10)

    s = Servo(pwm, inverted=True)
    assert s.angle_to_duty_u16(30) == Servo(FakePWM()).angle_to_duty_u16(-30)


class FakeServo:
    def __init__(self):
        self.angle = None

    def set_angle(self, angle):
        self.angle = angle


def test_elbow_servo_gets_alpha2_minus_alpha1_like_the_twin():
    base, shoulder, elbow = FakeServo(), FakeServo(), FakeServo()
    arm = Arm(base, shoulder, elbow)
    arm.set(90, 67.5, -67.5)

    assert (base.angle, shoulder.angle) == (90, 67.5)
    assert elbow.angle == pytest.approx(-135)     # rotation.z = alpha2 - alpha1
    assert arm.angles == (90, 67.5, -67.5)


def test_arm_starts_at_zero():
    elbow = FakeServo()
    arm = Arm(FakeServo(), FakeServo(), elbow)
    assert arm.angles == (0.0, 0.0, 0.0) and elbow.angle == 0


class FakeMotor:
    def __init__(self):
        self.speed = None

    def set_speed(self, s):
        self.speed = s

    def stop(self):
        self.speed = 0.0


def test_drive_uses_inverse_kinematics():
    left, right = FakeMotor(), FakeMotor()
    d = DiffDrive(left, right, 0.065, 0.5)
    d.drive(0.2, 1.0)
    assert left.speed == pytest.approx(0.2 - 0.065)
    assert right.speed == pytest.approx(0.2 + 0.065)


def test_drive_saturation_keeps_the_turning_radius():
    left, right = FakeMotor(), FakeMotor()
    d = DiffDrive(left, right, 0.065, 0.5)
    d.drive(0.9, 2.0)  # rueda derecha pediría 1.03 m/s

    assert right.speed == pytest.approx(0.5)
    assert left.speed / right.speed == pytest.approx((0.9 - 0.13) / (0.9 + 0.13))
    assert d.v / d.w == pytest.approx(0.9 / 2.0)  # mismo radio


def test_drive_stop():
    left, right = FakeMotor(), FakeMotor()
    d = DiffDrive(left, right, 0.065, 0.5)
    d.drive(0.2, 0)
    d.stop()
    assert left.speed == right.speed == 0.0


def test_drive_calibration_matches_the_measured_values_at_v_04():
    # v = 0.4: recta w = 0.6, izquierda w = 0.4 * 5.4375 = 2.175, derecha w = -0.4 * 4.75 = -1.9
    for w, expected in ((0.0, 0.6), (0.4, 2.175), (-0.4, -1.9)):
        left, right = FakeMotor(), FakeMotor()
        d = DiffDrive(left, right, 0.065, 5.0, straight_w_trim=0.6, arc_w_gain_left=5.4375, arc_w_gain_right=4.75)
        d.drive(0.4, w)
        assert (right.speed - left.speed) / (2 * 0.065) == pytest.approx(expected)


def test_drive_calibration_leaves_spins_and_defaults_alone():
    left, right = FakeMotor(), FakeMotor()
    d = DiffDrive(left, right, 0.065, 5.0, straight_w_trim=0.6, arc_w_gain_left=5.4375, arc_w_gain_right=4.75)
    d.drive(0.0, 1.0)  # giro en el sitio
    assert (right.speed - left.speed) / (2 * 0.065) == pytest.approx(1.0)

    left, right = FakeMotor(), FakeMotor()
    DiffDrive(left, right, 0.065, 5.0).drive(0.4, 0.0)  # sin calibración: recto de verdad
    assert left.speed == right.speed == pytest.approx(0.4)


def test_drive_reports_the_requested_v_w_not_the_corrected_ones():
    left, right = FakeMotor(), FakeMotor()
    d = DiffDrive(left, right, 0.065, 5.0, straight_w_trim=0.6)
    d.drive(0.4, 0.0)
    assert (d.v, d.w) == (0.4, 0.0)


def test_arm_without_a_base_servo_ignores_alpha0():
    shoulder, elbow = FakeServo(), FakeServo()
    arm = Arm(None, shoulder, elbow)
    arm.set(90, 30, -30)

    assert shoulder.angle is not None and elbow.angle is not None
    assert arm.angles == (90, 30, -30)  # alpha0 se guarda (como el gemelo) pero no mueve nada
