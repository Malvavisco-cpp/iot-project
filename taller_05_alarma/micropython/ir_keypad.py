import sys

from ir_in import IRIn


class KeypadIR(IRIn):
    """IRIn que entrega cada trama directamente a la alarma (on_code), sin dar la vuelta por MQTT.

    Por qué no suscribir la alarma a `IRIn/value` con Node:
      * Node.subscribe() también suscribe el tópico en el broker; como el Pico publica
        en ese mismo tópico, el broker devuelve el eco y cada tecla se contaría DOS veces.
      * La alarma debe funcionar aunque no haya WiFi ni broker.
      * Publicar cada tecla en un broker público filtraría la clave. Por defecto NO se
        publica; `raw_topic` solo se usa para depurar.

    Las tramas de menos de `min_bits` bits (ruido, o la trama de "repetición" que el
    control manda si se deja la tecla presionada) se descartan.
    """

    def __init__(self, scheduler, pin_ir, on_code, min_bits=8, pubsub=None, raw_topic=None, **kwargs):
        self.on_code = on_code
        self.min_bits = min_bits
        self.raw_topic = raw_topic
        super().__init__(scheduler=scheduler, pubsub=pubsub, pin_ir=pin_ir, **kwargs)

    def update(self):
        if not self.new_code:
            return

        code = self.last_code
        bits = self.last_bits
        self.new_code = False

        if bits < self.min_bits:
            print("IR: 0x%X (%d bits, descartado: ruido o repetición)" % (code, bits))
            return

        print("IR: 0x%X (%d bits)" % (code, bits))

        if self.raw_topic and self.pubsub:
            self.pubsub.publish(self.raw_topic, {"value": code})

        try:
            self.on_code(code)
        except Exception as e:
            sys.print_exception(e)
