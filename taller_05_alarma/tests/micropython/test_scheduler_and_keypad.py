"""SafeScheduler y KeypadIR (con la clase IRIn real del taller y la PIO simulada)."""

import gc

import pytest

import ir_keypad
import safe_scheduler
from task import Task

ON_THRESHOLD_US = 20000


# --------------------------------------------------------------------------
# SafeScheduler
# --------------------------------------------------------------------------

class Counter(Task):
    def __init__(self, scheduler, period_ms, name, stop_after=None, boom_on=()):
        super().__init__(scheduler, period_ms, name=name)
        self.calls = 0
        self.stop_after = stop_after
        self.boom_on = boom_on

    def update(self):
        self.calls += 1
        if self.calls in self.boom_on:
            raise OSError("fallo de red")
        if self.stop_after is not None and self.calls >= self.stop_after:
            raise KeyboardInterrupt  # BaseException: es la forma de detener run() en el test


def test_a_failing_task_does_not_stop_the_scheduler_or_other_tasks():
    scheduler = safe_scheduler.SafeScheduler()
    flaky = Counter(scheduler, 10, "flaky", boom_on=(1, 2, 3))
    healthy = Counter(scheduler, 10, "healthy", stop_after=20)

    with pytest.raises(KeyboardInterrupt):
        scheduler.run()

    assert healthy.calls == 20
    assert flaky.calls >= 4  # siguió corriendo después de fallar 3 veces


def test_tasks_run_at_their_own_period():
    scheduler = safe_scheduler.SafeScheduler()
    fast = Counter(scheduler, 10, "fast")
    slow = Counter(scheduler, 100, "slow", stop_after=5)

    with pytest.raises(KeyboardInterrupt):
        scheduler.run()

    assert fast.calls > slow.calls * 5


def test_gc_runs_periodically_not_every_loop(monkeypatch):
    calls = []
    monkeypatch.setattr(gc, "collect", lambda: calls.append(1))
    scheduler = safe_scheduler.SafeScheduler(gc_period_ms=1000)
    Counter(scheduler, 1, "t", stop_after=3500)

    with pytest.raises(KeyboardInterrupt):
        scheduler.run()

    assert 2 <= len(calls) <= 4  # ~1 por segundo, no ~3500


# --------------------------------------------------------------------------
# Simulación de la salida de la PIO para una trama NEC
# --------------------------------------------------------------------------

def off_word(off_us: int) -> int:
    """Lo que la PIO empuja al terminar un OFF: el contador restante."""
    return ON_THRESHOLD_US - off_us


def on_word(on_us: int) -> int:
    """Lo que empuja al terminar un ON: invert(restante); el bit 31 lo marca para ignorarlo."""
    return (~(ON_THRESHOLD_US - on_us)) & 0xFFFFFFFF


def nec_bits(address: int, command: int) -> list:
    """NEC: 4 bytes (dir, ~dir, cmd, ~cmd), cada uno con el bit menos significativo primero."""
    bits = []
    for byte in (address, address ^ 0xFF, command, command ^ 0xFF):
        bits += [(byte >> i) & 1 for i in range(8)]
    return bits


def nec_frame_words(address: int, command: int) -> list:
    words = [0]                                   # END de la espera previa
    words += [on_word(9000), off_word(4500)]      # cabecera
    for bit in nec_bits(address, command):
        words += [on_word(560), off_word(1690 if bit else 560)]
    words += [on_word(560), 0]                    # bit de parada + END
    return words


def repeat_frame_words() -> list:
    """Lo que manda el control si se deja la tecla presionada."""
    return [on_word(9000), off_word(2250), on_word(560), 0]


class Rig:
    def __init__(self, **kwargs):
        self.codes = []
        self.published = []

        class Bus:
            def publish(inner, topic, msg):
                self.published.append((topic, msg))

        self.keypad = ir_keypad.KeypadIR(
            safe_scheduler.SafeScheduler(),
            pin_ir=22,
            on_code=self.codes.append,
            pubsub=Bus(),
            **kwargs,
        )

    def feed(self, words):
        sm = self.keypad.sm
        sm.fifo.extend(words)
        sm.handler(sm)          # la IRQ de la PIO
        self.keypad.update()    # la tarea del Scheduler


def expected_code(address: int, command: int) -> int:
    code = 0
    for bit in nec_bits(address, command):
        code = (code << 1) | bit
    return code


# --------------------------------------------------------------------------
# KeypadIR
# --------------------------------------------------------------------------

def test_a_nec_frame_is_decoded_into_one_32_bit_code():
    rig = Rig()
    rig.feed(nec_frame_words(address=0x00, command=0x16))

    assert rig.codes == [expected_code(0x00, 0x16)]
    assert rig.keypad.last_bits == 32


def test_different_keys_give_different_codes():
    rig = Rig()
    rig.feed(nec_frame_words(0x00, 0x16))
    rig.feed(nec_frame_words(0x00, 0x0C))

    assert len(rig.codes) == 2
    assert rig.codes[0] != rig.codes[1]


def test_a_repeat_frame_from_a_held_key_is_ignored():
    rig = Rig()
    rig.feed(nec_frame_words(0x00, 0x16))
    rig.feed(repeat_frame_words())
    rig.feed(repeat_frame_words())

    assert len(rig.codes) == 1


def test_the_spurious_end_event_at_boot_is_ignored():
    rig = Rig()
    rig.feed([0])  # la PIO emite un END al arrancar, con 0 bits

    assert rig.codes == []


def test_pio_is_started_with_the_frame_end_threshold():
    rig = Rig()
    assert rig.keypad.sm.active_flag == 1
    assert rig.keypad.sm.put_values == [ON_THRESHOLD_US]


def test_codes_are_delivered_locally_and_not_published_by_default():
    rig = Rig()
    rig.feed(nec_frame_words(0x00, 0x16))

    assert rig.published == []  # la clave no sale a un broker público


def test_raw_code_is_published_only_when_debugging():
    rig = Rig(raw_topic="IRIn/value")
    rig.feed(nec_frame_words(0x00, 0x16))

    assert rig.published == [("IRIn/value", {"value": expected_code(0x00, 0x16)})]


def test_a_failing_callback_does_not_crash_the_task():
    rig = Rig()

    def boom(code):
        raise ValueError("bug")

    rig.keypad.on_code = boom
    rig.feed(nec_frame_words(0x00, 0x16))  # no debe lanzar


def test_new_code_flag_is_cleared_so_a_frame_is_delivered_once():
    rig = Rig()
    rig.feed(nec_frame_words(0x00, 0x16))
    rig.keypad.update()
    rig.keypad.update()

    assert len(rig.codes) == 1


def test_min_bits_is_configurable():
    rig = Rig(min_bits=40)
    rig.feed(nec_frame_words(0x00, 0x16))

    assert rig.codes == []
