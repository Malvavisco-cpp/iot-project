"""Evaluación 6: el robot hace lo mismo que su gemelo virtual, al mismo tiempo.

Se ejecuta la misma coreografía en el robot (MotionPlayer + Choreographer, el
código que corre en el Pico) y en un port de RoDifArm.js, y se comparan
velocidades, brazo y posición a lo largo del tiempo.
"""

import math

import pytest

from common import motion
from common.choreographer import Choreographer
from common.kinematics import integrate_pose
from common.player import MotionPlayer
from common.timeutil import unix_ms_to_iso
from flet_ui import model
from twin_model import TwinRobot

FRAME_MS = 16      # el gemelo se dibuja a ~60 fps
TICK_MS = 20       # MotionTask del Pico


class PoseDrive:
    """Tracción falsa que integra la pose con v y w (como haría el carro real)."""

    def __init__(self):
        self.v = self.w = 0.0

    def drive(self, v, w):
        self.v, self.w = v, w

    def stop(self):
        self.v = self.w = 0.0


class FakeArm:
    def __init__(self):
        self.angles = (0.0, 0.0, 0.0)

    def set(self, a0, a1, a2):
        self.angles = (a0, a1, a2)


class Robot:
    def __init__(self, unix_ms):
        self.ticks = 0
        self.unix_ms = unix_ms
        self.pose = (0.0, 0.0, 0.0)
        self.drive = PoseDrive()
        self.arm = FakeArm()
        self.player = MotionPlayer(self.drive, self.arm, lambda: self.ticks)
        self.choreo = Choreographer(self.player, lambda: self.unix_ms)

    def advance(self, ms):
        self.pose = integrate_pose(*self.pose, self.drive.v, self.drive.w, ms / 1000)
        self.ticks += ms
        self.unix_ms += ms
        self.choreo.tick()
        self.player.tick()


def run_both(states, total_ms, start_delay_ms=0, check=None):
    t0 = 1_760_000_000_000
    robot = Robot(t0)
    twin = TwinRobot()

    robot.choreo.handle(motion.build_create("c", states))
    robot.choreo.handle(motion.build_schedule("c", unix_ms_to_iso(t0 + start_delay_ms)))

    t_robot = t_twin = 0
    twin_started = False
    for t in range(0, total_ms + 1, 4):
        while t_robot + TICK_MS <= t:
            t_robot += TICK_MS
            robot.advance(TICK_MS)
        while t_twin + FRAME_MS <= t:
            t_twin += FRAME_MS
            if not twin_started and t_twin >= start_delay_ms:
                twin.run_sequence(states)   # setTimeout(run_at - Date.now())
                twin_started = True
                twin.update((t_twin - start_delay_ms) / 1000)
            else:
                twin.update(FRAME_MS / 1000)
        if check and t % 100 == 0 and t >= start_delay_ms:
            check(t, robot, twin)
    return robot, twin


def test_the_example_choreography_matches_the_twin_over_time():
    c = model.Choreography()
    c.load_example()
    max_err = {"arm": 0.0}

    def check(t, robot, twin):
        twin_deg = [math.degrees(a) for a in twin.alpha]
        err = max(abs(r - w) for r, w in zip(robot.arm.angles, twin_deg))
        max_err["arm"] = max(max_err["arm"], err)

    robot, twin = run_both(c.states, 15100, start_delay_ms=2000, check=check)

    # El brazo nunca se separa más de lo que gira en un par de ticks (a 90°/s).
    assert max_err["arm"] < 4.0
    # Al final los dos están quietos, en el mismo lugar y con el brazo igual.
    assert not robot.player.active and twin.motion is None
    rx, ry, rth = robot.pose
    assert rx == pytest.approx(twin.x, abs=0.05)
    assert ry == pytest.approx(-twin.y, abs=0.05)          # el gemelo usa y hacia abajo
    assert rth == pytest.approx(twin.beta, abs=0.02)
    assert robot.arm.angles == pytest.approx([math.degrees(a) for a in twin.alpha], abs=0.01)


def test_both_start_at_run_at_not_when_the_message_arrives():
    states = [motion.build_state(2, 0, 0, 0, 0, 1.0)]
    seen = {}

    def check(t, robot, twin):
        if robot.player.active and "robot" not in seen:
            seen["robot"] = t
        if twin.motion and "twin" not in seen:
            seen["twin"] = t

    run_both(states, 4000, start_delay_ms=3000, check=check)
    assert seen["robot"] == pytest.approx(3000, abs=100)
    assert seen["twin"] == pytest.approx(3000, abs=100)


def test_missing_angles_hold_like_the_twin():
    states = [
        {"alpha1_deg": 60, "duration_s": 1},
        {"v_dm/s": 1, "duration_s": 1},          # sin ángulos: el brazo se queda
        {"alpha0_deg": -45, "duration_s": 1},    # alpha1 se mantiene en 60
    ]
    robot, twin = run_both(states, 3500)
    assert robot.arm.angles == pytest.approx((-45, 60, 0), abs=0.01)
    assert robot.arm.angles == pytest.approx([math.degrees(a) for a in twin.alpha], abs=0.01)
