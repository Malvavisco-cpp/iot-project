from datetime import datetime, timedelta, timezone

import pytest

from common import motion
from common.timeutil import iso_to_unix_ms
from flet_ui import model


def test_example_is_the_one_from_motion_topics_md():
    c = model.Choreography()
    c.load_example()

    assert c.name == "hello"
    assert len(c.states) == 6
    assert c.total_s() == pytest.approx(13.0)
    payload = c.create_payload()
    assert payload["action"] == "create" and payload["states"][1]["w_deg/s"] == 30


def test_add_remove_clear():
    c = model.Choreography("x")
    c.add(motion.build_state(1, 0, 0, 0, 0, 1))
    c.add(motion.build_state(2, 0, 0, 0, 0, 1))
    c.remove(0)
    assert c.states[0]["v_dm/s"] == 2
    c.clear()
    with pytest.raises(ValueError):
        c.create_payload()


def test_empty_name_is_rejected():
    c = model.Choreography("")
    c.add(motion.build_state(1, 0, 0, 0, 0, 1))
    with pytest.raises(ValueError):
        c.create_payload()


def test_end_pose_of_a_straight_line():
    c = model.Choreography()
    c.add(motion.build_state(2, 0, 0, 0, 0, 5))
    assert c.end_pose() == pytest.approx((10, 0, 0))


def test_run_at_in_seconds():
    now = 1_760_000_000_000
    assert iso_to_unix_ms(model.run_at_in(10, now)) == now + 10000
    with pytest.raises(ValueError):
        model.run_at_in(-1, now)


def test_run_at_local_time_converts_to_utc():
    bogota = timezone(timedelta(hours=-5))
    now = datetime(2026, 10, 19, 14, 0, 0, tzinfo=bogota)

    iso = model.run_at_local_time("15:30", now)
    assert iso == "2026-10-19T20:30:00.000Z"


@pytest.mark.parametrize("bad", ["13:00", "25:00", "aa:bb", "15"])
def test_run_at_local_time_rejects_past_or_bad(bad):
    now = datetime(2026, 10, 19, 14, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        model.run_at_local_time(bad, now)


def test_parse_float_accepts_comma():
    assert model.parse_float("2,5", "v") == 2.5
    with pytest.raises(ValueError):
        model.parse_float("dos", "v")


def test_twin_instructions_match_the_prefix():
    text = model.twin_instructions()
    assert "UDFJC/iot_ws" in text and "Robot ID 4" in text
    assert "UDFJC/iot_ws/robot4/motion" in text
