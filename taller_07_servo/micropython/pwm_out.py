"""PWMOut: salida PWM genérica controlada por MQTT.

Como GPIOOut pero con ciclo de trabajo en vez de nivel on/off: cualquiera que
publique en su tópico se lo cambia. Sirve para un servo (a través de `Servo`,
que le calcula el ciclo de trabajo a partir de un ángulo), o para cualquier
otra salida PWM: el brillo de un LED, la velocidad de un motor DC, etc.

No necesita que el Scheduler lo llame periódicamente: todo pasa por el
callback que registra en `node` al construirse (ver `common.messages`).
"""


class PWMOut:

    def __init__(self, pwm, node, topic):
        """
        pwm:   objeto con `.duty_u16(int)`, ya configurado en frecuencia
               (p. ej. `machine.PWM(machine.Pin(n))` con `.freq()` ya puesto).
        node:  el `Node` de PicoROS; se usa solo para `node.subscribe(...)`.
        topic: tópico (sin prefijo) al que se suscribe, p. ej. `messages.TOPIC_PWM_DUTY`.
        """
        self.pwm = pwm
        self.topic = topic
        node.subscribe(topic, self._on_message)

    def set_duty_u16(self, value: int) -> None:
        self.pwm.duty_u16(max(0, min(65535, int(value))))

    def _on_message(self, topic, msg):
        if not isinstance(msg, dict):
            return
        duty = msg.get("duty_u16")
        if isinstance(duty, int) and not isinstance(duty, bool):
            self.set_duty_u16(duty)
