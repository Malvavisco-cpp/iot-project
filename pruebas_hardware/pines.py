"""Pines y datos de TODO el robot, en un solo lugar. Las pruebas leen de aquí.

Edite este archivo para que coincida con su montaje y súbalo al Pico junto con la
prueba que va a correr. Los números son GPIO (GP4 = 4), NO la pata física.
"""

# --- OLED (I2C) ----------------------------------------------------------------
OLED_I2C_ID = 0
OLED_SDA = 4
OLED_SCL = 5
OLED_ADDR = 0x3C
OLED_ANCHO = 128
OLED_ALTO = 64
OLED_CONTROLADOR = "sh1106"        # "sh1106" (1.3") o "ssd1306" (0.96")

# --- Servos (hombro y codo; sin servo de base) ---------------------------------------
SERVOS = {"hombro": 11, "codo": 12}
SERVO_FREQ_HZ = 50
SERVO_MIN_MS = 0.5                  # 0.5 ms = -90 grados (SG90 / MG90S)
SERVO_MAX_MS = 2.5                  # 2.5 ms = +90 grados; 1.5 ms = centro

# --- Motores: L298N mini (PWM directo en los IN) -------------------------------------
# (IN_adelante, IN_atras, invertido)
MOTOR_IZQ = (17, 16, False)
MOTOR_DER = (14, 15, True)
MOTOR_FREQ_HZ = 1000
MOTOR_DUTY_MIN = 0.5                # PWM con el que el motor apenas arranca (0-1)

# --- Potenciómetro (ADC) ---------------------------------------------------------------
POT_GPIO = 28                       # ADC solo en GP26, GP27 y GP28

# --- WiFi / MQTT / hora -------------------------------------------------------------------
WIFI_SSID = "Ejemplo"
WIFI_PASSWORD_FILE = ".env"         # archivo en el Pico con SOLO la contraseña
BROKER = "broker.hivemq.com"
PORT = 1883
PREFIX = "UDFJC/iot_ws/robot4/"
NTP_HOST = "pool.ntp.org"
