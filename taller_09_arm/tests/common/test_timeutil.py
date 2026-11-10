import struct
from datetime import datetime, timezone

import pytest

from common.ticks import TICKS_PERIOD, ticks_add, ticks_diff
from common.timeutil import (
    NTP_DELTA_S,
    civil_from_days,
    days_from_civil,
    iso_to_unix_ms,
    ntp_to_unix_ms,
    unix_ms_to_iso,
)
from common.wallclock import WallClock


def py_ms(*args, **kw):
    return int(datetime(*args, tzinfo=timezone.utc, **kw).timestamp() * 1000)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("2025-09-25T20:00:00Z", py_ms(2025, 9, 25, 20, 0, 0)),
        ("2025-09-25T20:00:00.250Z", py_ms(2025, 9, 25, 20, 0, 0) + 250),
        ("2025-09-25T20:00:00.5Z", py_ms(2025, 9, 25, 20, 0, 0) + 500),
        ("2025-09-25T20:00Z", py_ms(2025, 9, 25, 20, 0, 0)),
        ("2025-09-25T15:00:00-05:00", py_ms(2025, 9, 25, 20, 0, 0)),   # Colombia
        ("2025-09-25T22:00:00+0200", py_ms(2025, 9, 25, 20, 0, 0)),
        ("2025-09-25T20:00:00", py_ms(2025, 9, 25, 20, 0, 0)),         # sin zona = UTC
        ("2025-09-25", py_ms(2025, 9, 25)),
        ("2024-02-29T00:00:00Z", py_ms(2024, 2, 29)),                   # bisiesto
        ("1970-01-01T00:00:00Z", 0),
    ],
)
def test_iso_to_unix_ms(text, expected):
    assert iso_to_unix_ms(text) == expected


@pytest.mark.parametrize("bad", ["", "ayer", "2025-13-01T00:00:00Z", "2025-09-25T25:00:00Z",
                                 "2025/09/25 20:00", "2025-09-25T20:00:00+5", None, 12])
def test_bad_dates_are_rejected(bad):
    with pytest.raises(ValueError):
        iso_to_unix_ms(bad)


def test_iso_round_trip():
    ms = py_ms(2026, 10, 19, 13, 45, 7) + 123
    assert unix_ms_to_iso(ms) == "2026-10-19T13:45:07.123Z"
    assert iso_to_unix_ms(unix_ms_to_iso(ms)) == ms


def test_civil_days_round_trip_over_many_years():
    for days in range(-1000, 30000, 37):
        assert days_from_civil(*civil_from_days(days)) == days


def test_ntp_packet_is_read_with_millisecond_fraction():
    unix_s = 1760000000
    packet = bytes(40) + struct.pack("!II", unix_s + NTP_DELTA_S, 1 << 31)  # ,5 s
    assert ntp_to_unix_ms(packet) == unix_s * 1000 + 500


def test_ntp_kiss_of_death_and_short_packets_are_rejected():
    with pytest.raises(ValueError):
        ntp_to_unix_ms(bytes(48))
    with pytest.raises(ValueError):
        ntp_to_unix_ms(bytes(20))


def test_ticks_wrap_around():
    assert ticks_diff(5, TICKS_PERIOD - 5) == 10
    assert ticks_add(TICKS_PERIOD - 5, 10) == 5


def test_wallclock_adds_elapsed_ticks():
    t = {"now": TICKS_PERIOD - 100}
    clock = WallClock(lambda: t["now"])
    assert clock.now() is None and not clock.synced

    clock.set(1_000_000, t["now"])
    t["now"] = ticks_add(t["now"], 250)  # el contador da la vuelta
    assert clock.synced
    assert clock.now() == 1_000_250
