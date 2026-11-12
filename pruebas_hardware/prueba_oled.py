"""Pantalla OLED. Sube con ella: pines.py y el driver (sh1106.py o ssd1306.py).

F5 corre una demo corta. Luego en la Shell:
    texto("Hola", 0, 0)        escribe sin borrar lo anterior (x, y en píxeles; la fuente es de 8x8)
    renglon(2, "Hola")         borra el renglón 2 (de 0 a 7) y escribe ahí
    limpiar()                  pantalla en blanco
    llenar()                   todos los píxeles encendidos
    contraste(0..255)          invertir(True/False)     rotar(True/False)
"""

import time

from machine import I2C, Pin

import pines

_pantalla = None


def abrir():
    global _pantalla
    i2c = I2C(pines.OLED_I2C_ID, sda=Pin(pines.OLED_SDA), scl=Pin(pines.OLED_SCL), freq=400000)
    if pines.OLED_ADDR not in i2c.scan():
        raise RuntimeError("OLED no aparece en %s (scan: %s)" % (hex(pines.OLED_ADDR), [hex(a) for a in i2c.scan()]))
    if pines.OLED_CONTROLADOR == "sh1106":
        from sh1106 import SH1106_I2C as Driver
    else:
        from ssd1306 import SSD1306_I2C as Driver
    _pantalla = Driver(pines.OLED_ANCHO, pines.OLED_ALTO, i2c, addr=pines.OLED_ADDR)
    return _pantalla


def _d():
    return _pantalla or abrir()


def texto(s, x=0, y=0, color=1):
    d = _d()
    d.text(s, x, y, color)
    d.show()


def renglon(n, s):
    d = _d()
    d.fill_rect(0, n * 8, pines.OLED_ANCHO, 8, 0)
    d.text(s, 0, n * 8, 1)
    d.show()


def limpiar():
    d = _d()
    d.fill(0)
    d.show()


def llenar():
    d = _d()
    d.fill(1)
    d.show()


def contraste(valor):
    _d().contrast(valor)


def invertir(si=True):
    _d().invert(1 if si else 0)


def rotar(si=True):
    _d().rotate(si)
    _d().show()


def demo():
    d = _d()
    d.fill(0)
    d.rect(0, 0, pines.OLED_ANCHO, pines.OLED_ALTO, 1)
    for r in range(1, 7):
        d.text("Renglon %d" % r, 8, r * 8 + 4 - 8, 1)
    d.show()
    time.sleep(2)
    llenar()
    time.sleep(0.6)
    limpiar()
    texto("OLED lista", 20, 28)


if __name__ == "__main__":
    demo()
