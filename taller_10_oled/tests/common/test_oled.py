import pytest

from common import messages
from common.oled import OLED


class FakeDisplay:
    def __init__(self):
        self.calls = []

    def fill(self, color):
        self.calls.append(("fill", color))

    def text(self, string, x, y, color=1):
        self.calls.append(("text", string, x, y, color))

    def show(self):
        self.calls.append(("show",))


class FakeNode:
    """Como Node de PicoROS: llama callback(topic=..., msg=...)."""

    def __init__(self):
        self.subscriptions = {}

    def subscribe(self, topic, callback):
        self.subscriptions[topic] = callback

    def deliver(self, topic, msg):
        self.subscriptions[topic](topic=topic, msg=msg)


@pytest.fixture
def rig():
    node, display = FakeNode(), FakeDisplay()
    return node, display, OLED(node, display)


def test_subscribes_to_oled_text(rig):
    node, _, _ = rig
    assert messages.TOPIC_TEXT in node.subscriptions


def test_a_message_draws_the_text_and_refreshes(rig):
    node, display, _ = rig
    node.deliver(messages.TOPIC_TEXT, {"text": "hola", "x": 8, "y": 16, "color": 1})

    assert display.calls == [("text", "hola", 8, 16, 1), ("show",)]


def test_defaults_write_at_the_origin_without_clearing(rig):
    node, display, _ = rig
    node.deliver(messages.TOPIC_TEXT, {"text": "hola"})

    assert display.calls == [("text", "hola", 0, 0, 1), ("show",)]


def test_clear_blanks_the_screen_before_writing(rig):
    node, display, _ = rig
    node.deliver(messages.TOPIC_TEXT, {"text": "hola", "clear": True})

    assert display.calls == [("fill", 0), ("text", "hola", 0, 0, 1), ("show",)]


def test_empty_text_with_clear_only_blanks_the_screen(rig):
    node, display, _ = rig
    node.deliver(messages.TOPIC_TEXT, {"text": "", "clear": True})

    assert display.calls == [("fill", 0), ("show",)]


@pytest.mark.parametrize("bad", [None, [], {}, {"text": 5}, {"text": "a", "x": 500}, {"text": ""}])
def test_malformed_messages_leave_the_screen_untouched(rig, bad):
    node, display, _ = rig
    node.deliver(messages.TOPIC_TEXT, bad)

    assert display.calls == []


def test_a_display_failure_does_not_escape_the_callback(rig):
    node, display, _ = rig

    def broken():
        raise OSError("I2C no responde")

    display.show = broken
    node.deliver(messages.TOPIC_TEXT, {"text": "hola"})  # Node quitaría el callback si lanzara
