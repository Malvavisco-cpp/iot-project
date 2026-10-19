"""RobotNode: conecta los tópicos de movimiento con el reproductor y el coreógrafo.

    motion/state    -> MotionPlayer.play([estado])     (inmediato; reemplaza lo que corra)
    motion/sequence -> Choreographer.handle(mensaje)
    motion/status   <- se publica (retenido) cada vez que algo cambia

Node de PicoROS borra PARA SIEMPRE un callback que lance una excepción: por eso
los dos callbacks atrapan todo y solo imprimen el error.
"""

from common import motion, timeutil


class RobotNode:

    def __init__(self, node, player, choreographer, clock_synced=None):
        self.node = node
        self.player = player
        self.choreographer = choreographer
        self.clock_synced = clock_synced or (lambda: False)

        player.on_change = self.publish_status
        choreographer.on_change = self.publish_status

        node.subscribe(motion.TOPIC_STATE, self._on_state)
        node.subscribe(motion.TOPIC_SEQUENCE, self._on_sequence)

    def status(self):
        s = self.player.status()
        s["arm_deg"] = [round(a, 1) for a in self.player.arm.angles]
        s["sequences"] = sorted(self.choreographer.sequences)
        s["scheduled"] = dict(
            (name, timeutil.unix_ms_to_iso(at)) for name, at in self.choreographer.scheduled.items()
        )
        s["clock_synced"] = bool(self.clock_synced())
        return s

    def publish_status(self):
        try:
            self.node.publish(motion.TOPIC_STATUS, self.status())
        except Exception as e:
            # Un fallo de red jamás debe frenar la coreografía.
            print("Robot: no se pudo publicar el estado:", e)

    def _on_state(self, topic, msg):
        try:
            if not isinstance(msg, dict):
                raise ValueError("el estado debe ser un objeto JSON")
            self.player.play([msg])
        except Exception as e:
            print("Robot: motion/state ignorado:", e)

    def _on_sequence(self, topic, msg):
        try:
            self.choreographer.handle(msg)
        except Exception as e:
            print("Robot: motion/sequence ignorado:", e)
