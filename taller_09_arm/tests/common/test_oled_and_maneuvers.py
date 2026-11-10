import math

import pytest

from common import maneuvers, oled_view
from common.kinematics import integrate_pose

STATS = {
    "first_ts": "1.0", "mem_free_bytes": 184320, "mem_used_bytes": 86016, "rssi": -56,
    "sended": 12, "temperature_c": "24.31",
    "Motion": {"len": 10, "count": 500, "unit": "us", "min": 80, "max": 950, "avg": 120.4, "period": 20},
    "MQTTTransport": {"len": 10, "count": 90, "unit": "us", "min": 40, "max": 3100, "avg": 300, "period": 100},
}


def test_watchdog_lines_fit_the_oled():
    lines = oled_view.format_watchdog(STATS)
    assert all(len(line) <= oled_view.COLS for line in lines)
    assert "RAM lib 180KB" in lines
    assert "RSSI -56 dBm" in lines
    assert any(line.startswith("Motion") for line in lines)
    assert " 120us max 950" in lines


def test_watchdog_without_data():
    assert oled_view.format_watchdog(None) == ["Watchdog:", " esperando..."]


def test_status_lines():
    lines = oled_view.status_lines({"mode": "sequence", "name": "hello", "step": 2, "steps": 6}, True,
                                   "2026-10-19T20:00:05.000Z")
    assert lines == ["Sec hello 2/6", "Hora: OK", "Prog 20:00:05"]
    assert oled_view.status_lines({"mode": "idle"}, False)[1] == "Hora: sin NTP"


def test_scroll_covers_the_whole_list():
    s = oled_view.Scroller()
    assert s.update(0, 20) == 0
    assert s.update(65535, 20) == 12          # 20 renglones - 8 visibles


def test_scroll_ignores_adc_jitter():
    s = oled_view.Scroller()
    s.update(32768, 20)                       # offset 6
    for noise in (32700, 32900, 33200, 32400):
        assert s.update(noise, 20) == 6


def test_no_scroll_when_everything_fits():
    s = oled_view.Scroller()
    assert s.update(65535, 5) == 0
    assert oled_view.scrollbar(0, 5) is None


def test_scrollbar_moves_from_top_to_bottom():
    assert oled_view.scrollbar(0, 16)[0] == 0
    y, h = oled_view.scrollbar(8, 16)
    assert y + h == 64


def end(v_dm, w_deg, t):
    return integrate_pose(0, 0, 0, v_dm, math.radians(w_deg), t)


def test_straight_one_meter_in_dm():
    v, w, t = maneuvers.straight(10, 2)
    assert (v, w, t) == (2, 0.0, 5.0)
    assert end(v, w, t) == pytest.approx((10, 0, 0))


def test_quarter_circle_left_and_right():
    v, w, t = maneuvers.quarter_circle(10, 2, maneuvers.LEFT)
    assert w == pytest.approx(math.degrees(0.2))             # 11.46 °/s
    assert t == pytest.approx((math.pi / 2) / 0.2)           # 7.85 s
    assert end(v, w, t) == pytest.approx((10, 10, math.pi / 2))

    v, w, t = maneuvers.quarter_circle(10, 2, maneuvers.RIGHT)
    assert end(v, w, t) == pytest.approx((10, -10, -math.pi / 2))


@pytest.mark.parametrize("args", [(0, 2), (10, 0), (10, -1)])
def test_bad_maneuvers(args):
    with pytest.raises(ValueError):
        maneuvers.straight(*args)
    with pytest.raises(ValueError):
        maneuvers.quarter_circle(args[0], args[1], maneuvers.LEFT)
