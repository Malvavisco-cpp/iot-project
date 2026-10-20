"""Cinemática del MeArm comparada contra el código original del notebook 09.

REF se generó corriendo `solve_third_point` + `update11` del notebook tal cual.
"""

import math

import pytest

from common import mearm

REF = {
    (90, -180): {"c": (-0.4, 0.8), "d": (0.0, 0.8), "f": (-0.35, 0.8), "h": (0.8, 1.0), "i": (0.8, 0.8), "j": (1.041481, 0.864705)},
    (60, -150): {"c": (0.0, 0.69282), "d": (0.4, 0.69282), "f": (0.096891, 0.51782), "h": (1.09282, 1.29282), "i": (1.09282, 1.09282), "j": (1.334302, 1.157525)},
    (110, 160): {"c": (-0.673616, 0.751754), "d": (-0.273616, 0.751754), "f": (-0.602509, 0.871461), "h": (0.478138, 0.678138), "i": (0.478138, 0.478138), "j": (0.719619, 0.542843)},
    (90, -135): {"c": (-0.4, 0.8), "d": (0.0, 0.8), "f": (-0.247487, 0.552513), "h": (0.565685, 1.565685), "i": (0.565685, 1.365685), "j": (0.807167, 1.43039)},
    (130, 170): {"c": (-0.91423, 0.612836), "d": (-0.51423, 0.612836), "f": (-0.858913, 0.673612), "h": (0.273616, 0.673917), "i": (0.273616, 0.473917), "j": (0.515098, 0.538622)},
    (75, -160): {"c": (-0.192945, 0.772741), "d": (0.207055, 0.772741), "f": (-0.121837, 0.653034), "h": (0.958809, 1.246357), "i": (0.958809, 1.046357), "j": (1.200291, 1.111062)},
}

POSES = list(REF)


@pytest.mark.parametrize("q", POSES)
def test_forward_matches_the_notebook(q):
    points = mearm.forward(*q)
    for name, expected in REF[q].items():
        assert points[name] == pytest.approx(expected, abs=1e-5), name


@pytest.mark.parametrize("q", POSES)
def test_parallelogram_forearm_angle_is_q2_plus_180(q):
    p = mearm.forward(*q)
    forearm = math.degrees(math.atan2(p["i"][1] - p["d"][1], p["i"][0] - p["d"][0]))
    assert mearm.wrap_deg(forearm - (q[1] + 180)) == pytest.approx(0, abs=1e-6)


@pytest.mark.parametrize("q", POSES)
def test_gripper_always_keeps_the_same_angle(q):
    p = mearm.forward(*q)
    angle = math.degrees(math.atan2(p["j"][1] - p["i"][1], p["j"][0] - p["i"][0]))
    assert angle == pytest.approx(mearm.gripper_angle_deg()) == pytest.approx(15.0)


def same_angles(got, expected):
    return all(abs(mearm.wrap_deg(g - e)) < 1e-6 for g, e in zip(got, expected))


@pytest.mark.parametrize("q", POSES)
def test_inverse_undoes_forward_for_the_tip_and_the_wrist(q):
    p = mearm.forward(*q)
    assert same_angles(mearm.inverse(*p["j"]), q)
    assert same_angles(mearm.inverse(*p["i"], target="wrist"), q)


@pytest.mark.parametrize("xy", [(3.0, 0.0), (0.0, 0.0)])
def test_out_of_reach_points_raise(xy):
    with pytest.raises(ValueError):
        mearm.inverse(*xy, target="wrist")


def test_a_point_next_to_the_shoulder_needs_a_fully_folded_elbow():
    # Geométricamente se alcanza (brazo y antebrazo miden igual), pero el codo
    # queda casi a -180°: fuera de lo que el MeArm puede hacer.
    a1, a2 = mearm.twin_from_servos(*mearm.inverse(0.01, 0.0, target="wrist"))
    assert mearm.elbow_relative_deg(a1, a2) == pytest.approx(-180, abs=1)
    assert not mearm.check_reachable(a1, a2, -160, -20)


def test_solve_third_point_gives_both_solutions():
    r1, r2 = mearm.solve_third_point((0, 0), (2, 0), math.sqrt(2), math.sqrt(2))
    assert r1 == pytest.approx((1, 1)) and r2 == pytest.approx((1, -1))
    with pytest.raises(ValueError):
        mearm.solve_third_point((0, 0), (5, 0), 1, 1)


def test_law_of_cosines():
    assert mearm.law_cos(1, 1, 1) == pytest.approx(math.pi / 3)
    assert math.degrees(mearm.law_cos(5, 3, 4)) == pytest.approx(90)


def test_twin_mapping_round_trip():
    assert mearm.twin_from_servos(90, -180) == (90, 0)          # brazo vertical, antebrazo horizontal
    assert mearm.servos_from_twin(67.5, -67.5) == (67.5, 112.5)
    for a1, a2 in [(45, 30), (90, 0), (67.5, -67.5)]:
        assert mearm.twin_from_servos(*mearm.servos_from_twin(a1, a2)) == pytest.approx((a1, a2))


@pytest.mark.parametrize(
    "alpha1, alpha2, ok",
    [
        (67.5, -67.5, True),   # pose de ejemplo del gemelo: codo relativo -135°
        (90, 0, True),         # -90°
        (45, 30, True),        # -15°: ojo, cerca del límite real
        (0, 0, False),         # brazo estirado: el paralelogramo se aplana
        (0, 90, False),        # el último estado del ejemplo de motionTopics.md
    ],
)
def test_reachability(alpha1, alpha2, ok):
    assert mearm.check_reachable(alpha1, alpha2, -170, -10) == ok


def test_wrap():
    assert mearm.wrap_deg(190) == -170
    assert mearm.wrap_deg(-180) == 180
