"""Herramientas para revisar el cableado pin por pin. Números GPIO, no patas físicas.

En la Shell (después de F5):
    nivel(15)              lee el pin con pull-up (1 = alto o suelto, 0 = a tierra)
    contacto_3v3(27)       cable del pin a 3V3: debe dar 1  (0 = el cable no hace contacto)
    contacto_gnd(27)       cable del pin a GND: debe dar 0  (1 = no hace contacto)
    adc(27)                lectura analógica (solo GP26, GP27, GP28)
    adc_todos()            las tres a la vez
    salida(15, 1)          pone el pin en 1 o 0 (para un LED o un multímetro)
    pwm(15, 50, 1000)      PWM al 50 % a 1000 Hz en ese pin
    quitar_pwm(15)
    led()                  parpadea el LED de la placa (Pico W)
Patas físicas útiles: GP26 = 31, GP27 = 32, GP28 = 34, 3V3(OUT) = 36, GND = 3, 8, 13, 18, 23, 28, 33, 38.
"""

import time

from machine import ADC, PWM, Pin

_pwm = {}


def nivel(g):
    v = Pin(g, Pin.IN, Pin.PULL_UP).value()
    print("GP%d = %d" % (g, v))
    return v


def contacto_3v3(g):
    v = Pin(g, Pin.IN, Pin.PULL_DOWN).value()
    print("GP%d con pull-down = %d  (%s)" % (g, v, "hay 3V3" if v else "NO hay contacto con 3V3"))
    return v


def contacto_gnd(g):
    v = Pin(g, Pin.IN, Pin.PULL_UP).value()
    print("GP%d con pull-up = %d  (%s)" % (g, v, "está a GND" if v == 0 else "NO hay contacto con GND"))
    return v


def adc(g):
    v = ADC(Pin(g)).read_u16()
    print("GP%d ADC = %d  (%.2f V)" % (g, v, v * 3.3 / 65535))
    return v


def adc_todos():
    for g in (26, 27, 28):
        adc(g)


def salida(g, valor):
    Pin(g, Pin.OUT).value(1 if valor else 0)
    print("GP%d = %d" % (g, 1 if valor else 0))


def pwm(g, porcentaje, freq=1000):
    p = _pwm.get(g) or PWM(Pin(g))
    p.freq(freq)
    p.duty_u16(int(porcentaje / 100 * 65535))
    _pwm[g] = p
    print("GP%d PWM %.0f %% a %d Hz" % (g, porcentaje, freq))


def quitar_pwm(g):
    p = _pwm.pop(g, None)
    if p:
        p.duty_u16(0)
        p.deinit()
    print("GP%d PWM apagado" % g)


def led(veces=5):
    l = Pin("LED", Pin.OUT)
    for _ in range(veces):
        l.toggle()
        time.sleep(0.25)
    l.value(0)


if __name__ == "__main__":
    print(__doc__)
    adc_todos()
