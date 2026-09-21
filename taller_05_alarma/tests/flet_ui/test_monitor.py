"""AlarmMonitor: el modelo de la interfaz, sin Flet ni broker."""

import json

import pytest

from common import messages
from flet_ui import monitor as mon
from flet_ui.monitor import AlarmMonitor

PREFIX = "UDFJC/iot_ws/robot0/"


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def monitor(clock) -> AlarmMonitor:
    return AlarmMonitor(PREFIX, clock=clock, wall_clock=lambda: 1_700_000_000.0, offline_after_s=15.0)


def send(monitor: AlarmMonitor, topic: str, payload) -> bool:
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    return monitor.handle_message(PREFIX + topic, body)


def state_msg(state="armed", door_open=False, keys=0, wrong=0, reason=None, uptime=10) -> dict:
    return messages.build_state(state, door_open, keys, wrong, reason, uptime)


# --------------------------------------------------------------------------
# alarm/state
# --------------------------------------------------------------------------

def test_starts_without_data(monitor):
    assert monitor.status.state == mon.STATE_UNKNOWN
    assert monitor.link() == mon.LINK_WAITING
    assert mon.headline_for(monitor.status) == "SIN DATOS"


def test_state_message_updates_the_status(monitor):
    changed = send(monitor, "alarm/state", state_msg("triggered", True, 0, 2, "door_open", 99))

    assert changed
    assert monitor.status.state == "triggered"
    assert monitor.status.door_open is True
    assert monitor.status.siren is True
    assert monitor.status.wrong_attempts == 2
    assert monitor.status.reason == "door_open"
    assert monitor.status.uptime_s == 99


@pytest.mark.parametrize(
    "state, headline",
    [
        ("disarmed", "ALARMA DESACTIVADA"),
        ("armed", "ALARMA ACTIVADA"),
        ("triggered", "¡ALARMA DISPARADA!"),
    ],
)
def test_headline_for_each_state(monitor, state, headline):
    send(monitor, "alarm/state", state_msg(state))
    assert mon.headline_for(monitor.status) == headline


def test_detail_explains_why_the_alarm_fired(monitor):
    send(monitor, "alarm/state", state_msg("triggered", True, reason="door_open"))
    assert "puerta" in mon.detail_for(monitor.status).lower()

    send(monitor, "alarm/state", state_msg("triggered", False, reason="wrong_password"))
    assert "clave" in mon.detail_for(monitor.status).lower()


def test_topics_to_subscribe_carry_the_prefix(monitor):
    assert monitor.topics == [
        PREFIX + "alarm/state",
        PREFIX + "alarm/event",
        PREFIX + "node/online",
        PREFIX + "watchdog/stats",
    ]


# --------------------------------------------------------------------------
# Datos malos (el broker es público)
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "payload",
    [
        b"esto no es json",
        b"\xff\xfe",
        b"[1, 2, 3]",
        b'{"state": "exploded"}',
        b"null",
    ],
)
def test_malformed_state_is_rejected_without_crashing(monitor, payload):
    assert send(monitor, "alarm/state", payload) is False
    assert monitor.status.state == mon.STATE_UNKNOWN
    assert monitor.rejected == 1


def test_messages_from_another_prefix_are_ignored(monitor):
    changed = monitor.handle_message("OTRO/grupo/alarm/state", json.dumps(state_msg()).encode())

    assert changed is False
    assert monitor.status.state == mon.STATE_UNKNOWN
    assert monitor.rejected == 0


def test_a_bad_message_does_not_erase_the_last_good_state(monitor):
    send(monitor, "alarm/state", state_msg("armed"))
    send(monitor, "alarm/state", b"basura")

    assert monitor.status.state == "armed"


# --------------------------------------------------------------------------
# alarm/event -> bitácora
# --------------------------------------------------------------------------

def test_events_are_logged_newest_first_with_a_level(monitor):
    send(monitor, "alarm/event", messages.build_event(1, "armed", {}, 5))
    send(monitor, "alarm/event", messages.build_event(2, "triggered", {"reason": "door_open"}, 9))

    assert [e.name for e in monitor.log] == ["triggered", "armed"]
    assert monitor.log[0].level == mon.LEVEL_DANGER
    assert monitor.log[1].level == mon.LEVEL_SUCCESS
    assert "puerta" in monitor.log[0].text.lower()


def test_key_events_are_not_logged_so_digits_never_appear(monitor):
    changed = send(monitor, "alarm/event", messages.build_event(1, "key", {"count": 2}, 5))

    assert changed is False
    assert len(monitor.log) == 0


