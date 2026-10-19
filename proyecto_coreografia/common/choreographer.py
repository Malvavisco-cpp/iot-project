"""Choreographer: guarda secuencias y las arranca a la hora pedida (motion/sequence).

    {"action": "create",      "name", "states": [...], "run_at"?}   guarda (y programa si trae run_at)
    {"action": "delete",      "name"}                               borra, cancela y frena si corría
    {"action": "schedule",    "name", "run_at": "now" | ISO}        programa (o arranca ya)
    {"action": "execute_now", "name"}                               arranca ya (lo entiende RoDifArm.js)

`run_at` es una fecha ISO en UTC ("2025-09-25T20:00:00Z"). Para ejecutarla a la
vez que el gemelo (que usa la hora del PC), el robot necesita la hora real:
`wall_now()` devuelve ms Unix, o None mientras no se haya sincronizado por NTP.
Si llega una hora que ya pasó, arranca de inmediato (los dos gemelos hacen eso).

Sin `time`: recibe el reproductor y el reloj, así se prueba en el PC.
"""

from common import timeutil

NOW_VALUES = (None, "", "now", "immediately")


class Choreographer:

    def __init__(self, player, wall_now, on_change=None):
        self.player = player
        self.wall_now = wall_now
        self.on_change = on_change
        self.sequences = {}   # name -> [estados crudos]
        self.scheduled = {}   # name -> ms Unix

    # ----------------------------------------------------------------- MQTT

    def handle(self, payload):
        """Procesa un mensaje de motion/sequence. Lanza ValueError si es inválido."""
        if not isinstance(payload, dict):
            raise ValueError("motion/sequence debe ser un objeto JSON")
        action = payload.get("action")
        name = payload.get("name")
        if not isinstance(action, str):
            raise ValueError("falta 'action'")
        if not isinstance(name, str) or not name:
            raise ValueError("falta 'name'")

        if action == "create":
            self._create(name, payload.get("states"))
            if payload.get("run_at") not in (None, ""):
                self._schedule(name, payload["run_at"])
        elif action == "delete":
            self._delete(name)
        elif action == "schedule":
            self._schedule(name, payload.get("run_at", "now"))
        elif action == "execute_now":
            self._schedule(name, "now")
        else:
            raise ValueError("acción desconocida: %s" % action)
        self._notify()

    # ----------------------------------------------------------------- tiempo

    def tick(self):
        if not self.scheduled:
            return
        now = self.wall_now()
        if now is None:
            return
        due = [(at, name) for name, at in self.scheduled.items() if now >= at]
        for at, name in sorted(due):
            del self.scheduled[name]
            print("Coreografía: arranca '%s' (%d ms después de lo programado)" % (name, now - at))
            self._run(name)
        if due:
            self._notify()

    def next_scheduled(self):
        """(name, ms Unix) de la próxima ejecución programada, o None."""
        if not self.scheduled:
            return None
        name = min(self.scheduled, key=lambda n: self.scheduled[n])
        return name, self.scheduled[name]

    def due_within(self, window_ms):
        """True si algo está programado para dentro de menos de window_ms."""
        nxt = self.next_scheduled()
        now = self.wall_now()
        return nxt is not None and now is not None and nxt[1] - now < window_ms

    # --------------------------------------------------------------- acciones

    def _create(self, name, states):
        if not isinstance(states, list) or not states:
            raise ValueError("'create' necesita una lista 'states' no vacía")
        for i, state in enumerate(states):
            if not isinstance(state, dict):
                raise ValueError("el estado %d no es un objeto JSON" % (i + 1))
        self.sequences[name] = [dict(s) for s in states]
        print("Coreografía: '%s' guardada (%d estados)" % (name, len(states)))

    def _delete(self, name):
        self.sequences.pop(name, None)
        self.scheduled.pop(name, None)
        if self.player.mode == "sequence" and self.player.name == name:
            self.player.stop()
        print("Coreografía: '%s' borrada" % name)

    def _schedule(self, name, run_at):
        if name not in self.sequences:
            raise ValueError("no existe la secuencia '%s': mande 'create' primero" % name)
        if run_at in NOW_VALUES:
            self.scheduled.pop(name, None)
            self._run(name)
            return
        at = timeutil.iso_to_unix_ms(run_at)
        self.scheduled[name] = at
        now = self.wall_now()
        if now is None:
            print("Coreografía: '%s' programada para %s; reloj aún sin sincronizar" % (name, run_at))
        else:
            print("Coreografía: '%s' programada para %s (en %.1f s)" % (name, run_at, (at - now) / 1000))

    def _run(self, name):
        states = self.sequences.get(name)
        if not states:
            print("Coreografía: '%s' ya no existe" % name)
            return
        self.player.play(states, name=name)

    def _notify(self):
        if self.on_change is not None:
            self.on_change()
