"""Hora real (UTC, en ms) a partir de una sincronización NTP + time.ticks_ms().

El RTC del Pico solo guarda segundos enteros; para arrancar la coreografía al
mismo tiempo que el gemelo (que usa la hora del PC en ms) se guarda el instante
de la sincronización y se le suma lo que ha avanzado ticks_ms() desde entonces.
"""

from common.ticks import ticks_diff


class WallClock:

    def __init__(self, ticks_ms):
        self._ticks_ms = ticks_ms
        self._base_unix_ms = None
        self._base_ticks = 0

    @property
    def synced(self):
        return self._base_unix_ms is not None

    def set(self, unix_ms, at_ticks):
        """unix_ms era la hora real en el instante at_ticks (de ticks_ms)."""
        self._base_unix_ms = unix_ms
        self._base_ticks = at_ticks

    def now(self):
        """ms Unix actuales, o None si todavía no se ha sincronizado."""
        if self._base_unix_ms is None:
            return None
        return self._base_unix_ms + ticks_diff(self._ticks_ms(), self._base_ticks)
