"""Configuración del Pico. Ajuste aquí pines, WiFi y clave; main.py no se toca.

Los valores compartidos con Flet (broker y PREFIX) viven en common/config.py.
"""

from common.config import BROKER, PORT, PREFIX, PASSWORD_LENGTH, DEFAULT_IR_KEYMAP

# --- WiFi -------------------------------------------------------------------
WIFI_SSID = "Ejemplo"          # <- cambiar por su red
WIFI_PASSWORD_FILE = ".env"    # archivo en el Pico con SOLO la contraseña del WiFi

# --- MQTT -------------------------------------------------------------------
NODE_NAME = "alarm_node"       # main.py le agrega el id único de la placa

# --- Pines (numeración GPIO de la Pico; "LED" = LED integrado de la Pico W) ---
IR_GPIO = 22                   # Vout del receptor IR
DOOR_GPIO = "GP16"             # botón/sensor de la Puerta 1
LED_GPIO = "GP0"               # LED: fijo = alarma activa, parpadeando = sirena
SIREN_GPIO = "GP2"             # buzzer/sirena activa; None si no hay (el LED parpadea)

# Sensor de puerta. Por defecto: un botón entre 3V3 y el GPIO
# (1 = abierta, 0 = cerrada, como en el taller) con pull-down interno.
DOOR_OPEN_LEVEL = 1
DOOR_PULL = "down"             # "down", "up" o None si el circuito ya trae su resistencia
DOOR_DEBOUNCE_MS = 50

# --- Alarma -----------------------------------------------------------------
ALARM_PASSWORD = "1234"        # <- cambiar; exactamente PASSWORD_LENGTH dígitos
KEY_TIMEOUT_MS = 12000         # una clave a medias se descarta tras este tiempo
IR_KEYMAP = DEFAULT_IR_KEYMAP  # <- pegar aquí el resultado de ir_calibration.py
IR_MIN_BITS = 8                # tramas más cortas (ruido / repetición) se ignoran
PUBLISH_RAW_IR = False         # True publica cada código en IRIn/value: SOLO para depurar

# --- Tiempos ----------------------------------------------------------------
ALARM_PERIOD_MS = 20           # cada cuánto se lee la puerta y se actualizan salidas
STATE_PERIOD_MS = 5000         # cada cuánto se republica alarm/state
WATCHDOG_PERIOD_MS = 10000     # telemetría de PicoROS
