import gc
import sys
import time

from scheduler import Scheduler


class SafeScheduler(Scheduler):
    """Scheduler de PicoROS que sobrevive a errores de una tarea.

    El original deja morir todo el programa si UNA tarea lanza una excepción (p. ej.
    un OSError de red) y además llama a gc.collect() en cada vuelta (cada ~1 ms).
    Para una alarma que debe funcionar sola, una caída de WiFi no puede apagarla.
    """

    def __init__(self, gc_period_ms=1000):
        super().__init__()
        self.gc_period_ms = gc_period_ms

    def run(self):
        last_gc = time.ticks_ms()
        while True:
            now = time.ticks_ms()

            for task in self.tasks:
                if time.ticks_diff(now, task.next_run) >= 0:
                    task.next_run = time.ticks_add(now, task.period)
                    try:
                        task.update_measured()
                    except Exception as e:
                        print("SafeScheduler: error en", task.name)
                        sys.print_exception(e)

            if time.ticks_diff(now, last_gc) >= self.gc_period_ms:
                gc.collect()
                last_gc = now

            time.sleep_ms(1)
