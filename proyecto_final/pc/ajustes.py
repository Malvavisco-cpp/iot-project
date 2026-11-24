"""Ajustes del proyecto final en el PC. Lo del robot (broker, PREFIX) sale del config
compartido de taller_09_arm: se cambia en un solo sitio.
"""

import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_RAIZ, "taller_09_arm"))

from common import config as _robot  # noqa: E402

BROKER = _robot.BROKER
PORT = _robot.PORT
PREFIX = _robot.PREFIX            # 'UDFJC/iot_ws/robot34/' (2 dígitos y barra final)

TOPIC_FRAME = PREFIX + "camera/frame/+"
TOPIC_SEQUENCE = PREFIX + "motion/sequence"
TOPIC_STATE = PREFIX + "motion/state"

# --- Color objetivo (HSV de OpenCV: H 0-179, S y V 0-255) -----------------------------
# Rojo cruza el 0 de H, por eso son dos rangos. Mida el suyo con la cámara real.
COLORES = {
    "rojo": [((0, 120, 70), (10, 255, 255)), ((170, 120, 70), (179, 255, 255))],
    "verde": [((40, 80, 60), (85, 255, 255))],
    "azul": [((95, 120, 60), (130, 255, 255))],
}
COLOR_OBJETIVO = "rojo"
AREA_MIN_PX = 12                  # a 160x120 un punto lejano ocupa pocos píxeles

# --- Geometría (MEDIR y poner aquí; están en cero a propósito) -------------------------
CAM_ALTURA_M = 0.0                # altura de la cámara sobre el piso
CAM_INCLINACION_DEG = 0.0         # cuánto mira hacia abajo respecto a la horizontal
CAM_FOV_VERT_DEG = 0.0            # campo de visión vertical del OV7670 con su lente
ALCANCE_BRAZO_M = 0.08            # MeArm estirado (~8 cm): el punto debe quedar a esta distancia
DIST_PARADA_M = 0.0               # a cuántos m del punto se detiene el carro para bajar el brazo