@pytest.mark.parametrize(
    "name, detail, expected, level",
    [
        ("door", {"open": True}, "ABIERTA", mon.LEVEL_INFO),
        ("door", {"open": False}, "CERRADA", mon.LEVEL_INFO),
        ("wrong_password", {"attempts": 3}, "intento 3", mon.LEVEL_WARNING),
        ("disarmed", {"silenced": True}, "silenciada", mon.LEVEL_SUCCESS),
        ("disarmed", {"silenced": False}, "DESACTIVADA", mon.LEVEL_SUCCESS),
        ("keys_cleared", {"reason": "timeout"}, "tiempo agotado", mon.LEVEL_INFO),
        ("keys_cleared", {"reason": "clear_key"}, "borrar", mon.LEVEL_INFO),
        ("triggered", {"reason": "wrong_password"}, "clave", mon.LEVEL_DANGER),
    ],
)
def test_event_descriptions(name, detail, expected, level):
    text, got_level = mon.describe_event(name, detail)
    assert expected.lower() in text.lower()
    assert got_level == level


def test_unknown_event_names_are_shown_instead_of_dropped():
    text, level = mon.describe_event("algo_nuevo", {})
    assert "algo_nuevo" in text


def test_log_is_bounded(clock):
    monitor = AlarmMonitor(PREFIX, clock=clock, max_log=5)
    for seq in range(20):
        send(monitor, "alarm/event", messages.build_event(seq, "armed", {}, 0))

    assert len(monitor.log) == 5
    assert monitor.log[0].seq == 19


def test_log_version_changes_only_when_something_is_logged(monitor):
    v0 = monitor.log_version
    send(monitor, "alarm/event", messages.build_event(1, "key", {"count": 1}, 0))
    assert monitor.log_version == v0
    send(monitor, "alarm/event", messages.build_event(2, "armed", {}, 0))
    assert monitor.log_version == v0 + 1


def test_invalid_event_is_rejected(monitor):
    assert send(monitor, "alarm/event", {"event": "armed"}) is False
    assert monitor.rejected == 1


# --------------------------------------------------------------------------
# Enlace con el Pico (Last Will + tiempo sin reportar)
# --------------------------------------------------------------------------

def test_link_is_online_while_the_pico_keeps_reporting(monitor, clock):
    send(monitor, "alarm/state", state_msg())
    clock.now += 14
    assert monitor.link() == mon.LINK_ONLINE


def test_link_becomes_silent_when_the_pico_stops_reporting(monitor, clock):
    send(monitor, "alarm/state", state_msg())
    clock.now += 16
    assert monitor.link() == mon.LINK_SILENT


def test_a_new_state_message_brings_the_link_back(monitor, clock):
    send(monitor, "alarm/state", state_msg())
    clock.now += 60
    assert monitor.link() == mon.LINK_SILENT

    send(monitor, "alarm/state", state_msg())
    assert monitor.link() == mon.LINK_ONLINE


def test_last_will_marks_the_pico_offline_immediately(monitor):
    send(monitor, "alarm/state", state_msg())
    send(monitor, "node/online", messages.build_online(False, "pico"))

    assert monitor.link() == mon.LINK_OFFLINE


def test_pico_coming_back_online_clears_offline(monitor):
    send(monitor, "node/online", messages.build_online(False, "pico"))
    send(monitor, "node/online", messages.build_online(True, "pico"))
    send(monitor, "alarm/state", state_msg())

    assert monitor.link() == mon.LINK_ONLINE


def test_invalid_online_payload_is_rejected(monitor):
    assert send(monitor, "node/online", {"online": "yes"}) is False
    assert monitor.rejected == 1


# --------------------------------------------------------------------------
# watchdog/stats (telemetría de PicoROS)
# --------------------------------------------------------------------------

def test_watchdog_stats_are_parsed_including_text_temperature(monitor):
    changed = send(
        monitor,
        "watchdog/stats",
        {"mem_free_bytes": 180000, "rssi": -60, "temperature_c": "24.31", "AlarmTask": {"avg": 12}},
    )

    assert changed
    assert monitor.system.mem_free_bytes == 180000
    assert monitor.system.rssi == -60
    assert monitor.system.temperature_c == pytest.approx(24.31)


def test_watchdog_with_missing_or_garbage_fields_does_not_crash(monitor):
    send(monitor, "watchdog/stats", {"mem_free_bytes": "mucho", "temperature_c": "n/a"})

    assert monitor.system.mem_free_bytes is None
    assert monitor.system.temperature_c is None
