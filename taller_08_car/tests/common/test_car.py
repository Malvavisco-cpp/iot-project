import pytest

from common import messages
from common.car import Car, ticks_diff

D = 0.065
MAX = 0.5


class FakeMotor:
    def __init__(self):
        self.speed = 0.0
        self.stops = 0

    def set_speed(self, speed):
        self.speed = speed

    def stop(self):
        self.speed = 0.0
        self.stops += 1


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


class Rig:
    def __init__(self):
        self.now = 1000
        self.node = FakeNode()
        self.left = FakeMotor()
        self.right = FakeMotor()
        self.car = Car(self.node, self.left, self.right, D, MAX, clock=lambda: self.now, max_duration_s=30.0)

    def advance(self, ms):
        end = self.now + ms
        while self.now < end:
            self.now += 20
            self.car.tick()

    def states(self):
        return [msg for topic, msg in self.node.published if topic == messages.TOPIC_STATE]


@pytest.fixture
def rig():
    return Rig()


def test_subscribes_to_cmd_and_stop(rig):
    assert messages.TOPIC_CMD in rig.node.subscriptions
    assert messages.TOPIC_STOP in rig.node.subscriptions


def test_a_command_drives_the_wheels_with_inverse_kinematics(rig):
    rig.node.deliver(messages.TOPIC_CMD, messages.build_cmd(0.2, 0.5, 2.0))

    assert rig.car.moving
    assert rig.left.speed == pytest.approx(0.2 - 0.5 * D)
    assert rig.right.speed == pytest.approx(0.2 + 0.5 * D)


def test_the_car_stops_by_itself_when_t_is_over(rig):
    rig.node.deliver(messages.TOPIC_CMD, messages.build_cmd(0.2, 0.0, 1.0))

    rig.advance(980)
    assert rig.car.moving

    rig.advance(40)
    assert not rig.car.moving
    assert rig.left.speed == 0.0 and rig.right.speed == 0.0


def test_stop_topic_brakes_immediately(rig):
    rig.node.deliver(messages.TOPIC_CMD, messages.build_cmd(0.2, 0.0, 10.0))
    rig.node.deliver(messages.TOPIC_STOP, {})

    assert not rig.car.moving
    assert rig.left.speed == 0.0 and rig.right.speed == 0.0


def test_a_new_command_replaces_the_running_one(rig):
    rig.node.deliver(messages.TOPIC_CMD, messages.build_cmd(0.2, 0.0, 10.0))
    rig.node.deliver(messages.TOPIC_CMD, messages.build_cmd(-0.1, 0.0, 1.0))

    assert rig.left.speed == pytest.approx(-0.1)
    rig.advance(1100)
    assert not rig.car.moving


def test_publishes_state_when_starting_and_stopping(rig):
    rig.node.deliver(messages.TOPIC_CMD, messages.build_cmd(0.2, 0.0, 0.5))
    rig.advance(600)

    states = rig.states()
    assert [s["moving"] for s in states] == [True, False]
    for s in states:
        messages.validate_state(s)


def test_saturated_wheel_scales_speed_and_stretches_time(rig):
    # Spin rápido: |v_l| = |v_r| = 20 * 0.065 = 1.3 m/s > 0.5
    rig.node.deliver(messages.TOPIC_CMD, messages.build_cmd(0.0, 20.0, 0.5))

    assert abs(rig.right.speed) == pytest.approx(MAX)
    assert rig.left.speed == pytest.approx(-rig.right.speed)
    k = MAX / (20.0 * D)
    assert rig.states()[-1]["t"] == pytest.approx(0.5 / k)  # mismo ángulo girado, más lento


def test_duration_is_capped(rig):
    rig.node.deliver(messages.TOPIC_CMD, messages.build_cmd(0.1, 0.0, 999.0))
    assert rig.states()[-1]["t"] == 30.0


@pytest.mark.parametrize("bad", [None, [], {}, {"v": 0.2, "w": 0}, {"v": "0.2", "w": 0, "t": 1}, {"v": 0.2, "w": 0, "t": 0}])
def test_malformed_commands_are_ignored(rig, bad):
    rig.node.deliver(messages.TOPIC_CMD, bad)
    assert not rig.car.moving


def test_publish_failure_does_not_prevent_stopping(rig):
    def broken(topic, msg):
        raise OSError("sin red")

    rig.node.publish = broken
    rig.node.deliver(messages.TOPIC_CMD, messages.build_cmd(0.2, 0.0, 0.5))
    rig.advance(600)

    assert not rig.car.moving


def test_stop_survives_tick_counter_wraparound():
    now = {"t": (1 << 30) - 100}
    node, left, right = FakeNode(), FakeMotor(), FakeMotor()
    car = Car(node, left, right, D, MAX, clock=lambda: now["t"])

    car.drive(0.2, 0.0, 0.5)
    now["t"] = (now["t"] + 600) & ((1 << 30) - 1)  # el contador dio la vuelta
    car.tick()

    assert not car.moving
    assert ticks_diff(5, (1 << 30) - 5) == 10
