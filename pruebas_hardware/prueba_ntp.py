"""Hora por NTP (UDP 123). Necesita WiFi.

F5 sincroniza e imprime la hora UTC. Si falla, la red bloquea el puerto UDP 123
(pasa en algunas redes de universidades): use otro servidor o otra red.
    sincronizar()            con pines.NTP_HOST
    sincronizar("192.168.1.1")
"""

import time

import ntptime

import prueba_wifi
import pines


def sincronizar(host=None):
    if not prueba_wifi._wlan().isconnected():
        prueba_wifi.conectar()
    ntptime.host = host or pines.NTP_HOST
    try:
        ntptime.settime()
    except Exception as e:
        print("NTP falló:", e)
        return False
    t = time.gmtime()
    print("hora UTC: %04d-%02d-%02d %02d:%02d:%02d" % t[:6])
    return True


if __name__ == "__main__":
    sincronizar()
