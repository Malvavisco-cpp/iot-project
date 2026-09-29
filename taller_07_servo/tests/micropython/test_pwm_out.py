import pytest

from pwm_out import PWMOut


class FakePWM:
    def __init__(self):
        self.duty = None

    def duty_u16(self, value: int) -> None:
        self.duty = value


class FakeNode:
    def __init__(self):
        self.subscriptions = {}

    def subscribe(self, topic, callback):
        self.subscriptions[topic] = callback

    def deliver(self, topic, msg):
        self.subscriptions[topic](topic=topic, msg=msg)


@pytest.fixture
def node():
    return FakeNode()


@pytest.fixture
def pwm():
    return FakePWM()


@pytest.fixture
def pwm_out(pwm, node):
    return PWMOut(pwm, node, "pwm/duty")


def test_subscribes_to_the_given_topic_on_construction(node, pwm, pwm_out):
    assert "pwm/duty" in node.subscriptions


def test_a_valid_message_updates_the_duty_cycle(node, pwm, pwm_out):
    node.deliver("pwm/duty", {"duty_u16": 4000})
    assert pwm.duty == 4000


def test_set_duty_u16_can_be_called_directly(pwm, pwm_out):
    pwm_out.set_duty_u16(1000)
    assert pwm.duty == 1000


def test_duty_is_clamped_to_16_bits(pwm, pwm_out):
    pwm_out.set_duty_u16(70000)
    assert pwm.duty == 65535

    pwm_out.set_duty_u16(-10)
    assert pwm.duty == 0


@pytest.mark.parametrize("bad_msg", [None, [], "4000", {}, {"duty_u16": "4000"}, {"duty_u16": True}])
def test_malformed_messages_are_ignored_without_crashing(node, pwm, pwm_out, bad_msg):
    node.deliver("pwm/duty", bad_msg)
    assert pwm.duty is None
