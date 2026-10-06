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

# --- Puente H ---------------------------------------------------------------
# "mini": L298N mini (placa roja pequeña): solo IN1..IN4, el PWM va por los IN.
# "l298n": L298N grande o TB6612: ENA/ENB (o PWMA/PWMB) para la velocidad + IN1..IN4.
MOTOR_DRIVER = "mini"

# Números GPIO de la Pico (GP2 = 2), no el número de pata física.
# Ajústenlos para que coincidan con el diagrama de conexiones de la clase.
LEFT_IN1_GPIO = 2              # IN1  (L298N mini)  / IN1  (L298N) / AIN1 (TB6612)
LEFT_IN2_GPIO = 3              # IN2                / IN2          / AIN2
RIGHT_IN1_GPIO = 6             # IN3                / IN3          / BIN1
RIGHT_IN2_GPIO = 7             # IN4                / IN4          / BIN2

# Solo si MOTOR_DRIVER = "l298n" (el mini no tiene estos pines):
LEFT_PWM_GPIO = 4              # ENA (L298N) / PWMA (TB6612)
RIGHT_PWM_GPIO = 8             # ENB (L298N) / PWMB (TB6612)
STBY_GPIO = None               # solo TB6612: pin STBY (se deja en 1)

# True si esa rueda gira al revés de lo esperado con un comando de "adelante".
LEFT_INVERTED = False
RIGHT_INVERTED = False

MOTOR_PWM_FREQ_HZ = 1000

# --- Tiempos --------------------------------------------------------------
CAR_PERIOD_MS = 20             # cada cuánto se revisa si ya se cumplió t
