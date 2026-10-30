"""Contrato de mensajes entre la app Flet y la pantalla OLED (Pico).

Los tópicos van SIN prefijo; el transporte MQTT antepone `config.PREFIX`.

    Flet -> Pico
      oled/text   {"text": str, "x": px, "y": px, "color": 0|1, "clear": bool}
                  Solo "text" es obligatorio. Por defecto x = 0, y = 0, color = 1
                  (píxeles encendidos) y clear = false (se escribe encima de lo que haya).
                  color = 0 borra con la forma del texto; clear = true apaga toda la
                  pantalla antes de escribir. Con clear = true, "text" puede ir vacío
                  para dejar la pantalla en blanco.
"""

from common import config

TOPIC_TEXT = "oled/text"

CHAR_PX = 8  # la fuente de framebuf es de 8x8: 16 columnas x 8 renglones en 128x64


def _is_int(value):
    # bool es subclase de int en Python; aquí no cuenta como número.
    return isinstance(value, int) and not isinstance(value, bool)


def build_text(text, x=0, y=0, color=1, clear=False):
    return {"text": text, "x": x, "y": y, "color": color, "clear": clear}


def validate_text(msg, width=config.OLED_WIDTH, height=config.OLED_HEIGHT):
    """Devuelve (text, x, y, color, clear) con los valores por defecto aplicados.

    Lanza ValueError si `msg` no es un oled/text válido (el broker es público).
    """
    if not isinstance(msg, dict):
        raise ValueError("oled/text debe ser un objeto JSON")

    text = msg.get("text")
    clear = msg.get("clear", False)
    if not isinstance(clear, bool):
        raise ValueError("clear debe ser true o false")
    if not isinstance(text, str):
        raise ValueError("text debe ser una cadena")
    if text == "" and not clear:
        raise ValueError("text vacío: use clear = true para borrar la pantalla")

    x = msg.get("x", 0)
    y = msg.get("y", 0)
    if not _is_int(x) or not 0 <= x < width:
        raise ValueError("x debe ser un entero entre 0 y %d" % (width - 1))
    if not _is_int(y) or not 0 <= y < height:
        raise ValueError("y debe ser un entero entre 0 y %d" % (height - 1))

    color = msg.get("color", 1)
    if not _is_int(color) or color not in (0, 1):
        raise ValueError("color debe ser 0 o 1")

    return text, x, y, color, clear
