import os
import sys
import time

import pytest

from common import camera, mision
from common.vision_rojo import detectar_rojo

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "micropython"))

from test_mision import GEOM, H, W, imagen  # noqa: E402


class Reloj:
    def __init__(self):
        self.t = 0

    def __call__(self):
        return self.t


class FakeScheduler:
    def add(self, task):
        pass


class FakeNode:
    def __init__(self):
        self.pub, self.subs = [], {}

    def subscribe(self, topic, cb):
        self.subs[topic] = cb

    def publish(self, topic, msg):
        self.pub.append((topic, msg))


class FakePlayer:
    def __init__(self):
        self.active = False
        self.jugado, self.paradas = [], 0

    def play(self, estados, name=None):
        self.jugado.append(estados)
        self.active = True

    def stop(self):
        self.paradas += 1
        self.active = False


@pytest.fixture
def mt(monkeypatch):
    monkeypatch.setattr(time, "ticks_ms", lambda: 0, raising=False)
    monkeypatch.setattr(time, "ticks_us", lambda: 0, raising=False)
    monkeypatch.setattr(time, "ticks_diff", lambda a, b: a - b, raising=False)
    import mision_task

    reloj = Reloj()
    node, player = FakeNode(), FakePlayer()
    t = mision_task.MisionTask(FakeScheduler(), node, player, dict(GEOM), clock=reloj, camera_period_ms=700)
    t.reloj = reloj
    t.node_, t.player_ = node, player
    return t


class Camara:
    period = 2000


def test_no_hace_nada_si_no_se_arranco(mt):
    mt.on_frame(imagen(100, 40), W, H)
    assert mt.player_.jugado == []


def test_arranca_ve_y_se_mueve(mt):
    mt.camera = Camara()
    mt.node_.subs["mission/cmd"]("mission/cmd", {"action": "start"})
    assert mt.mision.corriendo and mt.camera.period == 700        # cámara más seguido durante la misión
    mt.on_frame(imagen(130, 50), W, H)                            # punto a la derecha
    assert len(mt.player_.jugado) == 1
    assert mt.player_.jugado[0][0]["w_deg/s"] < 0
    topic, est = mt.node_.pub[-1]
    assert topic == "mission/status" and est["visto"] is True and est["fase"] == "buscando"


def test_mientras_el_carro_se_mueve_ignora_imagenes(mt):
    mt.node_.subs["mission/cmd"]("mission/cmd", {"action": "start"})
    mt.on_frame(imagen(130, 50), W, H)           # ahora el carro está "moviéndose"
    n = len(mt.player_.jugado)
    mt.on_frame(imagen(130, 50), W, H)
    assert len(mt.player_.jugado) == n


def test_espera_a_que_pase_el_temblor(mt):
    mt.node_.subs["mission/cmd"]("mission/cmd", {"action": "start"})
    assert mt.settling()
    mt.reloj.t = 700
    assert not mt.settling()
    mt.player_.active = True
    mt.update()
    mt.player_.active = False
    mt.reloj.t = 800
    mt.update()                                   # frenó en t = 800
    mt.reloj.t = 1000
    assert mt.settling()
    mt.reloj.t = 1500
    assert not mt.settling()


def test_stop_frena_y_restaura_la_camara(mt):
    mt.camera = Camara()
    mt.node_.subs["mission/cmd"]("mission/cmd", {"action": "start"})
    mt.node_.subs["mission/cmd"]("mission/cmd", {"action": "stop"})
    assert not mt.mision.corriendo and mt.player_.paradas >= 1
    assert mt.camera.period == 2000


def test_sin_medidas_no_arranca_y_lo_dice(monkeypatch, mt):
    mt.params["cam_altura_m"] = None
    mt.node_.subs["mission/cmd"]("mission/cmd", {"action": "start"})
    assert not mt.mision.corriendo
    assert "cam_altura_m" in mt.node_.pub[-1][1]["motivo"]


def test_un_error_detiene_el_carro(mt, monkeypatch):
    mt.node_.subs["mission/cmd"]("mission/cmd", {"action": "start"})
    import mision_task

    def boom(*a, **k):
        raise RuntimeError("falla")

    monkeypatch.setattr(mision_task, "detectar_rojo", boom)
    mt.on_frame(imagen(100, 40), W, H)
    assert mt.mision.fase == mision.FALLO and mt.player_.paradas >= 1


def test_cruz_sobre_el_punto():
    rgb = bytearray(10 * 10 * 3)
    camera.draw_cross(rgb, 10, 10, 5, 5, size=2)
    assert rgb[(5 * 10 + 5) * 3 + 1] == 255 and rgb[(5 * 10 + 7) * 3 + 1] == 255
    assert rgb[(0 * 10 + 0) * 3 + 1] == 0
    camera.draw_cross(rgb, 10, 10, 99, 99)        # fuera de la imagen: no revienta
