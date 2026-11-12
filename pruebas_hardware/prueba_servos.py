"""Servos del brazo (hombro y codo). Mueve despacio para no dar tirones.

ANTES: los servos van a una fuente de 5 V aparte, con la tierra unida a la del Pico.
F5 hace una pasada corta. Luego en la Shell:
    ir("hombro", 20)           lleva ese servo a 20 grados (0 = centro, de -90 a 90)
    ir("codo", -15)
    centrar()                  los dos al centro
    barrer("hombro", 30)       va y viene +-30 grados
    pulso("codo", 1.7)         manda un pulso de 1.7 ms directo (para calibrar)
    liberar()                  suelta los servos (sin pulso, no tiemblan)
    manual()                   pregunta ángulos por teclado ("q" para salir)
"""

import time

from machine import PWM, Pin

import pines

_pwm = {}
_angulo = {}


def _canal(nombre):
    if nombre not in pines.SERVOS:
        raise ValueError("servo desconocido: %s (hay: %s)" % (nombre, list(pines.SERVOS)))
    if nombre not in _pwm:
        p = PWM(Pin(pines.SERVOS[nombre]))
        p.freq(pines.SERVO_FREQ_HZ)
        _pwm[nombre] = p
        _angulo[nombre] = 0
    return _pwm[nombre]


def _duty(ms):
    return int(ms / (1000 / pines.SERVO_FREQ_HZ) * 65535)


def pulso(nombre, ms):
    _canal(nombre).duty_u16(_duty(ms))


def _a_ms(grados):
    grados = max(-90, min(90, grados))
    return pines.SERVO_MIN_MS + (grados + 90) / 180 * (pines.SERVO_MAX_MS - pines.SERVO_MIN_MS)


def ir(nombre, grados, paso=2, pausa_ms=20):
    """Mueve despacio (de a `paso` grados) hasta `grados`."""
    _canal(nombre)
    actual = _angulo[nombre]
    sentido = 1 if grados >= actual else -1
    a = actual
    while (grados - a) * sentido > 0:
        a += sentido * min(paso, abs(grados - a))
        pulso(nombre, _a_ms(a))
        time.sleep_ms(pausa_ms)
    pulso(nombre, _a_ms(grados))
    _angulo[nombre] = grados
    print("%s -> %d grados" % (nombre, grados))


def centrar():
    for n in pines.SERVOS:
        ir(n, 0)


def barrer(nombre, rango=30, veces=1):
    for _ in range(veces):
        ir(nombre, rango)
        ir(nombre, -rango)
    ir(nombre, 0)


def liberar():
    for n, p in _pwm.items():
        p.duty_u16(0)
    print("servos liberados")


def manual():
    nombres = list(pines.SERVOS)
    while True:
        n = input("servo %s (q = salir): " % nombres).strip()
        if n == "q":
            break
        if n not in pines.SERVOS:
            print("no existe")
            continue
        g = input("grados (-90 a 90): ").strip()
        try:
            ir(n, int(g))
        except ValueError:
            print("número inválido")
    liberar()


if __name__ == "__main__":
    centrar()
    time.sleep(1)
    for n in pines.SERVOS:
        barrer(n, 25)
    liberar()
