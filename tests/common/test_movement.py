from common.movement import Move


def test_create_state_basic():
    move = Move()
    state = move.create_state(1.5, 10.0, -10.0, 90.0, 2.0)

    assert len(state) == 5
    assert state["v_dm/s"] == 1.5
    assert state["w_deg/s"] == 45.0
    assert state["alpha_1"] == 10.0
    assert state["alpha_2"] == -10.0
    assert state["duration_s"] == 2.0


def test_create_state_zero_duration_does_not_raise():
    move = Move()
    state = move.create_state(0.0, 0.0, 0.0, 90.0, 0.0)

    assert state["w_deg/s"] == 0.0
    assert state["duration_s"] == 0.0


def test_s_movement_structure():
    move = Move()
    msg = move.s_movement("move")

    assert len(msg) == 3
    assert msg["action"] == "move"
    assert msg["name"] == "S_Move"
    assert isinstance(msg["states"], list)
    assert len(msg["states"]) == 4


def test_s_movement_states_have_expected_shape():
    move = Move()
    msg = move.s_movement("move")

    for state in msg["states"]:
        assert set(state.keys()) == {
            "v_dm/s", "w_deg/s", "alpha_1", "alpha_2", "duration_s"
        }
        assert state["duration_s"] >= 0.0
        assert state["duration_s"] <= 5.0
