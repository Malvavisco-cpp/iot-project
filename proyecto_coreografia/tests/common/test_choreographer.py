import pytest

from common import motion
from common.timeutil import unix_ms_to_iso

SEQ = [motion.build_state(2, 0, 0, 0, 0, 1.0), motion.build_state(0, 0, 90, 0, 0, 1.0)]


def create(world, name="hello", states=SEQ, **extra):
    payload = motion.build_create(name, states)
    payload.update(extra)
    world.choreo.handle(payload)


def iso_in(world, ms):
    return unix_ms_to_iso(world.unix_ms + ms)


def test_create_stores_without_running(world):
    create(world)
    assert "hello" in world.choreo.sequences
    assert not world.player.active


def test_schedule_now_runs_immediately(world):
    create(world)
    world.choreo.handle(motion.build_schedule("hello", "now"))
    assert world.player.status()["name"] == "hello"


@pytest.mark.parametrize("run_at", ["now", "immediately", ""])
def test_now_aliases(world, run_at):
    create(world)
    world.choreo.handle({"action": "schedule", "name": "hello", "run_at": run_at})
    assert world.player.active


def test_missing_run_at_means_now(world):
    create(world)
    world.choreo.handle({"action": "schedule", "name": "hello"})
    assert world.player.active


def test_execute_now(world):
    create(world)
    world.choreo.handle(motion.build_execute_now("hello"))
    assert world.player.active


def test_scheduled_sequence_starts_at_the_exact_time(world):
    create(world)
    world.choreo.handle(motion.build_schedule("hello", iso_in(world, 3000)))

    world.advance(2980)
    assert not world.player.active
    world.advance(20)
    assert world.player.active and world.player.name == "hello"
    assert world.choreo.scheduled == {}


def test_a_time_in_the_past_runs_right_away(world):
    create(world)
    world.choreo.handle(motion.build_schedule("hello", iso_in(world, -5000)))
    world.advance(20)
    assert world.player.active


def test_without_ntp_it_waits_and_fires_once_the_clock_is_set(world):
    create(world)
    target = world.unix_ms + 1000
    world.unix_ms = None
    world.choreo.handle(motion.build_schedule("hello", unix_ms_to_iso(target)))

    world.advance(5000)
    assert not world.player.active        # no sabe qué hora es

    world.unix_ms = target + 200          # llega la sincronización NTP
    world.advance(20)
    assert world.player.active


def test_create_with_run_at_schedules_it(world):
    create(world, run_at=iso_in(world, 1000))
    assert "hello" in world.choreo.scheduled
    world.advance(1000)
    assert world.player.active


def test_rescheduling_replaces_the_previous_time(world):
    create(world)
    world.choreo.handle(motion.build_schedule("hello", iso_in(world, 1000)))
    world.choreo.handle(motion.build_schedule("hello", iso_in(world, 5000)))
    world.advance(2000)
    assert not world.player.active


def test_delete_cancels_and_stops_a_running_sequence(world):
    create(world)
    world.choreo.handle(motion.build_schedule("hello"))
    world.choreo.handle(motion.build_delete("hello"))

    assert "hello" not in world.choreo.sequences
    assert not world.player.active


def test_delete_cancels_a_pending_schedule(world):
    create(world)
    world.choreo.handle(motion.build_schedule("hello", iso_in(world, 1000)))
    world.choreo.handle(motion.build_delete("hello"))
    world.advance(2000)
    assert not world.player.active


def test_delete_does_not_stop_a_different_sequence(world):
    create(world, "a")
    create(world, "b")
    world.choreo.handle(motion.build_schedule("a"))
    world.choreo.handle(motion.build_delete("b"))
    assert world.player.active


def test_stored_states_are_copies(world):
    states = [dict(SEQ[0])]
    create(world, states=states)
    states[0]["v_dm/s"] = 99
    assert world.choreo.sequences["hello"][0]["v_dm/s"] == 2


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"action": "create"},
        {"action": "create", "name": "x"},
        {"action": "create", "name": "x", "states": []},
        {"action": "create", "name": "x", "states": ["no"]},
        {"action": "schedule", "name": "nunca_creada"},
        {"action": "bailar", "name": "x"},
    ],
)
def test_invalid_messages_raise(world, payload):
    with pytest.raises(ValueError):
        world.choreo.handle(payload)


def test_bad_run_at_raises(world):
    create(world)
    with pytest.raises(ValueError):
        world.choreo.handle(motion.build_schedule("hello", "mañana"))


def test_due_within(world):
    create(world)
    world.choreo.handle(motion.build_schedule("hello", iso_in(world, 4000)))
    assert world.choreo.due_within(5000)
    assert not world.choreo.due_within(3000)
