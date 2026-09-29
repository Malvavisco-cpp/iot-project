"""Configuración compartida por el Pico, el simulador y la app Flet.

El PREFIX debe ser IGUAL en el Pico y en Flet: es lo que los empareja.
El broker es público, así que cambien `robot0` por el número de su grupo
para no mezclarse con otros equipos.
"""

BROKER = "broker.hivemq.com"
PORT = 1883
PREFIX = "UDFJC/iot_ws/robot0/"

# --- Servo --------------------------------------------------------------
# Rango de ángulo del servo y el ancho de pulso (en ms) que le corresponde a
# cada extremo. Los valores por defecto son los típicos de un SG90 (0.5-2.5 ms
# a 50 Hz); ajústenlos según la hoja de datos de su servo.
SERVO_MIN_ANGLE = -90.0
SERVO_MAX_ANGLE = 90.0
SERVO_MIN_PULSE_MS = 0.5
SERVO_MAX_PULSE_MS = 2.5
SERVO_FREQ_HZ = 50.0
