"""Port a Python de IoT_ws/coreografia/3D/RoDifArm.js (_normalizeState,
_startMotion, runSequence, update). Solo para las pruebas: es "el gemelo".
"""

import math


def _number(value, fallback=0.0):
    try:
        n = float(value)
    except (TypeError, ValueError):
        return fallback
    return n if math.isfinite(n) else fallback


class TwinRobot:

    def __init__(self):
        self.x = self.y = self.beta = 0.0
        self.alpha = [0.0, 0.0, 0.0]
        self.v = self.w = 0.0
        self.motion = None
        self.runtime = None

    def _normalize(self, p):
        def angle(key, current):
            if key in p:
                return math.radians(_number(p[key], 0.0))
            return current

        return {
            "v": _number(p.get("v_dm/s"), 0.0) * 0.1,
            "w": math.radians(_number(p.get("w_deg/s"), 0.0)),
            "alpha": [angle("alpha%d_deg" % i, self.alpha[i]) for i in range(3)],
            "duration": max(0.001, _number(p.get("duration_s"), 1.0)),
        }

    def _start(self, s):
        self.motion = {"v": s["v"], "w": s["w"], "duration": s["duration"], "elapsed": 0.0,
                       "start": list(self.alpha), "target": s["alpha"]}
        self.v, self.w = s["v"], s["w"]

    def handle_state(self, payload):
        self.runtime = None
        self._start(self._normalize(payload))

    def run_sequence(self, states):
        self.runtime = {"states": [dict(s) for s in states], "index": 0}
        self._next()

    def _next(self):
        rt = self.runtime
        if rt["index"] >= len(rt["states"]):
            self.runtime = None
            self.motion = None
            self.v = self.w = 0.0
            return
        raw = rt["states"][rt["index"]]
        rt["index"] += 1
        self._start(self._normalize(raw))

    def update(self, dt):
        remaining = max(0.0, dt)
        guard = 0
        while remaining > 0 and self.motion and guard < 100:
            guard += 1
            m = self.motion
            step = min(remaining, max(0.0, m["duration"] - m["elapsed"]))
            if step > 0:
                self.x += m["v"] * math.cos(self.beta) * step
                self.y -= m["v"] * math.sin(self.beta) * step
                self.beta += m["w"] * step
                m["elapsed"] += step
                remaining -= step
                t = min(1.0, m["elapsed"] / m["duration"])
                for i in range(3):
                    self.alpha[i] = m["start"][i] + (m["target"][i] - m["start"][i]) * t
            if m["elapsed"] >= m["duration"]:
                self.v = self.w = 0.0
                if self.runtime:
                    self._next()
                else:
                    self.motion = None
                if step == 0 and not self.motion:
                    break
