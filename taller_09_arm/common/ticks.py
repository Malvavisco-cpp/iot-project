"""Aritmética de time.ticks_ms() de MicroPython (da la vuelta cada 2**30 ms, ~12 días).

Se reimplementa aquí para que la lógica funcione igual en el PC y en los tests.
"""

TICKS_PERIOD = 1 << 30
_TICKS_HALF = TICKS_PERIOD >> 1


def ticks_diff(new, old):
    """new - old, tolerante a la vuelta del contador (como time.ticks_diff)."""
    diff = (new - old) & (TICKS_PERIOD - 1)
    if diff >= _TICKS_HALF:
        diff -= TICKS_PERIOD
    return diff


def ticks_add(ticks, delta):
    return (ticks + delta) & (TICKS_PERIOD - 1)
