import math

import pytest

from common.kinematics import forward, integrate_pose, inverse, scale_to_limit

D = 0.065


def test_straight_line_gives_equal_wheel_speeds():
    assert inverse(0.2, 0.0, D) == (0.2, 0.2)


def test_turning_left_makes_the_right_wheel_faster():
    v_l, v_r = inverse(0.2, 0.5, D)
    assert v_r > v_l
    assert v_l == pytest.approx(0.2 - 0.5 * D)
    assert v_r == pytest.approx(0.2 + 0.5 * D)


def test_spinning_in_place_gives_opposite_wheel_speeds():
    v_l, v_r = inverse(0.0, 1.0, D)
    assert v_l == pytest.approx(-v_r)


@pytest.mark.parametrize("v, w", [(0.2, 0.0), (0.2, 0.2), (0.1, -0.7), (0.0, 1.0)])
def test_forward_undoes_inverse(v, w):
    v2, w2 = forward(*inverse(v, w, D), D)
    assert v2 == pytest.approx(v)
    assert w2 == pytest.approx(w)


def test_scale_keeps_speeds_that_fit():
    assert scale_to_limit(0.2, 0.3, 0.5) == (0.2, 0.3, 1.0)


def test_scale_reduces_both_wheels_in_the_same_proportion():
    v_l, v_r, k = scale_to_limit(0.4, 1.0, 0.5)

    assert k == pytest.approx(0.5)
    assert v_r == pytest.approx(0.5)
    assert v_l / v_r == pytest.approx(0.4 / 1.0)  # mismo radio de giro


def test_integrate_straight():
    x, y, theta = integrate_pose(0, 0, 0, 0.2, 0.0, 5.0)
    assert (x, y, theta) == pytest.approx((1.0, 0.0, 0.0))


def test_integrate_full_circle_returns_to_start():
    x, y, theta = integrate_pose(0, 0, 0, 0.2, 0.2, 2 * math.pi / 0.2)
    assert (x, y) == pytest.approx((0.0, 0.0), abs=1e-9)
    assert theta == pytest.approx(2 * math.pi)
