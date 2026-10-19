"""Consulta SNTP con precisión de milisegundos.

`ntptime` (el que trae MicroPython) solo da segundos enteros: para arrancar a la
vez que el gemelo hace falta más precisión, así que se lee la fracción de
segundo de la respuesta y se compensa la mitad del tiempo de ida y vuelta.
"""

import socket
import time

from common.timeutil import ntp_to_unix_ms


def query(host, timeout_s=1.0):
    """-> (ms Unix, ticks_ms en que era esa hora). Lanza OSError si no responde."""
    addr = socket.getaddrinfo(host, 123)[0][-1]
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.settimeout(timeout_s)
        packet = bytearray(48)
        packet[0] = 0x1B  # LI=0, versión 3, modo cliente
        t0 = time.ticks_ms()
        sock.sendto(packet, addr)
        data = sock.recv(48)
        t1 = time.ticks_ms()
    finally:
        sock.close()
    round_trip = time.ticks_diff(t1, t0)
    return ntp_to_unix_ms(data) + round_trip // 2, t1
