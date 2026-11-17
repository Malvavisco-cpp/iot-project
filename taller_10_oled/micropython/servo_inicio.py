"""Arranque de servos: la misma pasada que hace pruebas_hardware/prueba_servos.py.

Centra hombro y codo, hace un barrido corto de cada uno y los suelta.
main.py la llama una vez al encender, antes de abrir la pantalla.
"""

import time

from machine import PWM, Pin

import config


def _a_ms(grados):
    grados = max(-90, min(90, grados))
    return config.SERVO_MIN_MS + (grados + 90) / 180 * (config.SERVO_MAX_MS - config.SERVO_MIN_MS)


def _duty(ms):
    return int(ms / (1000 / config.SERVO_FREQ_HZ) * 65535)


class _Servo:
    def __init__(self, gpio):
        self.pwm = PWM(Pin(gpio))
        self.pwm.freq(config.SERVO_FREQ_HZ)
        self.grados = 0

    def ir(self, grados, paso=2, pausa_ms=20):
        sentido = 1 if grados >= self.grados else -1
        a = self.grados
        while (grados - a) * sentido > 0:
            a += sentido * min(paso, abs(grados - a))
            self.pwm.duty_u16(_duty(_a_ms(a)))
            time.sleep_ms(pausa_ms)
        self.pwm.duty_u16(_duty(_a_ms(grados)))
        self.grados = grados

    def liberar(self):
        self.pwm.duty_u16(0)


def rutina():
    servos = {n: _Servo(g) for n, g in config.SERVOS.items()}
    for s in servos.values():
        s.ir(0)
    time.sleep(1)
    for n, s in servos.items():
        print("servo", n)
        s.ir(config.SERVO_BARRIDO_DEG)
        s.ir(-config.SERVO_BARRIDO_DEG)
        s.ir(0)
    for s in servos.values():
        s.liberar()
    print("servos listos")
