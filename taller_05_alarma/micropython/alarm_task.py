from task import Task


class AlarmTask(Task):
    """Ejecuta AlarmRuntime.poll() periódicamente dentro del Scheduler."""

    def __init__(self, scheduler, runtime, period_ms=20):
        self.runtime = runtime
        # priority=0: corre antes que la red (MQTT/WiFi) en cada barrido.
        super().__init__(scheduler, period_ms, priority=0, name="AlarmTask")

    def update(self):
        self.runtime.poll()
