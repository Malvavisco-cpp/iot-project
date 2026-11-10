"""Prueba de conexión de la OLED. Se corre desde Thonny (F5), NO se llama main.py.

Necesita en el Pico solo este archivo y el driver (ssd1306.py o sh1106.py, según CONTROLLER). No usa WiFi ni MQTT.

    1. Escanea el bus I2C de los pines configurados y dice qué direcciones responden.
    2. Si no aparece nada, lee el nivel de SDA y SCL (una línea pegada a 0 V indica
       un problema de alimentación o de cableado) y prueba todos los pares SDA/SCL válidos del Pico y le dice
       en cuáles encontró algo (sirve para detectar cables cambiados o en otros pines).
    3. Si encuentra la pantalla, dibuja texto, un marco y una animación corta.

Con el intérprete en "MicroPython (Raspberry Pi Pico)", abra el archivo y pulse F5.
"""

import time

from machine import I2C, Pin

# --- Ajuste aquí si su montaje es distinto ------------------------------------
I2C_ID = 0
SDA_GPIO = 4
SCL_GPIO = 5
ADDR = 0x3C            # 0x3D en algunos módulos
WIDTH = 128
HEIGHT = 64            # 32 en las pantallas pequeñas
FREQ = 400000
CONTROLLER = "sh1106"   # "ssd1306" (0.96") o "sh1106" (1.3"): si queda en negro o con basura, pruebe el otro

# Pares (bus, SDA, SCL) válidos en la Pico: el bus lo decide el GPIO de SDA.
ALL_PAIRS = [
    (0, 0, 1), (0, 4, 5), (0, 8, 9), (0, 12, 13), (0, 16, 17), (0, 20, 21),
    (1, 2, 3), (1, 6, 7), (1, 10, 11), (1, 14, 15), (1, 18, 19), (1, 26, 27),
]


def scan(bus, sda, scl):
    try:
        i2c = I2C(bus, sda=Pin(sda), scl=Pin(scl), freq=FREQ)
        return i2c, i2c.scan()
    except Exception as e:
        print("  (no se pudo abrir I2C%d GP%d/GP%d: %s)" % (bus, sda, scl, e))
        return None, []


def check_lines(sda, scl):
    """Nivel en reposo de SDA y SCL con pull-up interno: deben leer 1.

    Una línea que lee 0 está pegada a tierra: módulo sin alimentación, cable
    tocando GND, VCC/GND cambiados o módulo dañado.
    """
    print("Nivel en reposo (debe ser 1):")
    stuck = []
    for name, gpio in (("SDA", sda), ("SCL", scl)):
        level = Pin(gpio, Pin.IN, Pin.PULL_UP).value()
        print("  %s (GP%d) = %d" % (name, gpio, level))
        if level == 0:
            stuck.append("%s (GP%d)" % (name, gpio))
    if stuck:
        print("  Pegada a 0 V: %s" % ", ".join(stuck))
        print("  -> Desconecte ese cable y repita: si pasa a 1, la jala la OLED o el cable")
        print("     (¿VCC sin llegar a 3V3? ¿VCC/GND cambiados? ¿cable tocando GND?).")
    else:
        print("  Las dos líneas están en alto: el cableado de datos parece bien; revise")
        print("  que VCC llegue a 3V3(OUT) (pata 36) y si el módulo trae pull-ups.")
    return stuck


def find_anywhere():
    print("Probando todos los pares SDA/SCL válidos...")
    found = []
    for bus, sda, scl in ALL_PAIRS:
        _, addrs = scan(bus, sda, scl)
        if addrs:
            print("  I2C%d  SDA=GP%d  SCL=GP%d  ->  %s" % (bus, sda, scl, [hex(a) for a in addrs]))
            found.append((bus, sda, scl, addrs))
    if not found:
        print("  Ningún par respondió.")
    return found


def demo(display):
    display.fill(0)
    display.text("OLED OK!", 0, 0, 1)
    display.text("I2C %s" % hex(ADDR), 0, 16, 1)
    display.text("GP%d SDA GP%d SCL" % (SDA_GPIO, SCL_GPIO), 0, 32, 1)
    display.rect(0, 0, WIDTH, HEIGHT, 1)
    display.show()
    time.sleep(2)

    for contrast in (0, 255, 80):
        display.contrast(contrast)
        time.sleep(0.4)

    display.invert(1)
    time.sleep(0.6)
    display.invert(0)

    for x in range(0, WIDTH - 8, 4):
        display.fill(0)
        display.rect(0, 0, WIDTH, HEIGHT, 1)
        display.fill_rect(x, HEIGHT // 2 - 4, 8, 8, 1)
        display.text("Prueba lista", 16, 4, 1)
        display.show()
    display.fill(0)
    display.text("Todo bien :)", 16, HEIGHT // 2 - 4, 1)
    display.show()


def main():
    print("=== Prueba de la OLED ===")
    print("Pines: I2C%d  SDA=GP%d  SCL=GP%d  dirección esperada %s" % (I2C_ID, SDA_GPIO, SCL_GPIO, hex(ADDR)))

    i2c, addrs = scan(I2C_ID, SDA_GPIO, SCL_GPIO)
    print("Scan:", [hex(a) for a in addrs])

    if not addrs:
        print("\nNo respondió nada en esos pines.")
        check_lines(SDA_GPIO, SCL_GPIO)
        found = find_anywhere()
        if found:
            print("\nLa pantalla está en otros pines: cambie I2C_ID / SDA_GPIO / SCL_GPIO arriba (o recablee).")
        else:
            print("\nRevise: VCC a 3V3(OUT), GND a GND, SDA y SCL (no invertidos), cables firmes.")
        return

    if ADDR not in addrs:
        print("\nHay un dispositivo, pero no en %s. Ponga ADDR = %s arriba." % (hex(ADDR), hex(addrs[0])))
        return

    try:
        if CONTROLLER == "sh1106":
            from sh1106 import SH1106_I2C as Driver
        else:
            from ssd1306 import SSD1306_I2C as Driver
    except ImportError:
        print("\nFalta %s.py en el Pico: súbalo (taller_10_oled/micropython/)." % CONTROLLER)
        return

    display = Driver(WIDTH, HEIGHT, i2c, addr=ADDR)
    demo(display)
    print("\nOK: la OLED responde y dibuja. Ya puede subir el resto del taller.")


main()
