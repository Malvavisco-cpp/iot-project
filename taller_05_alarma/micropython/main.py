"""Alarma de control de acceso - punto de entrada del Pico.

Copie este archivo como main.py en la raíz del Pico: arranca solo al energizar y
no necesita el PC ni Thonny.

    Botón (puerta) -> AlarmRuntime -> LED / sirena     (todo local, en el Pico)
    Receptor IR    -> KeypadIR ----^
                                   |
                       Node -> MQTTTransport -> broker -> Flet   (solo informa)

Si no hay WiFi o broker, la alarma sigue funcionando; lo único que se pierde es
el monitoreo, que vuelve solo al recuperarse la red.
"""

import time

import machine
import ubinascii
from machine import Pin

import config
from common import messages
from common.alarm import AlarmController
from common.alarm_runtime import AlarmRuntime

from alarm_task import AlarmTask
from ir_keypad import KeypadIR
from mqtt import MQTTTransport
from safe_scheduler import SafeScheduler
from wifi import WiFiLink

from node import Node
from watchdog_task import WatchdogTask


def pin_id(name):
    """'GP16' -> 16; 'LED' (LED integrado de la Pico W) se deja como texto."""
    if isinstance(name, str) and name.startswith("GP"):
        return int(name[2:])
    return name


def read_wifi_password():
    try:
        with open(config.WIFI_PASSWORD_FILE) as f:
            return f.read().strip()
    except OSError:
        print("Sin", config.WIFI_PASSWORD_FILE, "-> se opera sin red")
        return None


def make_door_pin():
    pulls = {"down": Pin.PULL_DOWN, "up": Pin.PULL_UP}
    pull = pulls.get(config.DOOR_PULL)
    if pull is None:
        return Pin(pin_id(config.DOOR_GPIO), Pin.IN)
    return Pin(pin_id(config.DOOR_GPIO), Pin.IN, pull)


class DoorPin:
    """La puerta la manda el sensor físico si hay uno cableado; si no (como en
    este grupo, donde lo único conectado es el receptor IR), la maneja el botón
    Abrir/Cerrar de Flet vía MQTT (`sim/door_set`). Lo último que cambie manda.
    """

    def __init__(self, hardware_pin):
        self._hardware_pin = hardware_pin
        self._override = None

    def value(self, new=None):
        if new is not None:
            self._override = new
            return None
        if self._override is not None:
            return self._override
        return self._hardware_pin.value()


def main():
    board_id = ubinascii.hexlify(machine.unique_id()).decode()
    # El id de cliente MQTT debe ser único: si dos placas usan el mismo, el broker
    # público las expulsa una a la otra en un ciclo sin fin.
    client_id = config.NODE_NAME + "_" + board_id

    scheduler = SafeScheduler()
    node = Node(prefix=config.PREFIX, node_name=config.NODE_NAME)

    controller = AlarmController(
        config.ALARM_PASSWORD,
        config.IR_KEYMAP,
        password_length=config.PASSWORD_LENGTH,
        key_timeout_ms=config.KEY_TIMEOUT_MS,
    )

    siren_pin = None
    if config.SIREN_GPIO is not None:
        siren_pin = Pin(pin_id(config.SIREN_GPIO), Pin.OUT)
    led_pin = Pin(pin_id(config.LED_GPIO), Pin.OUT)

    door_pin = DoorPin(make_door_pin())
    runtime = AlarmRuntime(
        controller,
        door_pin=door_pin,
        led_pin=led_pin,
        siren_pin=siren_pin,
        publish=node.publish,
        clock=time.ticks_ms,
        door_open_level=config.DOOR_OPEN_LEVEL,
        debounce_ms=config.DOOR_DEBOUNCE_MS,
        state_period_ms=config.STATE_PERIOD_MS,
    )

    wifi = WiFiLink(scheduler, config.WIFI_SSID, read_wifi_password())

    MQTTTransport(
        scheduler,
        node,
        wifi,
        client_id=client_id,
        broker=config.BROKER,
        port=config.PORT,
        prefix=config.PREFIX,
        retain_topics=messages.RETAINED_TOPICS,
        should_defer=lambda: controller.keys_entered > 0,
        on_connect=runtime.mark_dirty,
    )

    def on_door_sim(topic, msg):
        try:
            messages.validate_door_set(msg)
        except (ValueError, TypeError):
            return
        door_pin.value(1 if msg["door_open"] else 0)

    node.subscribe(messages.TOPIC_DOOR_SIM, on_door_sim)

    AlarmTask(scheduler, runtime, period_ms=config.ALARM_PERIOD_MS)

    KeypadIR(
        scheduler,
        pin_ir=config.IR_GPIO,
        on_code=runtime.on_ir_code,
        min_bits=config.IR_MIN_BITS,
        pubsub=node,
        raw_topic="IRIn/value" if config.PUBLISH_RAW_IR else None,
    )

    WatchdogTask(scheduler, node, wifi, period_ms=config.WATCHDOG_PERIOD_MS)

    print("Alarma lista. Estado:", controller.state, "| nodo:", client_id)
    scheduler.run()


main()
