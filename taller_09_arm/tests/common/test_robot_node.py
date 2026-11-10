from common import motion


def test_subscribes_to_both_motion_topics(world):
    assert set(world.node.subscriptions) == {motion.TOPIC_STATE, motion.TOPIC_SEQUENCE}


def test_state_topic_moves_immediately(world):
    world.node.deliver(motion.TOPIC_STATE, motion.build_state(3, 0, 0, 0, 0, 2))
    assert world.player.active and world.player.mode == "state"


def test_sequence_topic_reaches_the_choreographer(world):
    world.node.deliver(motion.TOPIC_SEQUENCE, motion.build_create("a", [motion.build_state(1, 0, 0, 0, 0, 1)]))
    world.node.deliver(motion.TOPIC_SEQUENCE, motion.build_schedule("a"))
    assert world.player.name == "a"


def test_garbage_never_raises_out_of_the_callback(world):
    # Node de PicoROS quitaría el callback para siempre si lanzara.
    for bad in (None, "x", [], {"action": "bailar", "name": "a"}, {"action": "schedule", "name": "zz"}):
        world.node.deliver(motion.TOPIC_SEQUENCE, bad)
        world.node.deliver(motion.TOPIC_STATE, bad)
    world.node.deliver(motion.TOPIC_STATE, motion.build_state(1, 0, 0, 0, 0, 1))
    assert world.player.active


def test_status_is_published_on_changes(world):
    world.node.deliver(motion.TOPIC_SEQUENCE, motion.build_create("a", [motion.build_state(1, 0, 0, 0, 0, 1)]))
    world.node.deliver(motion.TOPIC_SEQUENCE, motion.build_schedule("a"))
    world.advance(1100)

    modes = [s["mode"] for s in world.statuses()]
    assert modes[-1] == "idle" and "sequence" in modes
    last = world.statuses()[-1]
    assert last["sequences"] == ["a"]
    assert last["clock_synced"] is True
    assert set(last) == {"mode", "name", "step", "steps", "arm_deg", "sequences", "scheduled", "clock_synced"}


def test_status_lists_scheduled_times_in_iso(world):
    world.node.deliver(motion.TOPIC_SEQUENCE, motion.build_create("a", [motion.build_state(1, 0, 0, 0, 0, 1)]))
    world.node.deliver(motion.TOPIC_SEQUENCE, motion.build_schedule("a", "2030-01-01T00:00:00Z"))
    assert world.statuses()[-1]["scheduled"] == {"a": "2030-01-01T00:00:00.000Z"}


def test_publish_failure_does_not_break_motion(world):
    def broken(topic, msg):
        raise OSError("sin red")

    world.node.publish = broken
    world.node.deliver(motion.TOPIC_STATE, motion.build_state(1, 0, 0, 0, 0, 0.5))
    world.advance(600)
    assert not world.player.active
