"""Configuración compartida por el Pico, el simulador y la app Flet.

El PREFIX debe ser IGUAL en el Pico, en Flet y en el gemelo virtual:
    gemelo oficial (PubSub_client_web.html): prefix "UDFJC/iot_ws" + Robot ID 4
    gemelo alterno (robot_coreografia_mqtt.html): Topic base "UDFJC/iot_ws/robot4/motion"
"""

BROKER = "broker.hivemq.com"   # o la IP del broker de la clase
PORT = 1883
PREFIX = "UDFJC/iot_ws/robot4/"

# --- Carro (los mismos valores que calibraron en el taller 08) -------------
WHEEL_HALF_TRACK_M = 0.065     # d: mitad de la distancia entre los centros de las ruedas
MAX_WHEEL_SPEED_M_S = 0.5      # rapidez de una rueda con el PWM al 100 %

# --- Brazo: 3 servos ----------------------------------------------------------
# El ángulo 0° del gemelo es el servo centrado (pulso de 1.5 ms). Pulsos típicos
# de un SG90 / MG90S: 0.5 ms = -90°, 2.5 ms = +90°.
SERVO_FREQ_HZ = 50
SERVO_MIN_PULSE_MS = 0.5
SERVO_MAX_PULSE_MS = 2.5
SERVO_LIMIT_DEG = 90.0         # nunca se manda más que esto (protege la mecánica)

# Ajuste fino por articulación:
#   offset_deg: cuánto hay que sumarle al servo para que 0° quede como en el gemelo
#   inverted:   True si el servo gira al revés que el gemelo
ARM_JOINTS = {
    "alpha0": {"offset_deg": 0.0, "inverted": False},  # base: giro horizontal
    "alpha1": {"offset_deg": 0.0, "inverted": False},  # hombro
    "alpha2": {"offset_deg": 0.0, "inverted": False},  # codo
}

# --- App ------------------------------------------------------------------------
DEFAULT_SPEED_DM_S = 2.0
