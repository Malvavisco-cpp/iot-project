"""Motores con el L298N mini (PWM directo en los IN). PONGA LAS RUEDAS EN EL AIRE.

F5 hace una pasada corta (pregunta antes de mover). Luego en la Shell:
    rueda("izq", 0.7, 2)       rueda izquierda al 70 % durante 2 s (negativo = atrás)
    rueda("der", -0.7, 2)
    adelante(0.7, 2)           las dos ruedas hacia adelante
    atras(0.7, 2)
    girar_izq(0.7, 2)          sobre su eje: derecha adelante, izquierda atrás
    girar_der(0.7, 2)
    parar()                    frena ya
La potencia va de 0 a 1 y se mapea de MOTOR_DUTY_MIN a 1 (así el motor arranca).
Si una rueda gira al revés de lo esperado, cambie su "invertido" en pines.py.
"""

import time

from machine import PWM, Pin

import pines

_pwm = {}


def _par(lado):
    in1, in2, inv = pines.MOTOR_IZQ if lado == "izq" else pines.MOTOR_DER
    for g in (in1, in2):
        if g not in _pwm:
            p = PWM(Pin(g))
            p.freq(pines.MOTOR_FREQ_HZ)
            p.duty_u16(0)
            _pwm[g] = p
    return _pwm[in1], _pwm[in2], inv


def _duty(potencia):
    potencia = min(abs(potencia), 1.0)
    d = pines.MOTOR_DUTY_MIN + (1 - pines.MOTOR_DUTY_MIN) * potencia
    return int(d * 65535)


def _poner(lado, potencia):
    p1, p2, inv = _par(lado)
    if potencia == 0:
        p1.duty_u16(0)
        p2.duty_u16(0)
        return
    adelante_ = (potencia > 0) != inv
    p1.duty_u16(_duty(potencia) if adelante_ else 0)
    p2.duty_u16(0 if adelante_ else _duty(potencia))


def parar():
    for lado in ("izq", "der"):
        _poner(lado, 0)
    print("motores parados")


def rueda(lado, potencia, segundos=2):
    if lado not in ("izq", "der"):
        raise ValueError('lado debe ser "izq" o "der"')
    print("rueda %s potencia %.2f durante %.1f s" % (lado, potencia, segundos))
    try:
        _poner(lado, potencia)
        time.sleep(segundos)
    finally:
        parar()


def _dos(p_izq, p_der, segundos):
    try:
        _poner("izq", p_izq)
        _poner("der", p_der)
        time.sleep(segundos)
    finally:
        parar()


def adelante(potencia=0.7, segundos=2):
    print("adelante %.2f durante %.1f s" % (potencia, segundos))
    _dos(potencia, potencia, segundos)


def atras(potencia=0.7, segundos=2):
    print("atrás %.2f durante %.1f s" % (potencia, segundos))
    _dos(-potencia, -potencia, segundos)


def girar_izq(potencia=0.7, segundos=2):
    print("giro a la izquierda %.2f durante %.1f s" % (potencia, segundos))
    _dos(-potencia, potencia, segundos)


def girar_der(potencia=0.7, segundos=2):
    print("giro a la derecha %.2f durante %.1f s" % (potencia, segundos))
    _dos(potencia, -potencia, segundos)


if __name__ == "__main__":
    if input("Ruedas en el aire? ENTER para empezar, q para salir: ").strip() != "q":
        rueda("izq", 0.7, 1.5)
        rueda("der", 0.7, 1.5)
        adelante(0.7, 1.5)
        girar_izq(0.7, 1.5)
        girar_der(0.7, 1.5)
        print("Listo. Cada rueda debía ir adelante en las dos primeras pruebas.")
