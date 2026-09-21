"""AlarmView contra la API real de Flet (sin abrir ventana): atrapa nombres de controles rotos."""

import json

import pytest

ft = pytest.importorskip("flet")

from common import messages  # noqa: E402
from common.config import PASSWORD_LENGTH, PREFIX  # noqa: E402
from flet_ui.main import LINK_TEXT, STATE_LOOK, TRIGGERED_ALT_COLOR, AlarmView  # noqa: E402
from flet_ui.monitor import LINK_OFFLINE, LINK_ONLINE, LINK_WAITING, AlarmMonitor  # noqa: E402


class FakePage:
    def __init__(self):
        self.added = []
        self.updates = 0

    def add(self, *controls):
        self.added.extend(controls)

    def update(self):
        self.updates += 1


@pytest.fixture
def parts():
    page = FakePage()
    monitor = AlarmMonitor(PREFIX)
    view = AlarmView(page, monitor)
    return page, monitor, view


def push(view: AlarmView, topic: str, msg: dict) -> None:
    view.on_message(PREFIX + topic, json.dumps(msg).encode())


def test_screen_builds_with_the_real_flet_api(parts):
    page, _, _ = parts

    assert len(page.added) == 5
    assert page.updates >= 1


def test_starts_showing_no_data(parts):
    _, _, view = parts

    assert view.status_headline.value == "SIN DATOS"
    assert view.door_value.value == "-"
    assert view.pico_pill.content.value == LINK_TEXT[LINK_WAITING][0]


def test_armed_state_is_shown(parts):
    _, _, view = parts
    push(view, "alarm/state", messages.build_state("armed", False, 0, 0, None, 60))

    assert view.status_headline.value == "ALARMA ACTIVADA"
    assert view.status_card.bgcolor == STATE_LOOK["armed"][0]
    assert view.door_value.value == "CERRADA"
    assert view.pico_pill.content.value == LINK_TEXT[LINK_ONLINE][0]
    assert view.banner.visible is False


def test_intrusion_shows_the_alarm_and_the_open_door(parts):
    _, _, view = parts
    push(view, "alarm/state", messages.build_state("triggered", True, 0, 0, "door_open", 60))

    assert view.status_headline.value == "¡ALARMA DISPARADA!"
    assert "puerta" in view.status_detail.value.lower()
    assert view.door_value.value == "ABIERTA"


def test_triggered_card_blinks_between_two_reds(parts):
    _, _, view = parts
    push(view, "alarm/state", messages.build_state("triggered", True, 0, 0, "door_open", 60))

    colors = set()
    for blink in (False, True, False, True):
        view._blink = blink
        view.render()
        colors.add(view.status_card.bgcolor)

    assert colors == {STATE_LOOK["triggered"][0], TRIGGERED_ALT_COLOR}


def test_a_steady_state_does_not_blink(parts):
    _, _, view = parts
    push(view, "alarm/state", messages.build_state("armed", False, 0, 0, None, 60))

    colors = set()
    for blink in (False, True):
        view._blink = blink
        view.render()
        colors.add(view.status_card.bgcolor)

    assert len(colors) == 1


def test_typed_digits_fill_the_dots_without_showing_values(parts):
    _, _, view = parts
    push(view, "alarm/state", messages.build_state("disarmed", False, 2, 0, None, 5))

    filled = [dot.icon == ft.Icons.CIRCLE for dot in view.key_dots]
    assert len(view.key_dots) == PASSWORD_LENGTH
    assert filled == [True, True, False, False]


def test_wrong_attempts_counter(parts):
    _, _, view = parts
    push(view, "alarm/state", messages.build_state("triggered", False, 0, 3, "wrong_password", 5))

    assert view.attempts_value.value == "3"


def test_events_appear_in_the_log(parts):
    _, _, view = parts
    push(view, "alarm/event", messages.build_event(1, "armed", {}, 5))
    push(view, "alarm/event", messages.build_event(2, "door", {"open": True}, 6))

    texts = [c.value for c in view.log_list.controls]
    assert len(texts) == 2
    assert "ABIERTA" in texts[0]      # el más reciente arriba
    assert "ACTIVADA" in texts[1]


def test_log_is_not_rebuilt_on_every_blink_redraw(parts):
    _, _, view = parts
    push(view, "alarm/event", messages.build_event(1, "armed", {}, 5))
    controls_before = view.log_list.controls

    view.render()
    view.render()

    assert view.log_list.controls is controls_before


def test_losing_the_pico_dims_the_card_and_warns(parts):
    _, _, view = parts
    push(view, "alarm/state", messages.build_state("armed", False, 0, 0, None, 5))
    push(view, "node/online", messages.build_online(False, "pico"))

    assert view.banner.visible is True
    assert view.status_card.opacity < 1.0
    assert view.pico_pill.content.value == LINK_TEXT[LINK_OFFLINE][0]
    assert "sigue funcionando" in view.banner.content.value


def test_broker_connection_state_is_shown(parts):
    _, _, view = parts
    view.on_link(True, "broker.test")
    assert view.broker_pill.content.value == "Broker: conectado"

    view.on_link(False, "Connection refused")
    assert "Connection refused" in view.broker_pill.content.value


def test_system_card_shows_watchdog_telemetry(parts):
    _, _, view = parts
    push(view, "alarm/state", messages.build_state("armed", False, 0, 0, None, 120))
    push(view, "watchdog/stats", {"mem_free_bytes": 204800, "rssi": -61, "temperature_c": "25.10"})

    text = view.system_value.value
    assert "200 KB" in text
    assert "-61 dBm" in text
    assert "25.1" in text


def test_garbage_messages_do_not_break_the_screen(parts):
    _, _, view = parts
    view.on_message(PREFIX + "alarm/state", b"basura")
    view.on_message(PREFIX + "alarm/event", b"\xff")

    assert view.status_headline.value == "SIN DATOS"
