"""Configuración compartida por el Pico, el simulador y la app Flet.

El PREFIX debe ser IGUAL en el Pico y en Flet: es lo que los empareja.
El broker es público: cambien `robot4` por el número de su grupo.
"""

BROKER = "broker.hivemq.com"
PORT = 1883
PREFIX = "UDFJC/iot_ws/robot4/"

# --- Pantalla OLED SSD1306 (la fuente de framebuf mide 8x8 píxeles) ----------
OLED_WIDTH = 128
OLED_HEIGHT = 64
