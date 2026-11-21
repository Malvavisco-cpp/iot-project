"""Taller 12: el Pico publica imágenes del OV7670 por MQTT. Se guarda como main.py en el Pico."""

import machine
import ubinascii

import config
from camera_task import make
from mqtt import MQTTTransport
from node import Node
from safe_scheduler import SafeScheduler
from wifi import WiFiLink


def password():
    try:
        with open(config.WIFI_PASSWORD_FILE) as f:
            return f.read().strip()
    except OSError:
        print("Sin", config.WIFI_PASSWORD_FILE)
        return None


scheduler = SafeScheduler()
node = Node(prefix=config.PREFIX, node_name=config.NODE_NAME)
client_id = config.NODE_NAME + "_" + ubinascii.hexlify(machine.unique_id()).decode()
wifi = WiFiLink(scheduler, config.WIFI_SSID, password())
mqtt = MQTTTransport(scheduler, node, wifi, client_id=client_id, broker=config.BROKER,
                     port=config.PORT, prefix=config.PREFIX)
make(config, scheduler, node, is_online=lambda: mqtt.connected)
print("Cámara -> %scamera/frame/..." % config.PREFIX)
scheduler.run()
