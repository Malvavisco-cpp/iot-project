"""Pruebas de la máquina de estados. Los primeros tests son las reglas de la pizarra."""

import pytest

from common.alarm import (
    AlarmController,
    STATE_ARMED,
    STATE_DISARMED,
    STATE_TRIGGERED,
    REASON_DOOR_OPEN,
    REASON_WRONG_PASSWORD,
    ticks_diff,
)
from common.config import DEFAULT_IR_KEYMAP

PASSWORD = "1234"
CODE_OF = {key: code for code, key in DEFAULT_IR_KEYMAP.items()}


class Bench:
    """Controlador + reloj falso + registro de eventos."""

    def __init__(self, **kwargs):
        self.events = []
        self.now = 1000
        self.ctrl = AlarmController(
            PASSWORD,
            DEFAULT_IR_KEYMAP,
            on_event=lambda name, detail: self.events.append((name, detail)),
            **kwargs,
        )

    def type(self, digits: str, gap_ms: int = 200) -> None:
        for digit in digits:
            self.now += gap_ms
            self.ctrl.handle_ir_code(CODE_OF[digit], self.now)

    def door(self, is_open: bool) -> None:
        self.now += 10
        self.ctrl.handle_door(is_open, self.now)

    def names(self) -> list:
        return [name for name, _ in self.events]


@pytest.fixture
def bench() -> Bench:
    return Bench()


# --------------------------------------------------------------------------
# Reglas de la pizarra
# --------------------------------------------------------------------------

def test_rule1_correct_password_arms_then_disarms(bench):
    assert bench.ctrl.state == STATE_DISARMED

    bench.type(PASSWORD)
    assert bench.ctrl.state == STATE_ARMED

    bench.type(PASSWORD)
    assert bench.ctrl.state == STATE_DISARMED
    assert not bench.ctrl.siren


def test_rule2_wrong_password_triggers_siren_when_disarmed(bench):
    bench.type("9999")

    assert bench.ctrl.state == STATE_TRIGGERED
    assert bench.ctrl.siren
    assert bench.ctrl.reason == REASON_WRONG_PASSWORD


def test_rule2_wrong_password_triggers_siren_when_armed(bench):
    bench.type(PASSWORD)
    bench.type("4321")

    assert bench.ctrl.siren
    assert bench.ctrl.reason == REASON_WRONG_PASSWORD


def test_rule3_door_open_while_armed_triggers_siren(bench):
    bench.type(PASSWORD)
    assert not bench.ctrl.siren

    bench.door(True)

    assert bench.ctrl.state == STATE_TRIGGERED
    assert bench.ctrl.siren
    assert bench.ctrl.reason == REASON_DOOR_OPEN


def test_rule4_door_open_while_disarmed_does_not_trigger(bench):
    bench.door(True)
    bench.door(False)
    bench.door(True)

    assert bench.ctrl.state == STATE_DISARMED
    assert not bench.ctrl.siren
    assert "triggered" not in bench.names()


# --------------------------------------------------------------------------
# La clave silencia la sirena
# --------------------------------------------------------------------------

def test_correct_password_silences_siren_and_disarms(bench):
    bench.type(PASSWORD)
    bench.door(True)
    assert bench.ctrl.siren

    bench.type(PASSWORD)

    assert bench.ctrl.state == STATE_DISARMED
    assert not bench.ctrl.siren
    assert ("disarmed", {"silenced": True}) in bench.events


def test_siren_keeps_ringing_on_more_wrong_passwords(bench):
    bench.type("0000")
    bench.type("1111")

    assert bench.ctrl.siren
    assert bench.ctrl.wrong_attempts == 2
    assert bench.names().count("triggered") == 1


def test_rearming_after_silence_needs_the_password_again(bench):
    bench.type("0000")
    bench.type(PASSWORD)
    assert bench.ctrl.state == STATE_DISARMED

    bench.type(PASSWORD)
    assert bench.ctrl.state == STATE_ARMED


