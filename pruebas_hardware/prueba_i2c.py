"""Escanea el bus I2C: dice qué dispositivos contestan y en qué dirección.

F5 para correrla; luego en la Shell:  escanear()   escanear(1, 6, 7)   todos_los_pares()
Una pantalla OLED suele aparecer como 0x3c (60 en decimal).
"""

from machine import I2C, Pin

import pines

PARES = [
    (0, 0, 1), (0, 4, 5), (0, 8, 9), (0, 12, 13), (0, 16, 17), (0, 20, 21),
    (1, 2, 3), (1, 6, 7), (1, 10, 11), (1, 14, 15), (1, 18, 19), (1, 26, 27),
]


def escanear(bus=None, sda=None, scl=None, freq=400000):
    bus = pines.OLED_I2C_ID if bus is None else bus
    sda = pines.OLED_SDA if sda is None else sda
    scl = pines.OLED_SCL if scl is None else scl
    i2c = I2C(bus, sda=Pin(sda), scl=Pin(scl), freq=freq)
    dirs = i2c.scan()
    print("I2C%d SDA=GP%d SCL=GP%d ->" % (bus, sda, scl), [hex(d) for d in dirs] or "nada responde")
    return dirs


def todos_los_pares():
    """Prueba todos los pares SDA/SCL válidos: útil si no sabe en cuáles quedó el cable."""
    for bus, sda, scl in PARES:
        try:
            dirs = I2C(bus, sda=Pin(sda), scl=Pin(scl), freq=400000).scan()
        except Exception as e:
            print("I2C%d GP%d/GP%d: error %s" % (bus, sda, scl, e))
            continue
        if dirs:
            print("I2C%d SDA=GP%d SCL=GP%d ->" % (bus, sda, scl), [hex(d) for d in dirs])
    print("listo")


if __name__ == "__main__":
    if not escanear():
        print("Nada en los pines de pines.py: probando todos los pares...")
        todos_los_pares()
