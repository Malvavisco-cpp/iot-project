from flet_ui.steps import STEP_ANGLE, STEP_WAIT, StepSequence


def test_steps_run_in_the_order_they_were_added():
    seq = StepSequence()
    seq.add_angle(20)
    seq.add_wait(2)
    seq.add_angle(-45)

    calls = []
    seq.run(
        set_angle=lambda a: calls.append(("angle", a)),
        wait=lambda s: calls.append(("wait", s)),
    )

    assert calls == [("angle", 20), ("wait", 2), ("angle", -45)]


def test_describe_reads_naturally():
    seq = StepSequence()
    seq.add_angle(20)
    seq.add_wait(1.5)

    assert seq.steps[0].describe() == "Poner el servo a 20°"
    assert seq.steps[1].describe() == "Esperar 1.5 s"


def test_remove_deletes_the_step_at_that_index():
    seq = StepSequence()
    seq.add_angle(1)
    seq.add_angle(2)
    seq.add_angle(3)

    seq.remove(1)

    assert [s.value for s in seq.steps] == [1, 3]


def test_clear_empties_the_sequence():
    seq = StepSequence()
    seq.add_angle(1)
    seq.add_wait(1)

    seq.clear()

    assert seq.steps == []


def test_on_step_is_called_before_each_step_with_its_index():
    seq = StepSequence()
    seq.add_angle(10)
    seq.add_angle(20)

    seen = []
    seq.run(set_angle=lambda a: None, wait=lambda s: None, on_step=lambda i, step: seen.append((i, step.value)))

    assert seen == [(0, 10), (1, 20)]


def test_cancelling_stops_before_the_next_step():
    seq = StepSequence()
    seq.add_angle(1)
    seq.add_angle(2)
    seq.add_angle(3)

    calls = []
    seq.run(
        set_angle=lambda a: calls.append(a),
        wait=lambda s: None,
        is_cancelled=lambda: len(calls) >= 1,
    )

    assert calls == [1]


def test_step_kinds_are_distinct():
    assert STEP_ANGLE != STEP_WAIT
