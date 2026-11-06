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

# --- Calibración de las maniobras de la app (medida en el carro real) --------
# Con v = 0.4 m/s y t = 3.9 s, y LEFT_GAIN = RIGHT_GAIN = 1.0, el carro hizo lo
# pedido con estos w (el teórico de un 1/4 de círculo R = 1 m a esa rapidez es ±0.4):
#   recta: w = +0.6   izquierda: w = +2.175   derecha: w = -1.9
# Se guardan como corrección: la recta suma STRAIGHT_W_TRIM, y los arcos
# multiplican su w teórico (2.175 / 0.4 y 1.9 / 0.4).
STRAIGHT_W_TRIM = 0.6
ARC_W_GAIN_LEFT = 5.4375
ARC_W_GAIN_RIGHT = 4.75
