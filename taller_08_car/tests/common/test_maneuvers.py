"""Cada maniobra, integrada con el modelo, debe terminar donde dice el taller."""

import math

import pytest

from common import maneuvers, messages
from common.kinematics import integrate_pose


def end_pose(cmd):
    return integrate_pose(0.0, 0.0, 0.0, cmd["v"], cmd["w"], cmd["t"])


def test_straight_one_meter():
    cmd = maneuvers.straight(1.0, 0.2)

    assert cmd == {"v": 0.2, "w": 0.0, "t": pytest.approx(5.0)}
    assert end_pose(cmd) == pytest.approx((1.0, 0.0, 0.0))


def test_quarter_circle_left_ends_at_1_1_facing_up():
    cmd = maneuvers.quarter_circle(1.0, 0.2, maneuvers.LEFT)

    assert cmd["w"] == pytest.approx(0.2)                 # w = v / R
    assert cmd["t"] == pytest.approx((math.pi / 2) / 0.2)  # ~7.85 s
    assert end_pose(cmd) == pytest.approx((1.0, 1.0, math.pi / 2))


def test_quarter_circle_right_ends_at_1_minus_1_facing_down():
    cmd = maneuvers.quarter_circle(1.0, 0.2, maneuvers.RIGHT)

    assert cmd["w"] == pytest.approx(-0.2)
    assert end_pose(cmd) == pytest.approx((1.0, -1.0, -math.pi / 2))


def test_the_arc_length_is_a_quarter_of_the_circumference():
    cmd = maneuvers.quarter_circle(1.0, 0.25, maneuvers.LEFT)
    assert cmd["v"] * cmd["t"] == pytest.approx(2 * math.pi * 1.0 / 4)


def test_speed_changes_the_time_not_the_path():
    slow = maneuvers.quarter_circle(1.0, 0.1, maneuvers.LEFT)
    fast = maneuvers.quarter_circle(1.0, 0.4, maneuvers.LEFT)

    assert end_pose(slow) == pytest.approx(end_pose(fast))
    assert slow["t"] == pytest.approx(4 * fast["t"])


def test_maneuvers_produce_valid_commands():
    messages.validate_cmd(maneuvers.straight(1.0, 0.2))
    messages.validate_cmd(maneuvers.quarter_circle(1.0, 0.2, maneuvers.RIGHT))


@pytest.mark.parametrize("speed", [0, -0.2])
def test_non_positive_speed_is_rejected(speed):
    with pytest.raises(ValueError):
        maneuvers.straight(1.0, speed)
    with pytest.raises(ValueError):
        maneuvers.quarter_circle(1.0, speed, maneuvers.LEFT)


def test_unknown_direction_is_rejected():
    with pytest.raises(ValueError):
        maneuvers.quarter_circle(1.0, 0.2, "up")
