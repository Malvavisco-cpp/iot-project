import math

import pytest

from common import motion

HERE = (10.0, 20.0, 30.0)


def test_units_are_converted_like_the_twin():
    s = motion.parse_state(
        {"v_dm/s": 2, "w_deg/s": 90, "alpha0_deg": 0, "alpha1_deg": 45, "alpha2_deg": -30, "duration_s": 1.5},
        HERE,
    )
    assert s["v"] == pytest.approx(0.2)            # dm/s -> m/s
    assert s["w"] == pytest.approx(math.pi / 2)    # °/s -> rad/s
    assert s["angles"] == (0.0, 45.0, -30.0)
    assert s["duration_ms"] == 1500


def test_missing_fields_follow_the_twin():
    s = motion.parse_state({}, HERE)
    assert s["v"] == 0 and s["w"] == 0
    assert s["angles"] == HERE          # el brazo se queda donde está
    assert s["duration_ms"] == 1000     # 1 s por defecto


def test_alfa_spelling_of_robot_coreografia_mqtt_html_is_accepted():
    s = motion.parse_state({"alfa0_deg": 5, "alfa1_deg": 6, "alfa2_deg": 7}, HERE)
    assert s["angles"] == (5.0, 6.0, 7.0)


def test_alpha_wins_over_alfa():
    assert motion.parse_state({"alpha0_deg": 1, "alfa0_deg": 99}, HERE)["angles"][0] == 1.0


def test_invalid_numbers_fall_back_like_number_in_js():
    s = motion.parse_state({"v_dm/s": "rápido", "alpha0_deg": None, "duration_s": float("nan")}, HERE)
    assert s["v"] == 0.0
    assert s["angles"][0] == 0.0        # presente pero inválido -> 0 (como el gemelo)
    assert s["duration_ms"] == 1000


def test_numeric_strings_are_accepted():
    assert motion.parse_state({"v_dm/s": "2.5"}, HERE)["v"] == pytest.approx(0.25)


def test_duration_has_a_minimum():
    assert motion.parse_state({"duration_s": 0}, HERE)["duration_ms"] == 1
    assert motion.parse_state({"duration_s": -5}, HERE)["duration_ms"] == 1


@pytest.mark.parametrize("bad", [None, [], "hola", 3])
def test_non_objects_are_rejected(bad):
    with pytest.raises(ValueError):
        motion.parse_state(bad, HERE)


def test_build_state_sends_both_spellings_and_round_trips():
    payload = motion.build_state(2, -11.4592, 0, 45, 30, 7.854)

    assert payload["alpha1_deg"] == payload["alfa1_deg"] == 45
    s = motion.parse_state(payload, HERE)
    assert s["angles"] == (0.0, 45.0, 30.0)
    assert s["duration_ms"] == 7854


def test_sequence_builders():
    st = [motion.build_state(1, 0, 0, 0, 0, 1)]
    assert motion.build_create("hello", st) == {"action": "create", "name": "hello", "states": st}
    assert motion.build_delete("hello") == {"action": "delete", "name": "hello"}
    assert motion.build_schedule("hello") == {"action": "schedule", "name": "hello", "run_at": "now"}
    assert motion.build_execute_now("hello")["action"] == "execute_now"
