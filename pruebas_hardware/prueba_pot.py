"""Potenciómetro en un pin ADC (GP26, GP27 o GP28; ver pines.py).

F5 imprime 40 lecturas: gírelo de un extremo a otro, deben ir de ~0 a ~65000.
En la Shell:
    leer()          una lectura (0-65535)
    leer(27)        otro pin ADC
    seguir(10)      imprime durante 10 s con una barra
    en_oled(10)     lo muestra en la OLED (necesita prueba_oled.py y el driver)
Si la lectura no cambia (por ejemplo siempre ~11000), la señal no llega al pin: use
prueba_pines.py (nivel, contacto) para revisar el cable.
"""

import time

from machine import ADC, Pin

import pines


def leer(gpio=None):
    return ADC(Pin(pines.POT_GPIO if gpio is None else gpio)).read_u16()


def seguir(segundos=10, gpio=None):
    a = ADC(Pin(pines.POT_GPIO if gpio is None else gpio))
    fin = time.ticks_add(time.ticks_ms(), int(segundos * 1000))
    while time.ticks_diff(fin, time.ticks_ms()) > 0:
        v = a.read_u16()
        print("%5d %s" % (v, "#" * (v * 40 // 65535)))
        time.sleep(0.2)


def en_oled(segundos=10):
    import prueba_oled as o
    a = ADC(Pin(pines.POT_GPIO))
    fin = time.ticks_add(time.ticks_ms(), int(segundos * 1000))
    while time.ticks_diff(fin, time.ticks_ms()) > 0:
        v = a.read_u16()
        d = o._d()
        d.fill(0)
        d.text("Pot GP%d" % pines.POT_GPIO, 0, 0, 1)
        d.text("%5d" % v, 0, 16, 1)
        d.rect(0, 40, 128, 12, 1)
        d.fill_rect(0, 40, v * 128 // 65535, 12, 1)
        d.show()
        time.sleep(0.1)
    o.limpiar()


if __name__ == "__main__":
    seguir(8)
