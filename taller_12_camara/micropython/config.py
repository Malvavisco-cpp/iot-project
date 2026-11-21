"""Configuración de la cámara (taller 12). Pines = tabla del taller: GP0-GP15.

Los números son GPIO (GP2 = 2), NO la pata física.
"""

WIFI_SSID = "Ejemplo"          # <- su red (2.4 GHz)
WIFI_PASSWORD_FILE = ".env"    # archivo en el Pico con SOLO la contraseña

BROKER = "broker.hivemq.com"
PORT = 1883
PREFIX = "UDFJC/iot_ws/robot14/"   # <- con SU número de robot (2 dígitos) y la barra final
NODE_NAME = "camara"

CAMERA_PINS = {
    "shutdown": 0,             # PWDN
    "reset": 1,
    "data_0": 2,               # D0-D7 = GP2..GP9, seguidos y en orden (lo exige el PIO)
    "mclk": 10,                # XCLK
    "pclk": 11,
    "href": 12,
    "vsync": 13,
    "sda1": 14,                # SCCB = I2C1
    "scl1": 15,
}
CAMERA_I2C_ID = 1
CAMERA_SIZE_DIV = 2            # 0=640x480 1=320x240 2=160x120 3=80x60 4=40x30
CAMERA_TEST_PATTERN = 2        # 2 = barras de color (prueba el envío sin escena); 0 = imagen real
CAMERA_PERIOD_MS = 1000        # cada cuánto se manda una imagen
