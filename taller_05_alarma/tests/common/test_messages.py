import pytest

from common import messages
from common.alarm import STATE_ARMED, STATE_TRIGGERED


def test_build_state_has_the_agreed_fields():
    msg = messages.build_state(STATE_ARMED, False, 2, 0, None, 42)

    assert len(msg) == 7
    assert msg["state"] == "armed"
    assert msg["door_open"] is False
    assert msg["siren"] is False
    assert msg["keys_entered"] == 2
    assert msg["wrong_attempts"] == 0
    assert msg["reason"] is None
    assert msg["uptime_s"] == 42


def test_siren_flag_is_derived_from_state():
    msg = messages.build_state(STATE_TRIGGERED, True, 0, 1, "door_open", 5)
    assert msg["siren"] is True


def test_build_event_has_the_agreed_fields():
    msg = messages.build_event(7, "door", {"open": True}, 12)

    assert msg == {"seq": 7, "event": "door", "detail": {"open": True}, "uptime_s": 12}


def test_build_online():
    assert messages.build_online(False, "pico") == {"online": False, "node": "pico"}


def test_valid_state_passes_validation():
    messages.validate_state(messages.build_state(STATE_ARMED, True, 0, 0, None, 1))
    messages.validate_state(messages.build_state(STATE_TRIGGERED, True, 0, 3, "door_open", 1))


@pytest.mark.parametrize(
    "mutation",
    [
        {"state": "exploded"},
        {"state": None},
        {"door_open": 1},
        {"siren": "yes"},
        {"keys_entered": -1},
        {"keys_entered": True},
        {"wrong_attempts": "3"},
        {"uptime_s": 1.5},
        {"reason": 42},
    ],
)
def test_invalid_state_is_rejected(mutation):
    msg = messages.build_state(STATE_ARMED, False, 0, 0, None, 1)
    msg.update(mutation)
    with pytest.raises(ValueError):
        messages.validate_state(msg)


@pytest.mark.parametrize("payload", [None, [], "armed", 5])
def test_non_object_state_is_rejected(payload):
    with pytest.raises(ValueError):
        messages.validate_state(payload)


def test_missing_state_field_is_rejected():
    msg = messages.build_state(STATE_ARMED, False, 0, 0, None, 1)
    del msg["door_open"]
    with pytest.raises(ValueError):
        messages.validate_state(msg)


def test_valid_event_passes_and_bad_event_fails():
    messages.validate_event(messages.build_event(1, "armed", {}, 0))

    with pytest.raises(ValueError):
        messages.validate_event({"seq": 1, "event": "", "detail": {}, "uptime_s": 0})
    with pytest.raises(ValueError):
        messages.validate_event({"seq": "1", "event": "x", "detail": {}, "uptime_s": 0})
    with pytest.raises(ValueError):
        messages.validate_event({"seq": 1, "event": "x", "detail": [], "uptime_s": 0})


def test_state_and_online_are_retained_but_events_are_not():
    assert messages.TOPIC_STATE in messages.RETAINED_TOPICS
    assert messages.TOPIC_ONLINE in messages.RETAINED_TOPICS
    assert messages.TOPIC_EVENT not in messages.RETAINED_TOPICS
