"""Configuración compartida por el Pico, el simulador y la app Flet.

El PREFIX debe ser IGUAL en el Pico y en Flet: es lo que los empareja.
El broker es público, así que cambie `robot0` por el número de su grupo
para no mezclarse con otros equipos.
"""

from common.alarm import KEY_CLEAR

BROKER = "broker.hivemq.com"
PORT = 1883
PREFIX = "UDFJC/iot_ws/robot0/"

# La clave del taller es de exactamente 4 dígitos.
PASSWORD_LENGTH = 4

# Código IR -> tecla. Los valores son "0".."9" y KEY_CLEAR ("C": borrar lo digitado).
# Por defecto: control remoto de 21 teclas (protocolo NEC) típico de los kits.
# Cada control es distinto: verifíquelos con micropython/ir_calibration.py y
# sobreescriba IR_KEYMAP en micropython/config.py.
DEFAULT_IR_KEYMAP = {
    0xFF6897: "0",
    0xFF30CF: "1",
    0xFF18E7: "2",
    0xFF7A85: "3",
    0xFF10EF: "4",
    0xFF38C7: "5",
    0xFF5AA5: "6",
    0xFF42BD: "7",
    0xFF4AB5: "8",
    0xFF52AD: "9",
    0xFF9867: KEY_CLEAR,
}
