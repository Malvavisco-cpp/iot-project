"""Misión autónoma en el Pico: ve el punto rojo y se mueve sola hasta ponerle el lápiz encima.

Flet solo ARRANCA y MUESTRA; no controla nada durante la misión:
    mission/cmd     <- {"action": "start"} o {"action": "stop"}      (único mensaje que se recibe)
    mission/status  -> {"fase", "iter", "motivo", "visto", "cx", "cy", "err_x", "ang_deg", "dist_m"}

La cámara le pasa cada imagen a on_frame(); si la misión corre y el robot está quieto, detecta el
rojo, decide con common.mision y manda los estados al MotionPlayer (los mismos de motion/state).
Cualquier excepción detiene el carro: un fallo de la misión nunca deja los motores andando.
"""

import time

from common import mision as mision_lib
from common.ticks import ticks_add, ticks_diff
from common.vision_rojo import detectar_rojo
from task import Task

TOPIC_CMD = mision_lib.TOPIC_CMD
TOPIC_STATUS = mision_lib.TOPIC_STATUS


class MisionTask(Task):

    def __init__(self, scheduler, node, player, params, clock=time.ticks_ms, camera_period_ms=None):
        super().__init__(scheduler, 100, name="Mision")
        self.node = node
        self.player = player
        self.params = params
        self.clock = clock
        self.mision = mision_lib.Mision(params)
        self.camera = None                      # CameraTask: se le baja el período mientras corre la misión
        self.camera_period_ms = camera_period_ms
        self._camera_period_normal = None
        self._activo_antes = False
        self._fin_mov = clock()
        node.subscribe(TOPIC_CMD, self._on_cmd)

    # ------------------------------------------------------------------ tarea

    def update(self):
        """Anota cuándo el robot se detuvo, para esperar a que pase el temblor antes de mirar."""
        activo = self.player.active
        if self._activo_antes and not activo:
            self._fin_mov = self.clock()
        self._activo_antes = activo

    @property
    def activa(self):
        return self.mision.corriendo

    def settling(self):
        """True mientras la misión corre y el robot acaba de frenar: la cámara aún no debe capturar."""
        return self.mision.corriendo and ticks_diff(self.clock(), self._fin_mov) < self.params["settle_ms"]

    # ------------------------------------------------------------------ comandos

    def _on_cmd(self, topic, msg):
        try:
            accion = msg.get("action") if isinstance(msg, dict) else None
            if accion == "start":
                self.player.stop()
                motivo = self.mision.start()
                print("Misión:", "ARRANCA" if motivo is None else "no arranca: " + motivo)
                self._fin_mov = ticks_add(self.clock(), -self.params["settle_ms"])    # aún no se ha movido: sin espera
                self._camara_rapida(motivo is None)
            elif accion == "stop":
                self._parar()
            else:
                print("Misión: comando desconocido:", msg)
            self._publicar()
        except Exception as e:
            print("Misión: comando con error:", e)
            self._parar()

    def _parar(self):
        self.player.stop()
        self.mision.stop()
        self._camara_rapida(False)

    def _camara_rapida(self, si):
        if self.camera is None or self.camera_period_ms is None:
            return
        if si:
            self._camera_period_normal = self.camera.period
            self.camera.period = self.camera_period_ms
        elif self._camera_period_normal is not None:
            self.camera.period = self._camera_period_normal
            self._camera_period_normal = None

    # ------------------------------------------------------------------ imágenes

    def on_frame(self, frame, ancho, alto):
        """Llamada por CameraTask con cada imagen nueva (bytes RGB565)."""
        if not self.mision.corriendo or self.player.active or self.settling():
            return      # en movimiento o recién frenado la imagen sale movida: se muestra, pero no se analiza
        try:
            p = self.params
            t0 = time.ticks_ms()
            det = detectar_rojo(frame, ancho, alto, p["rojo_r_min"], p["rojo_dif_min"], p["area_min"])
            ms = time.ticks_diff(time.ticks_ms(), t0)
            estados = self.mision.decidir(det, ancho, alto)
            print("Misión: %s | detección %d ms | %s" % (self.mision.fase, ms, self.mision.ultima))
            if self.mision.motivo:
                print("Misión: MOTIVO:", self.mision.motivo)
            if estados:
                self.player.play(estados)
            if not self.mision.corriendo:
                self._parar_motores_y_camara()
        except Exception as e:
            print("Misión: error, se detiene:", e)
            self.mision.fase, self.mision.motivo = mision_lib.FALLO, "error: %s" % e
            self._parar_motores_y_camara()
        self._publicar()

    def _parar_motores_y_camara(self):
        if self.mision.fase != mision_lib.LISTO:    # al terminar bien, el brazo se queda abajo
            self.player.stop()
        self._camara_rapida(False)

    def _publicar(self):
        try:
            self.node.publish(TOPIC_STATUS, self.mision.estado())
        except Exception as e:
            print("Misión: no se pudo publicar el estado:", e)


def make(config, scheduler, node, player):
    from common.config import MISION

    return MisionTask(scheduler, node, player, MISION, camera_period_ms=getattr(config, "CAMERA_PERIOD_MISION_MS", 700))
