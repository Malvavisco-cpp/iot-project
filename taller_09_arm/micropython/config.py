"""Configuración del Pico. Ajuste aquí pines y WiFi; main.py no se toca.

Lo compartido con Flet (broker, PREFIX, geometría del carro, servos) vive en
common/config.py.

Los números son GPIO (GP2 = 2), NO el número de pata física.
"""

from common.config import (
    ARC_W_GAIN_LEFT,
    ARC_W_GAIN_RIGHT,
    STRAIGHT_W_TRIM,
    ARM_JOINTS,
    MEARM_CRANK_CENTER_DEG,
    MEARM_MAX_REL_DEG,
    MEARM_MIN_REL_DEG,
    MEARM_SHOULDER_CENTER_DEG,
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
NODE_NAME = "mearm_node"       # main.py le agrega el id único de la placa
NTP_HOST = "pool.ntp.org"

# --- Motores: L298N mini (PWM directo en IN1..IN4), igual que el taller 08 ---
# "mini" o "l298n" (L298N grande / TB6612, con ENA/ENB aparte).
MOTOR_DRIVER = "mini"
# Pines del montaje con cámara (taller 12): GP0-GP13 y GP18-GP22 son de la cámara y la
# OLED, así que los motores van en GP14-GP17 (ver la tabla de pines del README).
LEFT_IN1_GPIO = 17             # IN1
LEFT_IN2_GPIO = 16             # IN2
RIGHT_IN1_GPIO = 14            # IN3
RIGHT_IN2_GPIO = 15            # IN4
LEFT_PWM_GPIO = None           # solo "l298n": ENA (con "mini" no se usa; con "l298n" ponga un GPIO libre)
RIGHT_PWM_GPIO = None          # solo "l298n": ENB
STBY_GPIO = None               # solo TB6612
LEFT_INVERTED = False
RIGHT_INVERTED = True          # el motor derecho va montado en espejo
MOTOR_PWM_FREQ_HZ = 1000

# Fracción del PWM (0-1) con la que el motor apenas arranca. A PWM bajo el motor
# zumba pero no gira (zona muerta). Súbalo si no arranca; bájelo si arranca "de golpe".
MOTOR_MIN_DUTY = 0.5

# Factor del PWM de cada rueda para ir recto (0.98 = 2 % menos PWM en esa rueda).
# Con las dos en 1.0 no se corrige nada; bájela en la rueda que resulte más rápida.
LEFT_GAIN = 1.0
RIGHT_GAIN = 1.0

# --- Brazo: 2 servos a 50 Hz (hombro y codo; sin servo de base) -----------------
# OJO: dos pines que compartan "slice" PWM comparten frecuencia. Los motores
# van a 1000 Hz y los servos a 50 Hz, así que NO pueden compartir slice.
# slice = (GPIO // 2) % 8   ->  GP2/3=1, GP6/7=3, GP10/11=5, GP12=6. Bien.
# Base (alpha0): el robot no tiene servo de giro, así que no se usa. Con un número
# de GPIO aquí se crearía ese servo y alpha0 lo movería.
SERVO_ALPHA0_GPIO = None
SERVO_ALPHA1_GPIO = 11         # hombro (q1)
SERVO_ALPHA2_GPIO = 12         # codo (q2, mueve el antebrazo)

# --- OLED 128x64 (I2C0) y potenciómetro -----------------------------------------
# La cámara ocupa GP2-GP9 (datos), así que la OLED se mueve de GP4/GP5 a GP20/GP21
# (también son I2C0: SDA = GP20, SCL = GP21).
OLED_SDA_GPIO = 20
OLED_SCL_GPIO = 21
OLED_I2C_ADDR = 0x3C
POT_GPIO = 28                  # ADC2: pata central del potenciómetro (GP26/GP27 los usa la cámara o quedan libres)

# --- Cámara OV7670 (taller 12) ----------------------------------------------------
CAMERA_ENABLED = True          # False = el robot arranca sin cámara
CAMERA_PINS = {
    "data_0": 2,               # D0-D7 = GP2..GP9, seguidos y en orden (lo exige el PIO)
    "mclk": 22,                # XCLK (PWM a 16 MHz). GP22 = slice 3: ningún motor ni servo comparte slice con él
    "pclk": 1,
    "href": 10,
    "vsync": 13,
    "reset": 0,
    "shutdown": None,          # PWDN: unido a GND en el módulo (no hay pin libre para él)
    "sda1": 18,                # SCCB = I2C1 (SDA = GP18, SCL = GP19)
    "scl1": 19,
}
CAMERA_I2C_ID = 1
CAMERA_SIZE_DIV = 2            # 0=640x480 1=320x240 2=160x120 3=80x60 4=40x30
CAMERA_TEST_PATTERN = 0        # 0 = imagen real; 2 = barras de color (para probar el envío sin escena)
CAMERA_PERIOD_MS = 2000        # cada cuánto se manda una imagen
CAMERA_PERIOD_MISION_MS = 700      # mientras corre la misión la cámara captura más seguido
CAMERA_PAUSE_WHILE_MOVING = True   # no manda imágenes mientras el robot ejecuta un movimiento

# --- Tiempos --------------------------------------------------------------
MOTION_PERIOD_MS = 20
WATCHDOG_PERIOD_MS = 2000
OLED_PERIOD_MS = 150

# --- Arranque de servos (misma pasada que pruebas_hardware/prueba_servos.py) ---
SERVO_BARRIDO_DEG = 25         # barrido de cada servo al arrancar
SERVO_AL_ARRANCAR = True       # False = main.py no mueve los servos al encender
