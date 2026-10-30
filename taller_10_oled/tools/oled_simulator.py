"""OLED virtual: corre en el PC la MISMA clase OLED y escucha por MQTT.

Sirve para probar la app Flet sin el Pico. En vez de píxeles, dibuja la pantalla
como una cuadrícula de 16 columnas x 8 renglones de caracteres (la fuente es de 8x8).

    python -m tools.oled_simulator              # broker y prefijo de common/config.py
"""

import argparse
import json
import threading

import paho.mqtt.client as mqtt

from common import config, messages
from common.oled import OLED


class FakeDisplay:
    """Imita lo que usa OLED de SSD1306_I2C: guarda los caracteres y los imprime en show()."""

    def __init__(self, width, height):
        self.cols = width // messages.CHAR_PX
        self.rows = height // messages.CHAR_PX
        self.grid = [[" "] * self.cols for _ in range(self.rows)]

    def fill(self, color):
        self.grid = [["#" if color else " "] * self.cols for _ in range(self.rows)]

    def text(self, string, x, y, color=1):
        row = y // messages.CHAR_PX
        col = x // messages.CHAR_PX
        if not 0 <= row < self.rows:
            return
        for i, ch in enumerate(string):
            if 0 <= col + i < self.cols:
                self.grid[row][col + i] = ch if color else " "

    def show(self):
        border = "+" + "-" * self.cols + "+"
        print(border)
        for row in self.grid:
            print("|" + "".join(row) + "|")
        print(border)


class PahoNode:
    """Lo mínimo del Node de PicoROS (subscribe) encima de paho-mqtt."""

    def __init__(self, client, prefix):
        self.client = client
        self.prefix = prefix
        self.subscriptions = {}
        client.on_message = self._on_message

    def subscribe(self, topic, callback):
        self.subscriptions[topic] = callback
        if self.client.is_connected():
            self.client.subscribe(self.prefix + topic)

    def resubscribe(self):
        for topic in self.subscriptions:
            self.client.subscribe(self.prefix + topic)

    def _on_message(self, client, userdata, message):
        topic = message.topic[len(self.prefix):]
        callback = self.subscriptions.get(topic)
        if callback is None:
            return
        try:
            msg = json.loads(message.payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return
        callback(topic=topic, msg=msg)


def main():
    parser = argparse.ArgumentParser(description="OLED virtual para probar la interfaz Flet")
    parser.add_argument("--broker", default=config.BROKER)
    parser.add_argument("--port", type=int, default=config.PORT)
    parser.add_argument("--prefix", default=config.PREFIX)
    args = parser.parse_args()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="oled_sim_pico")
    node = PahoNode(client, args.prefix)
    OLED(node, FakeDisplay(config.OLED_WIDTH, config.OLED_HEIGHT))

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            print("MQTT: no se pudo conectar:", reason_code)
            return
        print("MQTT conectado.")
        node.resubscribe()

    client.on_connect = on_connect
    client.reconnect_delay_set(1, 30)
    client.connect_async(args.broker, args.port, keepalive=30)
    client.loop_start()

    print(f"OLED virtual en {args.broker}:{args.port}, prefijo {args.prefix}")
    print("Mándele texto desde la app Flet. Ctrl+C para salir.")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
