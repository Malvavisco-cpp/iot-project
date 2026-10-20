"""Fechas ISO 8601 <-> milisegundos Unix (UTC), y lectura de una respuesta NTP.

Sin `time` ni `datetime`: MicroPython no tiene zonas horarias y su época puede
ser 1970 o 2000 según la versión, así que el cálculo de días se hace a mano
(algoritmo "days_from_civil" de Howard Hinnant).
"""

import struct

NTP_DELTA_S = 2208988800  # segundos entre 1900-01-01 (época NTP) y 1970-01-01
MS_PER_DAY = 86400000


def days_from_civil(y, m, d):
    if m <= 2:
        y -= 1
    era = y // 400
    yoe = y - era * 400
    doy = (153 * (m + (-3 if m > 2 else 9)) + 2) // 5 + d - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe - 719468


def civil_from_days(z):
    z += 719468
    era = z // 146097
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    d = doy - (153 * mp + 2) // 5 + 1
    m = mp + (3 if mp < 10 else -9)
    y = yoe + era * 400 + (1 if m <= 2 else 0)
    return y, m, d


def _int(text, what):
    if not text or not text.isdigit():
        raise ValueError("fecha inválida: %s" % what)
    return int(text)


def _split_offset(text):
    """'...Z' / '...+05:00' / '...-0500' -> (resto, minutos de desfase).

    El desfase solo puede venir después de la hora, así que se busca el signo
    en la parte que sigue a la 'T' (la fecha también lleva '-').
    """
    if text[-1:] in ("Z", "z"):
        return text[:-1], 0
    sep = text.find("T")
    if sep < 0:
        sep = text.find(" ")
    if sep < 0:
        return text, 0  # solo fecha
    for i in range(sep + 1, len(text)):
        if text[i] in "+-":
            digits = text[i + 1:].replace(":", "")
            if not digits.isdigit() or len(digits) not in (2, 4):
                raise ValueError("zona horaria inválida: %s" % text)
            minutes = int(digits[:2]) * 60 + (int(digits[2:]) if len(digits) == 4 else 0)
            return text[:i], -minutes if text[i] == "-" else minutes
    return text, 0  # sin zona: se asume UTC


def iso_to_unix_ms(text):
    """'2025-09-25T20:00:00Z' -> ms Unix. Acepta fracciones de segundo y +HH:MM.

    Sin zona horaria se asume UTC (la app de Flet siempre manda la 'Z').
    """
    if not isinstance(text, str):
        raise ValueError("la fecha debe ser texto")
    text = text.strip()
    body, offset_min = _split_offset(text)

    if "T" in body:
        date_part, time_part = body.split("T", 1)
    elif " " in body:
        date_part, time_part = body.split(" ", 1)
    else:
        date_part, time_part = body, "00:00:00"

    pieces = date_part.split("-")
    if len(pieces) != 3:
        raise ValueError("fecha inválida: %s" % text)
    y = _int(pieces[0], text)
    mo = _int(pieces[1], text)
    d = _int(pieces[2], text)

    ms = 0
    if "." in time_part:
        time_part, frac = time_part.split(".", 1)
        frac = (frac + "000")[:3]
        ms = _int(frac, text)
    hms = time_part.split(":")
    if len(hms) not in (2, 3):
        raise ValueError("hora inválida: %s" % text)
    h = _int(hms[0], text)
    mi = _int(hms[1], text)
    s = _int(hms[2], text) if len(hms) == 3 else 0

    if not (1 <= mo <= 12 and 1 <= d <= 31 and h <= 23 and mi <= 59 and s <= 60):
        raise ValueError("fecha fuera de rango: %s" % text)

    seconds = days_from_civil(y, mo, d) * 86400 + h * 3600 + mi * 60 + s
    return seconds * 1000 + ms - offset_min * 60000


def unix_ms_to_iso(ms):
    """ms Unix -> '2025-09-25T20:00:00.000Z'."""
    days, rem = divmod(int(ms), MS_PER_DAY)
    y, mo, d = civil_from_days(days)
    h, rem = divmod(rem, 3600000)
    mi, rem = divmod(rem, 60000)
    s, milli = divmod(rem, 1000)
    return "%04d-%02d-%02dT%02d:%02d:%02d.%03dZ" % (y, mo, d, h, mi, s, milli)


def ntp_to_unix_ms(packet):
    """Lee el "transmit timestamp" (bytes 40..47) de una respuesta NTP/SNTP."""
    if len(packet) < 48:
        raise ValueError("respuesta NTP incompleta")
    seconds, fraction = struct.unpack("!II", packet[40:48])
    if seconds == 0:
        raise ValueError("respuesta NTP vacía (kiss-of-death)")
    return (seconds - NTP_DELTA_S) * 1000 + ((fraction * 1000) >> 32)
