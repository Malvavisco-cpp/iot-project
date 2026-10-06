"""Carro diferencial - punto de entrada del Pico.

Se guarda como main.py en la raíz del Pico: arranca solo al energizar.

    Flet -> car/cmd {v, w, t} -> Car (cinemática inversa) -> Motor izq / der -> puente H
    Flet -> car/stop          -> Car.stop()
    Car  -> car/state         -> Flet (moviéndose / detenido)
"""

import time

import machine
import ubinascii
from machine import PWM, Pin

import config
from common import messages
from common.car import Car
from common.motor import MiniMotor, Motor

from car_task import CarTask
from mqtt import MQTTTransport
from node import Node
from safe_scheduler import SafeScheduler
from wifi import WiFiLink


def read_wifi_password():
    try:
        with open(config.WIFI_PASSWORD_FILE) as f:
            return f.read().strip()
    except OSError:
        print("Sin", config.WIFI_PASSWORD_FILE, "-> se opera sin red")
        return None


def make_pwm(gpio):
    pwm = PWM(Pin(gpio))
    pwm.freq(config.MOTOR_PWM_FREQ_HZ)
    pwm.duty_u16(0)
    return pwm


def make_motor(pwm_gpio, in1_gpio, in2_gpio, inverted):
    if config.MOTOR_DRIVER == "mini":
        return MiniMotor(make_pwm(in1_gpio), make_pwm(in2_gpio), config.MAX_WHEEL_SPEED_M_S, inverted)
    return Motor(
        make_pwm(pwm_gpio),
        Pin(in1_gpio, Pin.OUT, value=0),
        Pin(in2_gpio, Pin.OUT, value=0),
        config.MAX_WHEEL_SPEED_M_S,
        inverted,
    )


def main():
    board_id = ubinascii.hexlify(machine.unique_id()).decode()
    client_id = config.NODE_NAME + "_" + board_id

    if config.STBY_GPIO is not None:
        Pin(config.STBY_GPIO, Pin.OUT, value=1)

    left = make_motor(config.LEFT_PWM_GPIO, config.LEFT_IN1_GPIO, config.LEFT_IN2_GPIO, config.LEFT_INVERTED)
    right = make_motor(config.RIGHT_PWM_GPIO, config.RIGHT_IN1_GPIO, config.RIGHT_IN2_GPIO, config.RIGHT_INVERTED)

    scheduler = SafeScheduler()
    node = Node(prefix=config.PREFIX, node_name=config.NODE_NAME)

    # Car se suscribe a car/cmd y car/stop aquí; Node le pasa esas suscripciones
    # al MQTTTransport cuando este se registra (add_transport).
    car = Car(
        node,
        left,
        right,
        half_track_m=config.WHEEL_HALF_TRACK_M,
        max_wheel_speed=config.MAX_WHEEL_SPEED_M_S,
        clock=time.ticks_ms,
        max_duration_s=config.MAX_COMMAND_S,
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
        retain_topics=(messages.TOPIC_STATE,),
        on_connect=car.publish_state,
    )

    CarTask(scheduler, car, period_ms=config.CAR_PERIOD_MS)

    print("Carro listo | nodo:", client_id)
    scheduler.run()


main()