def test_wrong_attempts_reset_after_correct_password(bench):
    bench.type("0000")
    bench.type(PASSWORD)
    assert bench.ctrl.wrong_attempts == 0


# --------------------------------------------------------------------------
# Puerta: condición por nivel y anti-ruido
# --------------------------------------------------------------------------

def test_arming_with_door_already_open_triggers_immediately(bench):
    bench.door(True)
    bench.type(PASSWORD)

    assert bench.ctrl.state == STATE_TRIGGERED
    assert bench.ctrl.reason == REASON_DOOR_OPEN
    assert bench.names()[-2:] == ["armed", "triggered"]


def test_repeated_door_reading_does_not_repeat_events(bench):
    bench.door(True)
    bench.door(True)

    assert bench.names().count("door") == 1


def test_door_open_while_triggered_keeps_first_reason(bench):
    bench.type("0000")
    bench.door(True)

    assert bench.ctrl.reason == REASON_WRONG_PASSWORD


# --------------------------------------------------------------------------
# Teclado
# --------------------------------------------------------------------------

def test_unknown_ir_codes_are_ignored_not_wrong_passwords(bench):
    for code in (0, 1, 0xDEADBEEF, 0xFFA25D):
        bench.ctrl.handle_ir_code(code, bench.now)

    assert bench.events == []
    assert bench.ctrl.state == STATE_DISARMED


def test_partial_password_is_discarded_after_timeout(bench):
    bench.type("12")
    assert bench.ctrl.keys_entered == 2

    bench.now += 5000
    bench.ctrl.tick(bench.now)

    assert bench.ctrl.keys_entered == 0
    assert ("keys_cleared", {"reason": "timeout"}) in bench.events
    assert bench.ctrl.state == STATE_DISARMED


def test_stale_digits_do_not_poison_next_attempt(bench):
    bench.type("12")
    bench.now += 6000  # el usuario se fue; nadie llamó a tick()
    bench.type(PASSWORD)

    assert bench.ctrl.state == STATE_ARMED


def test_clear_key_discards_typed_digits(bench):
    bench.type("12")
    bench.type("C")
    bench.type(PASSWORD)

    assert bench.ctrl.state == STATE_ARMED
    assert ("keys_cleared", {"reason": "clear_key"}) in bench.events


def test_clear_key_with_nothing_typed_is_silent(bench):
    bench.type("C")
    assert bench.events == []


def test_digits_never_leave_the_controller_in_events(bench):
    bench.type(PASSWORD)
    for _, detail in bench.events:
        assert "1234" not in str(detail)
        assert set(detail) <= {"count", "open", "reason", "attempts", "silenced"}


# --------------------------------------------------------------------------
# Construcción y utilidades
# --------------------------------------------------------------------------

@pytest.mark.parametrize("bad", ["", "123", "12345", "abcd", "12 4"])
def test_password_must_be_exactly_four_digits(bad):
    with pytest.raises(ValueError):
        AlarmController(bad, DEFAULT_IR_KEYMAP)


def test_snapshot_reports_state_without_leaking_digits(bench):
    bench.type("12")
    snap = bench.ctrl.snapshot()

    assert snap == {
        "state": STATE_DISARMED,
        "door_open": False,
        "keys_entered": 2,
        "wrong_attempts": 0,
        "reason": None,
    }


def test_ticks_diff_handles_counter_wraparound():
    period = 1 << 30
    assert ticks_diff(10, 5) == 5
    assert ticks_diff(5, 10) == -5
    assert ticks_diff(3, period - 2) == 5  # el contador dio la vuelta


def test_key_timeout_survives_counter_wraparound():
    bench = Bench()
    bench.now = (1 << 30) - 100
    bench.type("1", gap_ms=0)

    bench.now = 4900 - 100  # 4.9 s después, ya del otro lado de la vuelta
    bench.ctrl.tick(bench.now)
    assert bench.ctrl.keys_entered == 1

    bench.now += 200
    bench.ctrl.tick(bench.now)
    assert bench.ctrl.keys_entered == 0
