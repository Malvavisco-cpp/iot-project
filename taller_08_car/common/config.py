"""Configuración compartida por el Pico, el simulador y la app Flet.

El PREFIX debe ser IGUAL en el Pico y en Flet: es lo que los empareja.
El broker es público: cambien `robot0` por el número de su grupo.

Unidades SI en todo el taller: metros, segundos, radianes.
"""

BROKER = "broker.hivemq.com"
PORT = 1883
PREFIX = "UDFJC/iot_ws/robot0/"

# --- Geometría del carro (MIDANLA con una regla) ---------------------------
# d: distancia del centro del carro a cada rueda = la mitad de la distancia
# entre los centros de las dos ruedas.
WHEEL_HALF_TRACK_M = 0.065

# --- Calibración de los motores ---------------------------------------------
# Rapidez lineal de una rueda (m/s) con el PWM al 100 %. Se calibra con la
# prueba de "línea recta" del README (§7); el valor por defecto es solo un
# punto de partida.
MAX_WHEEL_SPEED_M_S = 0.5

# Ningún comando dura más que esto (si se pierde la red, el carro no se va lejos).
MAX_COMMAND_S = 30.0

# Rapidez por defecto de las maniobras de la app (m/s).
DEFAULT_SPEED_M_S = 0.2
