"""Qué mostrar en el OLED (evaluación 5): estado del robot + datos del Watchdog,
con scroll controlado por el potenciómetro. Lógica pura: sin pantalla ni ADC.

OLED SSD1306 de 128x64 con la fuente de 8x8 de framebuf: 8 renglones de 16
caracteres. Se usan 15 por renglón para dejar la columna de la derecha a la
barra de scroll.
"""

COLS = 15
ROWS = 8


def _fit(text):
    return text[:COLS]


def status_lines(player_status, clock_synced, next_scheduled_iso=None):
    """Renglones de cabecera: qué está haciendo el robot y si tiene la hora."""
    mode = player_status.get("mode")
    if mode == "sequence":
        line = "Sec %s %d/%d" % (player_status.get("name"), player_status.get("step", 0), player_status.get("steps", 0))
    elif mode == "state":
        line = "Mov: estado"
    else:
        line = "Mov: quieto"
    lines = [_fit(line), "Hora: OK" if clock_synced else "Hora: sin NTP"]
    if next_scheduled_iso:
        lines.append(_fit("Prog " + next_scheduled_iso[11:19]))  # HH:MM:SS UTC
    return lines


def _kb(value):
    return "%dKB" % (value // 1024) if isinstance(value, int) else "-"


def format_watchdog(stats):
    """El diccionario que publica WatchdogTask -> renglones de <= 15 caracteres."""
    if not isinstance(stats, dict):
        return ["Watchdog:", " esperando..."]
    lines = [
        _fit("WATCHDOG #%s" % stats.get("sended", "-")),
        _fit("RAM lib " + _kb(stats.get("mem_free_bytes"))),
        _fit("RAM uso " + _kb(stats.get("mem_used_bytes"))),
        _fit("RSSI %s dBm" % stats.get("rssi", "-")),
        _fit("Temp %s C" % stats.get("temperature_c", "-")),
    ]
    tasks = sorted(k for k, v in stats.items() if isinstance(v, dict) and "period" in v)
    if tasks:
        lines.append("-- tareas --")
    for name in tasks:
        t = stats[name]
        lines.append(_fit("%s %sms" % (name[:9], t.get("period", "-"))))
        avg = t.get("avg")
        if isinstance(avg, (int, float)):
            lines.append(_fit(" %dus max %s" % (int(avg), t.get("max", "-"))))
    return lines


class Scroller:
    """Potenciómetro (0..65535) -> primer renglón visible.

    Con histéresis: el ADC del Pico baila unas decenas de cuentas, y sin esto
    la pantalla temblaría entre dos posiciones.
    """

    def __init__(self, rows=ROWS, hysteresis=0.6):
        self.rows = rows
        self.hysteresis = hysteresis
        self.offset = 0

    def update(self, raw, total_lines):
        max_offset = max(0, total_lines - self.rows)
        if max_offset == 0:
            self.offset = 0
            return 0
        target = max(0, min(65535, raw)) / 65535 * max_offset
        if abs(target - self.offset) > self.hysteresis or self.offset > max_offset:
            self.offset = min(max_offset, max(0, int(target + 0.5)))
        return self.offset


def visible(lines, offset, rows=ROWS):
    return lines[offset:offset + rows]


def scrollbar(offset, total_lines, rows=ROWS, height=64):
    """(y, alto) en píxeles de la barra de scroll, o None si todo cabe."""
    if total_lines <= rows:
        return None
    bar = max(4, height * rows // total_lines)
    y = (height - bar) * offset // (total_lines - rows)
    return y, bar
