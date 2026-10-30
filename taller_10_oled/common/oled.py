"""OLED: escribe en la pantalla el texto que llegue por MQTT.

    oled/text {"text", "x", "y", "color", "clear"} -> display.text(...) -> display.show()

No importa `machine`: recibe el `node` de PicoROS (solo usa `subscribe`) y un
`display` con la interfaz de `ssd1306.SSD1306_I2C` (`fill`, `text`, `show`).
Así corre igual en el Pico, en el simulador del PC y en los tests.
"""

from common import messages


class OLED:

    def __init__(self, node, display):
        self.node = node
        self.display = display
        node.subscribe(messages.TOPIC_TEXT, self._on_text)

    def write(self, text, x=0, y=0, color=1, clear=False):
        """Escribe `text` con su esquina superior izquierda en (x, y) y actualiza la pantalla."""
        if clear:
            self.display.fill(0)
        if text:
            self.display.text(text, x, y, color)
        self.display.show()

    def clear(self):
        self.write("", clear=True)

    # ---------------------------------------------------------------- MQTT

    # Node de PicoROS quita para siempre un callback que lance una excepción,
    # por eso este nunca la deja salir (un mensaje malo no debe dejar la pantalla muda).

    def _on_text(self, topic, msg):
        try:
            args = messages.validate_text(msg)
            self.write(*args)
        except Exception as e:
            print("OLED: oled/text ignorado:", e)
