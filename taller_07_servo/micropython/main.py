"""Control de servo por PWM - punto de entrada del Pico.

Copie este archivo como main.py en la raíz del Pico: arranca solo al energizar
y no necesita el PC ni Thonny.

    Flet -> servo/angle ─┐
                         ├─► Servo.set_angle() ─► PWMOut ─► pin PWM ─► servo
    Flet -> pwm/duty  ───┘   (PWMOut también se puede mandar directo)

Requiere en la raíz del Pico los archivos base de PicoROS (task.py,
scheduler.py, node.py, util.py, ring_buffer.py, watchdog_task.py, umqtt/),
igual que en el taller 05.
"""

import machine
import ubinascii
from machine import PWM, Pin

import config
from common import messages
from common.servo import Servo

from mqtt import MQTTTransport
from pwm_out import PWMOut
from safe_scheduler import SafeScheduler
from wifi import WiFiLink

from node import Node


def pin_id(name):
    """'GP15' -> 15."""
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


def main():
    board_id = ubinascii.hexlify(machine.unique_id()).decode()
    client_id = config.NODE_NAME + "_" + board_id

    scheduler = SafeScheduler()
    node = Node(prefix=config.PREFIX, node_name=config.NODE_NAME)

    pwm = PWM(Pin(pin_id(config.SERVO_GPIO)))
    pwm.freq(int(config.SERVO_FREQ_HZ))

    pwm_out = PWMOut(pwm, node, messages.TOPIC_PWM_DUTY)
    servo = Servo(
        pwm_out,
        min_angle=config.SERVO_MIN_ANGLE,
        max_angle=config.SERVO_MAX_ANGLE,
        min_pulse_ms=config.SERVO_MIN_PULSE_MS,
        max_pulse_ms=config.SERVO_MAX_PULSE_MS,
        freq_hz=config.SERVO_FREQ_HZ,
    )

    def on_servo_angle(topic, msg):
        try:
            messages.validate_angle(msg)
        except (ValueError, TypeError):
            return
        servo.set_angle(msg["angle"])

    node.subscribe(messages.TOPIC_SERVO_ANGLE, on_servo_angle)

    wifi = WiFiLink(scheduler, config.WIFI_SSID, read_wifi_password())

    MQTTTransport(
        scheduler,
        node,
        wifi,
        client_id=client_id,
        broker=config.BROKER,
        port=config.PORT,
        prefix=config.PREFIX,
    )

    print("Servo listo. Ángulo:", servo.angle, "| nodo:", client_id)
    scheduler.run()


main()
