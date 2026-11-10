"""Tareas del Scheduler de PicoROS para la coreografía."""

import time

import sntp
from common import oled_view
from common.ticks import ticks_add, ticks_diff
from common.timeutil import unix_ms_to_iso
from task import Task


class MotionTask(Task):
    """Avanza el reproductor (motores y brazo) y arranca lo programado."""

    def __init__(self, scheduler, player, choreographer, period_ms=20):
        super().__init__(scheduler, period_ms, name="Motion")
        self.player = player
        self.choreographer = choreographer

    def update(self):
        self.choreographer.tick()
        self.player.tick()


class ClockSyncTask(Task):
    """Pone la hora real por NTP al conectar el WiFi, y la refresca cada 15 min.

    La consulta bloquea hasta ~1 s, así que no se hace mientras el robot se
    mueve ni si falta poco para una coreografía programada (`should_defer`).
    """

    def __init__(self, scheduler, wifi, clock, host, should_defer=None, on_sync=None,
                 resync_ms=15 * 60 * 1000, retry_ms=10000):
        super().__init__(scheduler, 1000, name="ClockSync")
        self.wifi = wifi
        self.clock = clock
        self.host = host
        self.should_defer = should_defer
        self.on_sync = on_sync
        self.resync_ms = resync_ms
        self.retry_ms = retry_ms
        self._next = time.ticks_ms()

    def update(self):
        if not self.wifi.connected:
            return
        now = time.ticks_ms()
        if ticks_diff(now, self._next) < 0:
            return
        if self.should_defer is not None and self.should_defer():
            return
        try:
            unix_ms, at_ticks = sntp.query(self.host)
        except Exception as e:
            print("Reloj: no se pudo sincronizar con", self.host, "-", e)
            self._next = ticks_add(time.ticks_ms(), self.retry_ms)
            return
        self.clock.set(unix_ms, at_ticks)
        print("Reloj sincronizado (UTC):", unix_ms_to_iso(unix_ms))
        self._next = ticks_add(time.ticks_ms(), self.resync_ms)
        if self.on_sync is not None:
            self.on_sync()


class StatsTap:
    """Se le pasa a WatchdogTask en lugar del Node: publica igual por MQTT y
    además guarda el último dato para el OLED.

    (Suscribirse a watchdog/stats desde el mismo Pico haría que el broker le
    devolviera su propio mensaje: llegaría dos veces.)
    """

    def __init__(self, node):
        self.node = node
        self.last = None

    def publish(self, topic, msg):
        self.last = msg
        self.node.publish(topic, msg)


class OledTask(Task):
    """Evaluación 5: info del Watchdog en el OLED, scroll con el potenciómetro."""

    def __init__(self, scheduler, display, pot, tap, player, choreographer, clock, period_ms=150):
        super().__init__(scheduler, period_ms, name="Oled")
        self.display = display
        self.pot = pot
        self.tap = tap
        self.player = player
        self.choreographer = choreographer
        self.clock = clock
        self.scroller = oled_view.Scroller()
        self._last_frame = None

    def lines(self):
        nxt = self.choreographer.next_scheduled()
        header = oled_view.status_lines(
            self.player.status(),
            self.clock.synced,
            unix_ms_to_iso(nxt[1]) if nxt else None,
        )
        return header + oled_view.format_watchdog(self.tap.last)

    def update(self):
        if self.display is None:
            return
        lines = self.lines()
        offset = self.scroller.update(self.pot.read_u16(), len(lines))
        shown = oled_view.visible(lines, offset)
        frame = (offset, len(lines), tuple(shown))
        if frame == self._last_frame:
            return  # nada cambió: no se gasta tiempo en el I2C
        self._last_frame = frame

        d = self.display
        d.fill(0)
        for row, text in enumerate(shown):
            d.text(text, 0, row * 8, 1)
        bar = oled_view.scrollbar(offset, len(lines))
        if bar is not None:
            d.fill_rect(125, bar[0], 3, bar[1], 1)
        d.show()
