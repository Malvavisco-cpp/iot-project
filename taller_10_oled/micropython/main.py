"""Pantalla OLED por MQTT - punto de entrada del Pico.

Se guarda como main.py en la raíz del Pico: arranca solo al energizar.

    Flet -> oled/text {text, x, y, color, clear} -> OLED -> SSD1306 (I2C)
"""

import machine
import ubinascii
from machine import I2C, Pin

import config
from common.oled import OLED
from ssd1306 import SSD1306_I2C

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


def make_display():
    i2c = I2C(
        config.OLED_I2C_ID,
        sda=Pin(config.OLED_SDA_GPIO),
        scl=Pin(config.OLED_SCL_GPIO),
        freq=config.OLED_I2C_FREQ_HZ,
    )
    found = i2c.scan()
    print("I2C scan:", [hex(a) for a in found])
    if config.OLED_I2C_ADDR not in found:
        raise RuntimeError(
            "OLED: no aparece en 0x%02x (scan: %s). Revise SDA/SCL, VCC/GND y OLED_I2C_ADDR."
            % (config.OLED_I2C_ADDR, [hex(a) for a in found])
        )
    return SSD1306_I2C(config.OLED_WIDTH, config.OLED_HEIGHT, i2c, addr=config.OLED_I2C_ADDR)


def main():
    board_id = ubinascii.hexlify(machine.unique_id()).decode()
    client_id = config.NODE_NAME + "_" + board_id

    display = make_display()

    scheduler = SafeScheduler()
    node = Node(prefix=config.PREFIX, node_name=config.NODE_NAME)

    # OLED se suscribe a oled/text aquí; Node le pasa esa suscripción al
    # MQTTTransport cuando este se registra (add_transport).
    oled = OLED(node, display)
    oled.write("OLED lista", 0, 0, clear=True)
    oled.write("conectando...", 0, 16)

    def on_connect():
        oled.write("OLED lista", 0, 0, clear=True)
        oled.write("MQTT conectado", 0, 16)

    wifi = WiFiLink(scheduler, config.WIFI_SSID, read_wifi_password())

    MQTTTransport(
        scheduler,
        node,
        wifi,
        client_id=client_id,
        broker=config.BROKER,
        port=config.PORT,
        prefix=config.PREFIX,
        on_connect=on_connect,
    )

    print("OLED lista | nodo:", client_id, "| prefijo:", config.PREFIX)
    scheduler.run()


main()
