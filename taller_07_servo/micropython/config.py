"""Configuración del Pico. Ajuste aquí pines y WiFi; main.py no se toca.

Los valores compartidos con Flet (broker, PREFIX, rango del servo) viven en
common/config.py.
"""

from common.config import (
    BROKER,
    PORT,
    PREFIX,
    SERVO_FREQ_HZ,
    SERVO_MAX_ANGLE,
    SERVO_MAX_PULSE_MS,
    SERVO_MIN_ANGLE,
    SERVO_MIN_PULSE_MS,
)

# --- WiFi ---------------------------------------------------------------
WIFI_SSID = "Ejemplo"          # <- cambiar por su red
WIFI_PASSWORD_FILE = ".env"    # archivo en el Pico con SOLO la contraseña del WiFi

# --- MQTT -----------------------------------------------------------------
NODE_NAME = "servo_node"       # main.py le agrega el id único de la placa

# --- Pines (numeración GPIO de la Pico) ------------------------------------
SERVO_GPIO = "GP15"             # señal PWM del servo
