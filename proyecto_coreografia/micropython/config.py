"""Configuración del Pico. Ajuste aquí pines y WiFi; main.py no se toca.

Lo compartido con Flet (broker, PREFIX, geometría del carro, servos) vive en
common/config.py.

Los números son GPIO (GP2 = 2), NO el número de pata física.
"""

from common.config import (
    ARM_JOINTS,
    BROKER,
    MAX_WHEEL_SPEED_M_S,
    PORT,
    PREFIX,
    SERVO_FREQ_HZ,
    SERVO_LIMIT_DEG,
    SERVO_MAX_PULSE_MS,
    SERVO_MIN_PULSE_MS,
    WHEEL_HALF_TRACK_M,
)

# --- WiFi ---------------------------------------------------------------
WIFI_SSID = "Ejemplo"          # <- su red (2.4 GHz)
WIFI_PASSWORD_FILE = ".env"    # archivo en el Pico con SOLO la contraseña del WiFi

# --- MQTT / hora ----------------------------------------------------------
NODE_NAME = "coreo_node"       # main.py le agrega el id único de la placa
NTP_HOST = "pool.ntp.org"

# --- Motores: L298N mini (PWM directo en IN1..IN4), igual que el taller 08 ---
# "mini" o "l298n" (L298N grande / TB6612, con ENA/ENB aparte).
MOTOR_DRIVER = "mini"
LEFT_IN1_GPIO = 2              # IN1
LEFT_IN2_GPIO = 3              # IN2
RIGHT_IN1_GPIO = 6             # IN3
RIGHT_IN2_GPIO = 7             # IN4
LEFT_PWM_GPIO = 8              # solo "l298n": ENA  (déjelo aunque no lo use)
RIGHT_PWM_GPIO = 9             # solo "l298n": ENB  (déjelo aunque no lo use)
STBY_GPIO = None               # solo TB6612
LEFT_INVERTED = False
RIGHT_INVERTED = False
MOTOR_PWM_FREQ_HZ = 1000

# --- Brazo: 3 servos a 50 Hz ------------------------------------------------
# OJO: dos pines que compartan "slice" PWM comparten frecuencia. Los motores
# van a 1000 Hz y los servos a 50 Hz, así que NO pueden compartir slice.
# slice = (GPIO // 2) % 8   ->  GP2/3=1, GP6/7=3, GP10/11=5, GP12=6. Bien.
SERVO_ALPHA0_GPIO = 10         # base
SERVO_ALPHA1_GPIO = 11         # hombro
SERVO_ALPHA2_GPIO = 12         # codo

# --- OLED SSD1306 128x64 (I2C0) y potenciómetro -----------------------------
OLED_SDA_GPIO = 4
OLED_SCL_GPIO = 5
OLED_I2C_ADDR = 0x3C
POT_GPIO = 26                  # ADC0: pata central del potenciómetro

# --- Tiempos --------------------------------------------------------------
MOTION_PERIOD_MS = 20
WATCHDOG_PERIOD_MS = 2000
OLED_PERIOD_MS = 150
