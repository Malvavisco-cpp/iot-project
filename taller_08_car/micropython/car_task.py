from task import Task


class CarTask(Task):
    """Llama a car.tick() periódicamente: así el carro frena al cumplirse t
    sin bloquear al Scheduler (el WiFi y el MQTT siguen atendiéndose).
    """

    def __init__(self, scheduler, car, period_ms=20):
        super().__init__(scheduler, period_ms, name="CarTask")
        self.car = car

    def update(self):
        self.car.tick()
