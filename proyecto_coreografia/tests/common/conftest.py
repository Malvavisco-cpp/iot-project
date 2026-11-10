import pytest

from common.choreographer import Choreographer
from common.player import MotionPlayer
from common.robot import RobotNode


class FakeDrive:
    def __init__(self):
        self.v = 0.0
        self.w = 0.0
        self.calls = []

    def drive(self, v, w):
        self.v, self.w = v, w
        self.calls.append((v, w))

    def stop(self):
        self.v = self.w = 0.0
        self.calls.append("stop")


class FakeArm:
    def __init__(self):
        self.angles = (0.0, 0.0, 0.0)

    def set(self, a0, a1, a2):
        self.angles = (a0, a1, a2)


class FakeNode:
    """Como Node de PicoROS: llama callback(topic=..., msg=...)."""

    def __init__(self):
        self.subscriptions = {}
        self.published = []

    def subscribe(self, topic, callback):
        self.subscriptions[topic] = callback

    def publish(self, topic, msg):
        self.published.append((topic, msg))

    def deliver(self, topic, msg):
        self.subscriptions[topic](topic=topic, msg=msg)


class World:
    """Robot completo con reloj de ticks y hora real controlados por el test."""

    def __init__(self):
        self.ticks = 5000
        self.unix_ms = 1_760_000_000_000  # None = sin NTP
        self.drive = FakeDrive()
        self.arm = FakeArm()
        self.node = FakeNode()
        self.player = MotionPlayer(self.drive, self.arm, lambda: self.ticks)
        self.choreo = Choreographer(self.player, lambda: self.unix_ms)
        self.robot = RobotNode(self.node, self.player, self.choreo, clock_synced=lambda: self.unix_ms is not None)

    def advance(self, ms, step=20):
        end = self.ticks + ms
        while self.ticks < end:
            dt = min(step, end - self.ticks)
            self.ticks += dt
            if self.unix_ms is not None:
                self.unix_ms += dt
            self.choreo.tick()
            self.player.tick()

    def statuses(self):
        return [m for t, m in self.node.published if t == "motion/status"]


@pytest.fixture
def world():
    return World()
