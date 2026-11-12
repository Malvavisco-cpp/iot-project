"""MQTT contra el broker de pines.py. Necesita WiFi (prueba_wifi.py) y umqtt/simple.py.

F5 se conecta, publica un mensaje de prueba y escucha 15 s. En la Shell:
    publicar("hola")               publica en PREFIX + "prueba/ping"
    escuchar("motion/state", 20)   imprime lo que llegue a PREFIX + ese tópico durante 20 s
    escuchar("#", 20)              todo lo que haya bajo su prefijo
"""

import json
import time

import prueba_wifi
from umqtt.simple import MQTTClient

import pines

_c = None


def conectar():
    global _c
    if not prueba_wifi._wlan().isconnected():
        prueba_wifi.conectar()
    _c = MQTTClient("prueba_pico_%d" % (time.ticks_ms() % 10000), pines.BROKER, port=pines.PORT, keepalive=30)
    _c.connect()
    print("MQTT conectado a", pines.BROKER)
    return _c


def publicar(mensaje="hola", topico="prueba/ping"):
    c = _c or conectar()
    c.publish((pines.PREFIX + topico).encode(), json.dumps({"msg": mensaje}))
    print("publicado en", pines.PREFIX + topico)


def escuchar(topico="#", segundos=15):
    c = _c or conectar()

    def llego(t, m):
        print(t.decode(), m[:100])

    c.set_callback(llego)
    c.subscribe((pines.PREFIX + topico).encode())
    print("escuchando %s%s durante %d s..." % (pines.PREFIX, topico, segundos))
    fin = time.ticks_add(time.ticks_ms(), segundos * 1000)
    while time.ticks_diff(fin, time.ticks_ms()) > 0:
        c.check_msg()
        time.sleep(0.1)
    print("fin")


if __name__ == "__main__":
    conectar()
    publicar("hola desde el Pico")
    escuchar("#", 15)
