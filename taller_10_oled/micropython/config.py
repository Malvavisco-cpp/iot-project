"""Configuración del Pico. Ajuste aquí pines y WiFi; main.py no se toca.

Lo compartido con Flet (broker, PREFIX, tamaño de la pantalla) vive en
common/config.py.

Los números son GPIO (GP4 = 4), NO el número de pata física.
"""

from common.config import BROKER, OLED_HEIGHT, OLED_WIDTH, PORT, PREFIX

# --- WiFi ---------------------------------------------------------------
WIFI_SSID = "Ejemplo"          # <- cambiar por su red (2.4 GHz)
WIFI_PASSWORD_FILE = ".env"    # archivo en el Pico con SOLO la contraseña del WiFi

# --- MQTT -----------------------------------------------------------------
NODE_NAME = "oled_node"        # main.py le agrega el id único de la placa

# --- OLED SSD1306 por I2C -----------------------------------------------------
# GP4/GP5 son los pines de I2C0 (SDA/SCL). Si usan otros, el bus tiene que
# corresponder: GP26/GP27 son I2C1 (cambien OLED_I2C_ID a 1).
OLED_I2C_ID = 0
OLED_SDA_GPIO = 4
OLED_SCL_GPIO = 5
OLED_I2C_ADDR = 0x3C           # 0x3D en algunos módulos: lo dice el scan de la Shell
OLED_I2C_FREQ_HZ = 400000
