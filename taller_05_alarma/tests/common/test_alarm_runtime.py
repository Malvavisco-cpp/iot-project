"""AlarmRuntime con pines, reloj y red falsos: lo que hace sonar (o no) la sirena física."""

import pytest

from common import messages
from common.alarm import AlarmController
from common.alarm_runtime import AlarmRuntime
from common.config import DEFAULT_IR_KEYMAP

PASSWORD = "1234"
CODE_OF = {key: code for code, key in DEFAULT_IR_KEYMAP.items()}


class FakePin:
    def __init__(self, level: int = 0):
        self.level = level

    def value(self, new=None):
        if new is None:
            return self.level
        self.level = new


class Rig:
    """Runtime completo con hardware falso."""

    def __init__(self, siren: bool = True, publish=None, door_level: int = 0, **kwargs):
        self.now = 10_000
        self.door = FakePin(door_level)
        self.led = FakePin()
        self.siren = FakePin() if siren else None
        self.published = []
        self.controller = AlarmController(PASSWORD, DEFAULT_IR_KEYMAP)
        self.runtime = AlarmRuntime(
            self.controller,
            door_pin=self.door,
            led_pin=self.led,
            siren_pin=self.siren,
            publish=publish or (lambda topic, msg: self.published.append((topic, msg))),
            clock=lambda: self.now,
            **kwargs,
        )

    def advance(self, ms: int, step: int = 20) -> None:
        """Avanza el tiempo haciendo poll() cada `step` ms, como el Scheduler."""
        end = self.now + ms
        while self.now < end:
            self.now += step
            self.runtime.poll()

    def press(self, digits: str) -> None:
        for digit in digits:
            self.now += 200
            self.runtime.on_ir_code(CODE_OF[digit])

    def set_door(self, level: int) -> None:
        self.door.level = level

    def last_state(self) -> dict:
        return [m for t, m in self.published if t == messages.TOPIC_STATE][-1]

    def events(self) -> list:
        return [m["event"] for t, m in self.published if t == messages.TOPIC_EVENT]


@pytest.fixture
def rig() -> Rig:
    return Rig()


# --------------------------------------------------------------------------
# Salidas físicas
# --------------------------------------------------------------------------

def test_everything_is_off_at_boot(rig):
    assert rig.led.level == 0
    assert rig.siren.level == 0


def test_led_is_steady_on_when_armed_and_siren_is_off(rig):
    rig.press(PASSWORD)
    rig.advance(1000)

    assert rig.controller.state == "armed"
    assert rig.led.level == 1
    assert rig.siren.level == 0


def test_door_opening_while_armed_turns_the_siren_on(rig):
    rig.press(PASSWORD)
    rig.set_door(1)
    rig.advance(100)

    assert rig.siren.level == 1


def test_door_opening_while_disarmed_keeps_the_siren_off(rig):
    rig.set_door(1)
    rig.advance(500)

    assert rig.controller.state == "disarmed"
    assert rig.siren.level == 0
    assert rig.led.level == 0


def test_wrong_password_turns_siren_on_immediately_without_waiting_for_poll(rig):
    rig.press("9999")

    assert rig.siren.level == 1


def test_correct_password_turns_siren_and_led_off(rig):
    rig.press("9999")
    rig.press(PASSWORD)
    rig.advance(1000)

    assert rig.siren.level == 0
    assert rig.led.level == 0


def test_led_blinks_while_triggered(rig):
    rig.press("9999")
    levels = set()
    for _ in range(50):
        rig.advance(20)
        levels.add(rig.led.level)

    assert levels == {0, 1}


def test_without_siren_pin_the_led_blinks_as_the_siren():
    rig = Rig(siren=False)
    rig.press("9999")
    levels = set()
    for _ in range(50):
        rig.advance(20)
        levels.add(rig.led.level)

    assert rig.siren is None
    assert levels == {0, 1}


# --------------------------------------------------------------------------
# Puerta
# --------------------------------------------------------------------------

def test_door_bounce_shorter_than_debounce_is_ignored(rig):
    rig.press(PASSWORD)
    rig.set_door(1)
    rig.advance(20)  # 20 ms < 50 ms de debounce
    rig.set_door(0)
    rig.advance(200)

    assert rig.controller.state == "armed"
    assert rig.siren.level == 0


def test_door_change_is_accepted_after_the_debounce_time(rig):
    rig.press(PASSWORD)
    rig.set_door(1)
    rig.advance(100)

    assert rig.controller.door_open is True


def test_door_reading_at_boot_is_taken_without_debounce():
    rig = Rig(door_level=1)
    assert rig.controller.door_open is True


def test_normally_closed_switch_with_inverted_level():
    rig = Rig(door_level=0, door_open_level=0)
    assert rig.controller.door_open is True

    rig.set_door(1)  # el contacto cierra: puerta cerrada
    rig.advance(100)
    assert rig.controller.door_open is False


# --------------------------------------------------------------------------
# Publicación
# --------------------------------------------------------------------------

def test_state_is_published_at_boot_and_then_periodically(rig):
    rig.advance(20)
    states = [m for t, m in rig.published if t == messages.TOPIC_STATE]
    assert len(states) == 1

    rig.advance(5100)
    states = [m for t, m in rig.published if t == messages.TOPIC_STATE]
    assert len(states) == 2


def test_state_is_published_promptly_on_change(rig):
    rig.advance(20)
    rig.press(PASSWORD)
    rig.advance(20)

    assert rig.last_state()["state"] == "armed"
    assert rig.events()[-1] == "armed"


def test_every_published_state_and_event_passes_validation(rig):
    rig.press(PASSWORD)
    rig.set_door(1)
    rig.advance(200)
    rig.press("00")  # digitación a medias

    for topic, msg in rig.published:
        if topic == messages.TOPIC_STATE:
            messages.validate_state(msg)
        elif topic == messages.TOPIC_EVENT:
            messages.validate_event(msg)


def test_event_sequence_numbers_increase(rig):
    rig.press(PASSWORD)
    rig.press(PASSWORD)
    seqs = [m["seq"] for t, m in rig.published if t == messages.TOPIC_EVENT]

    assert seqs == sorted(seqs)
    assert len(set(seqs)) == len(seqs)


def test_uptime_advances_with_the_clock(rig):
    rig.advance(3000)
    rig.runtime.mark_dirty()
    rig.advance(20)

    assert rig.last_state()["uptime_s"] >= 3


def test_mark_dirty_republishes_state(rig):
    rig.advance(20)
    before = len(rig.published)
    rig.runtime.mark_dirty()
    rig.advance(20)

    assert len(rig.published) > before


def test_no_key_value_is_ever_published(rig):
    rig.press(PASSWORD)
    rig.advance(100)

    assert "1234" not in str(rig.published)


# --------------------------------------------------------------------------
# Autonomía: la alarma no depende de la red
# --------------------------------------------------------------------------

def test_alarm_still_works_when_publishing_raises():
    def broken_network(topic, msg):
        raise OSError("sin red")

    rig = Rig(publish=broken_network)
    rig.press(PASSWORD)
    rig.set_door(1)
    rig.advance(200)

    assert rig.controller.state == "triggered"
    assert rig.siren.level == 1


def test_password_still_arms_and_disarms_when_publishing_raises():
    def broken_network(topic, msg):
        raise OSError("sin red")

    rig = Rig(publish=broken_network)
    rig.press(PASSWORD)
    assert rig.controller.state == "armed"
    rig.press(PASSWORD)
    assert rig.controller.state == "disarmed"
