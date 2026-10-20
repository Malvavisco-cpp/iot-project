import math

import pytest

from common import motion


def st(v=0, w=0, a0=0, a1=0, a2=0, t=1.0):
    return motion.build_state(v, w, a0, a1, a2, t)


def test_state_applies_v_and_w_in_si_units(world):
    world.player.play([st(v=2, w=90, t=1)])
    assert world.drive.v == pytest.approx(0.2)
    assert world.drive.w == pytest.approx(math.pi / 2)


def test_arm_is_interpolated_linearly_over_the_duration(world):
    world.player.play([st(a0=90, a1=-40, a2=20, t=2)])

    world.advance(1000)
    assert world.arm.angles == pytest.approx((45, -20, 10))
    world.advance(1000)
    assert world.arm.angles == pytest.approx((90, -40, 20))


def test_robot_stops_after_the_last_state_and_arm_stays(world):
    world.player.play([st(v=2, a1=30, t=1)])
    world.advance(1020)

    assert not world.player.active
    assert world.drive.calls[-1] == "stop"
    assert world.arm.angles == pytest.approx((0, 30, 0))


def test_states_follow_each_other_without_gaps(world):
    world.player.play([st(v=1, t=1), st(v=2, t=0.5), st(v=3, t=1)], name="s")
    starts = {}
    for _ in range(200):
        world.advance(10, step=10)
        starts.setdefault(world.player.index, world.ticks)
    assert starts[2] - 5000 == pytest.approx(1000, abs=10)
    assert starts[3] - 5000 == pytest.approx(1500, abs=10)


def test_a_late_tick_catches_up_instead_of_drifting(world):
    world.player.play([st(v=1, t=1), st(v=2, t=1), st(a0=60, t=1)], name="s")
    world.ticks += 2500           # el Pico estuvo trabado 2.5 s
    world.player.tick()

    assert world.player.index == 3                       # ya va en el tercer estado
    assert world.arm.angles[0] == pytest.approx(30)      # y a la mitad de él
    world.advance(500)
    assert not world.player.active                       # termina a los 3 s exactos


def test_missing_angle_keeps_where_the_previous_state_left_it(world):
    world.player.play([st(a1=50, t=1), {"v_dm/s": 1, "duration_s": 1}], name="s")
    world.advance(2000)
    assert world.arm.angles == pytest.approx((0, 50, 0))


def test_new_play_replaces_the_running_one_from_the_current_pose(world):
    world.player.play([st(a0=100, t=2)])
    world.advance(1000)                   # a0 va en 50
    world.player.play([st(a0=0, t=1)])
    world.advance(500)
    assert world.arm.angles[0] == pytest.approx(25)


def test_stop_halts_the_drive(world):
    world.player.play([st(v=2, t=10)])
    world.player.stop()
    assert not world.player.active and world.drive.calls[-1] == "stop"


def test_invalid_state_inside_a_sequence_is_skipped(world):
    world.player.play(["basura", st(v=1, t=1)], name="s")
    assert world.player.active and world.drive.v == pytest.approx(0.1)


def test_status_reports_progress(world):
    world.player.play([st(t=1), st(t=1)], name="hola")
    assert world.player.status() == {"mode": "sequence", "name": "hola", "step": 1, "steps": 2}
    world.advance(2100)
    assert world.player.status()["mode"] == "idle"
