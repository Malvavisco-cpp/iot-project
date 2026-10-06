import time

import network

from task import Task


class WiFiLink(Task):
    """Conecta y reconecta el WiFi SIN bloquear.

    WiFiManager (PicoROS) espera en un `while` hasta que haya red: sin WiFi el programa
    no pasaría de ahí y la alarma nunca arrancaría. Aquí connect() solo lanza el intento
    y el Scheduler sigue; la alarma funciona con o sin red.

    Expone `.wlan` (lo usa WatchdogTask para el RSSI) y `.connected`.
    """

    def __init__(self, scheduler, ssid, password, period_ms=1000, retry_ms=15000):
        super().__init__(scheduler, period_ms, name="WiFiLink")
        self.ssid = ssid
        self.password = password
        self.retry_ms = retry_ms
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self._attempt_at = time.ticks_ms()
        if ssid and password:
            self.wlan.connect(ssid, password)
        self._was_connected = False

    @property
    def connected(self):
        return self.wlan.isconnected()

    def update(self):
        connected = self.wlan.isconnected()

        if connected != self._was_connected:
            self._was_connected = connected
            if connected:
                print("WiFi conectado, IP:", self.wlan.ifconfig()[0])
            else:
                print("WiFi caído; la alarma sigue funcionando sin red")

        if connected or not (self.ssid and self.password):
            return

        now = time.ticks_ms()
        if time.ticks_diff(now, self._attempt_at) >= self.retry_ms:
            self._attempt_at = now
            print("WiFi: reintentando, status =", self.wlan.status())
            self.wlan.connect(self.ssid, self.password)
