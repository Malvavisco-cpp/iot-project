"""Conexión WiFi del Pico W (2.4 GHz). Lee la contraseña del archivo .env del Pico.

F5 se conecta e imprime la IP. En la Shell:
    redes()          lista las redes que ve el Pico (si la suya no sale: 5 GHz o lejos)
    conectar()       se conecta con pines.WIFI_SSID
    estado()         IP y potencia de la señal (RSSI)
Códigos de estado: 3 = conectado, -2 = no encuentra la red, -3 = contraseña mal, -1 = falló.
"""

import time

import network

import pines


def _wlan():
    w = network.WLAN(network.STA_IF)
    w.active(True)
    return w


def redes():
    for r in sorted(_wlan().scan(), key=lambda r: -r[3]):
        print("%-32s %4d dBm  canal %d" % (r[0].decode(), r[3], r[2]))


def conectar(ssid=None, timeout_s=20):
    w = _wlan()
    ssid = ssid or pines.WIFI_SSID
    try:
        with open(pines.WIFI_PASSWORD_FILE) as f:
            clave = f.read().strip()
    except OSError:
        raise RuntimeError("falta el archivo %s con la contraseña" % pines.WIFI_PASSWORD_FILE)
    if not w.isconnected():
        w.connect(ssid, clave)
        fin = time.ticks_add(time.ticks_ms(), timeout_s * 1000)
        while not w.isconnected() and time.ticks_diff(fin, time.ticks_ms()) > 0:
            print("conectando... status =", w.status())
            time.sleep(1)
    estado()
    return w.isconnected()


def estado():
    w = _wlan()
    if w.isconnected():
        print("CONECTADO  IP:", w.ifconfig()[0], " RSSI:", w.status("rssi"), "dBm")
    else:
        print("sin conexión, status =", w.status())


if __name__ == "__main__":
    conectar()
