"""Configuración del Pico. Ajuste aquí pines y WiFi; main.py no se toca.

Lo compartido con Flet (broker, PREFIX, geometría y calibración del carro)
vive en common/config.py.
"""

from common.config import (
    BROKER,
    MAX_COMMAND_S,
    MAX_WHEEL_SPEED_M_S,
    PORT,
    PREFIX,
    WHEEL_HALF_TRACK_M,
)

# --- WiFi ---------------------------------------------------------------
WIFI_SSID = "Ejemplo"          # <- cambiar por su red (2.4 GHz)
WIFI_PASSWORD_FILE = ".env"    # archivo en el Pico con SOLO la contraseña del WiFi

# --- MQTT -----------------------------------------------------------------
NODE_NAME = "car_node"         # main.py le agrega el id único de la placa

# --- Pines del puente H (números GPIO de la Pico) --------------------------
# Ajústenlos para que coincidan con el diagrama de conexiones de la clase.
# Puente tipo L298N (ENA/IN1/IN2, ENB/IN3/IN4) o TB6612 (PWMA/AIN1/AIN2, ...).
LEFT_PWM_GPIO = 2              # ENA  (L298N)  / PWMA (TB6612)
LEFT_IN1_GPIO = 3              # IN1           / AIN1
LEFT_IN2_GPIO = 4              # IN2           / AIN2

RIGHT_PWM_GPIO = 6             # ENB           / PWMB
RIGHT_IN1_GPIO = 7             # IN3           / BIN1
RIGHT_IN2_GPIO = 8             # IN4           / BIN2

STBY_GPIO = None               # solo TB6612: pin STBY (se deja en 1). L298N: None

# True si esa rueda gira al revés de lo esperado con un comando de "adelante".
LEFT_INVERTED = False
RIGHT_INVERTED = False

MOTOR_PWM_FREQ_HZ = 1000

# --- Tiempos --------------------------------------------------------------
CAR_PERIOD_MS = 20             # cada cuánto se revisa si ya se cumplió t
