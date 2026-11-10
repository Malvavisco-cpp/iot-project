"""Interfaz Flet del Carrobot con brazo MeArm (taller 09).

Ejecutar desde la carpeta del proyecto:   python -m flet_ui.main

    1. Estado inmediato (motion/state) + brazo + DETENER     -> evaluaciones 1 y 4
    2. Maniobras: recta 1 m, 1/4 de círculo R=1 m izq./der.   -> evaluación 3
    3. Coreografía: armar pasos, cargar, ejecutar/programar  -> evaluación 6
    4. Robot: estado, secuencias cargadas, Watchdog          -> (lo mismo que el OLED)
    5. MeArm: llevar la pinza a (x, y) con cinemática inversa, y revisar ángulos

Todo lo que se manda también lo recibe el gemelo virtual (mismos tópicos).
"""

import json
from datetime import datetime, timedelta

import flet as ft

from common import config, maneuvers, motion, oled_view
from flet_ui import model
from flet_ui.mqtt_client import MqttClient

ONE_METER_DM = 10.0


def _pill(text, color):
    return ft.Container(
        content=ft.Text(text, size=13, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
        border_radius=ft.BorderRadius.all(20),
        bgcolor=color,
    )


def _card(title, controls):
    return ft.Container(
        content=ft.Column([ft.Text(title, size=16, weight=ft.FontWeight.BOLD), *controls], spacing=10),
        padding=ft.Padding.all(16),
        border_radius=ft.BorderRadius.all(12),
        bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE),
    )


def _field(label, value, width=110):
    return ft.TextField(label=label, value=str(value), width=width)


class StateFields:
    """Los 6 campos de un estado: v, w, alpha0, alpha1, alpha2, duración."""

    def __init__(self, duration=1.0):
        self.v = _field("v (dm/s)", 0)
        self.w = _field("w (°/s)", 0)
        self.a0 = _field("alpha0 (°)", 0)
        self.a1 = _field("alpha1 (°)", 0)
        self.a2 = _field("alpha2 (°)", 0)
        self.t = _field("duración (s)", duration)
        self.controls = [self.v, self.w, self.a0, self.a1, self.a2, self.t]

    def angles(self):
        return (
            model.parse_float(self.a0.value, "alpha0"),
            model.parse_float(self.a1.value, "alpha1"),
            model.parse_float(self.a2.value, "alpha2"),
        )

    def state(self):
        duration = model.parse_float(self.t.value, "duración")
        if duration <= 0:
            raise ValueError("la duración debe ser mayor que 0")
        return motion.build_state(
            model.parse_float(self.v.value, "v"),
            model.parse_float(self.w.value, "w"),
            *self.angles(),
            duration,
        )


class CoreoView:

    def __init__(self, page, send):
        self.page = page
        self._send = send
        self.choreo = model.Choreography()
        self._build()
        self._render_steps()

    # ------------------------------------------------------------ construcción

    def _build(self):
        self.broker_pill = _pill("Broker: conectando...", ft.Colors.BLUE_GREY_700)
        self.robot_pill = _pill("Robot: sin datos", ft.Colors.BLUE_GREY_700)
        self.clock_pill = _pill("Hora robot: ?", ft.Colors.BLUE_GREY_700)
        self.message = ft.Text("", size=13, color=ft.Colors.AMBER_300)
        self.sent = ft.Text("Todavía no se ha enviado nada.", size=12, selectable=True,
                            color=ft.Colors.BLUE_GREY_200)

        # 1. Estado inmediato
        self.now_fields = StateFields(duration=2.0)
        state_card = _card("1. Estado inmediato (motion/state)", [
            ft.Row(self.now_fields.controls, wrap=True, spacing=8),
            ft.Row([
                ft.Button(content="Enviar estado", icon=ft.Icons.SEND, on_click=self._on_send_state),
                ft.Button(content="Solo brazo (v=0, w=0)", icon=ft.Icons.PAN_TOOL, on_click=self._on_arm_only),
                ft.Button(content="DETENER", icon=ft.Icons.STOP, bgcolor=ft.Colors.RED_700,
                          color=ft.Colors.WHITE, on_click=self._on_stop),
            ], wrap=True, spacing=12),
            ft.Text("El brazo llega a los ángulos pedidos en la duración indicada, igual que el gemelo.",
                    size=12, color=ft.Colors.BLUE_GREY_300),
        ])

        # 2. Maniobras
        self.speed = _field("rapidez (dm/s)", config.DEFAULT_SPEED_DM_S, width=150)
        maneuvers_card = _card("2. Maniobras (radio y distancia = 1 m = 10 dm)", [
            ft.Row([
                self.speed,
                ft.Button(content="Recta 1 m", icon=ft.Icons.ARROW_UPWARD,
                          on_click=lambda e: self._maneuver(lambda v: maneuvers.straight(ONE_METER_DM, v))),
                ft.Button(content="1/4 círculo izquierda", icon=ft.Icons.TURN_LEFT,
                          on_click=lambda e: self._maneuver(
                              lambda v: maneuvers.quarter_circle(ONE_METER_DM, v, maneuvers.LEFT))),
                ft.Button(content="1/4 círculo derecha", icon=ft.Icons.TURN_RIGHT,
                          on_click=lambda e: self._maneuver(
                              lambda v: maneuvers.quarter_circle(ONE_METER_DM, v, maneuvers.RIGHT))),
            ], wrap=True, spacing=12),
            ft.Text("El brazo se mantiene en los ángulos del bloque 1.", size=12, color=ft.Colors.BLUE_GREY_300),
        ])

        # 3. Coreografía
        self.name_field = _field("nombre", self.choreo.name, width=160)
        self.step_fields = StateFields(duration=1.0)
        self.steps_list = ft.ListView(spacing=2, height=220)
        self.summary = ft.Text("", size=13)
        self.in_seconds = _field("en (s)", 10, width=90)
        self.at_time = ft.TextField(label="a las (HH:MM:SS)", width=150,
                                    value=(datetime.now() + timedelta(minutes=2)).strftime("%H:%M:00"))
        choreo_card = _card("3. Coreografía (motion/sequence)", [
            ft.Row([
                self.name_field,
                ft.Button(content="Ejemplo del enunciado", icon=ft.Icons.LIST, on_click=self._on_example),
                ft.Button(content="Limpiar", icon=ft.Icons.DELETE_SWEEP, on_click=self._on_clear),
            ], wrap=True, spacing=12),
            ft.Row(self.step_fields.controls + [
                ft.Button(content="Agregar paso", icon=ft.Icons.ADD, on_click=self._on_add_step),
            ], wrap=True, spacing=8),
            self.steps_list,
            self.summary,
            ft.Row([
                ft.Button(content="Cargar en robot", icon=ft.Icons.UPLOAD, on_click=self._on_upload),
                ft.Button(content="Ejecutar ya", icon=ft.Icons.PLAY_ARROW, on_click=self._on_run_now),
                self.in_seconds,
                ft.Button(content="Programar en N s", icon=ft.Icons.TIMER, on_click=self._on_run_in),
                self.at_time,
                ft.Button(content="Programar a esa hora", icon=ft.Icons.SCHEDULE, on_click=self._on_run_at),
                ft.Button(content="Borrar del robot", icon=ft.Icons.DELETE, on_click=self._on_delete),
            ], wrap=True, spacing=12),
            ft.Text("Ejecutar / Programar mandan primero 'create' y luego 'schedule': el robot y el "
                    "gemelo reciben la misma hora UTC y arrancan juntos. Sincronice la hora del PC "
                    "(Windows: Configuración > Hora > Sincronizar ahora).",
                    size=12, color=ft.Colors.BLUE_GREY_300),
        ])

        # 4. Robot
        self.robot_text = ft.Text("Esperando motion/status...", size=13, selectable=True)
        self.watchdog_text = ft.Text("Esperando watchdog/stats...", size=12, selectable=True,
                                     font_family="monospace")
        robot_card = _card("4. Robot", [
            self.robot_text,
            ft.Text("Watchdog (lo mismo que muestra el OLED):", size=12, color=ft.Colors.BLUE_GREY_300),
            self.watchdog_text,
        ])
        # 5. MeArm
        self.tip_x = _field("x punta (dm)", 1.2)
        self.tip_y = _field("y punta (dm)", 0.8)
        self.arm_base = _field("alpha0 (°)", 0)
        self.arm_time = _field("duración (s)", 1.5)
        self.arm_info = ft.Text("", size=13, selectable=True)
        arm_card = _card("5. Brazo MeArm (cinemática del taller 09)", [
            ft.Row([
                self.tip_x, self.tip_y, self.arm_base, self.arm_time,
                ft.Button(content="Llevar la pinza a (x, y)", icon=ft.Icons.MY_LOCATION, on_click=self._on_arm_ik),
                ft.Button(content="Revisar ángulos del bloque 1", icon=ft.Icons.RULE, on_click=self._on_arm_check),
            ], wrap=True, spacing=8),
            self.arm_info,
            ft.Text("x hacia adelante y y hacia arriba, desde el eje del hombro. La pinza del MeArm "
                    "siempre queda a %g°, así que solo se elige el punto." % model.mearm.gripper_angle_deg(),
                    size=12, color=ft.Colors.BLUE_GREY_300),
        ])
        twin_card = _card("Gemelo virtual", [
            ft.Text(model.twin_instructions(), size=13, selectable=True),
        ])

        self.page.add(
            ft.Row([ft.Text("Carrobot + MeArm", size=22, weight=ft.FontWeight.BOLD),
                    self.broker_pill, self.robot_pill, self.clock_pill], wrap=True, spacing=12),
            self.message,
            state_card,
            maneuvers_card,
            arm_card,
            choreo_card,
            ft.Row([robot_card, twin_card], wrap=True, spacing=12, vertical_alignment=ft.CrossAxisAlignment.START),
            _card("Último envío", [self.sent]),
        )

    # ------------------------------------------------------------- utilidades

    def _say(self, text):
        self.message.value = text
        self.message.update()

    def _publish(self, topic, payload, note=""):
        self._send(topic, payload)
        self.sent.value = "%s  %s\n%s" % (topic, note, json.dumps(payload))
        self.message.value = ""
        self.sent.update()
        self.message.update()

    def _try(self, action):
        try:
            action()
        except ValueError as e:
            self._say(str(e))

    # ------------------------------------------------------- 1. estado inmediato

    def _on_send_state(self, e):
        self._try(lambda: self._publish(motion.TOPIC_STATE, self.now_fields.state()))

    def _on_arm_only(self, e):
        def go():
            s = self.now_fields.state()
            s["v_dm/s"] = 0.0
            s["w_deg/s"] = 0.0
            self._publish(motion.TOPIC_STATE, s, "(solo brazo)")
        self._try(go)

    def _on_stop(self, e):
        # No hay tópico de "stop" en motionTopics.md: un estado quieto corto detiene
        # al robot Y al gemelo, y deja el brazo donde está (bloque 1).
        def go():
            self._publish(motion.TOPIC_STATE, motion.build_state(0, 0, *self.now_fields.angles(), 0.1), "(DETENER)")
        self._try(go)

    # ------------------------------------------------------------------ 5. MeArm

    def _on_arm_ik(self, e):
        def go():
            state, q1, q2 = model.arm_state_for_tip(
                model.parse_float(self.tip_x.value, "x"),
                model.parse_float(self.tip_y.value, "y"),
                model.parse_float(self.arm_base.value, "alpha0"),
                model.parse_float(self.arm_time.value, "duración"),
            )
            self._publish(motion.TOPIC_STATE, state, "(MeArm a la punta)")
            self.arm_info.value = "q1=%.1f° q2=%.1f°  ->  alpha1=%.1f° alpha2=%.1f°" % (
                q1, q2, state["alpha1_deg"], state["alpha2_deg"])
            self.arm_info.update()
        self._try(go)

    def _on_arm_check(self, e):
        def go():
            _, a1, a2 = self.now_fields.angles()
            self.arm_info.value = model.describe_arm(a1, a2)[0]
            self.arm_info.update()
        self._try(go)

    # -------------------------------------------------------------- 2. maniobras

    def _maneuver(self, build):
        def go():
            v, w, t = build(model.parse_float(self.speed.value, "rapidez"))
            state = motion.build_state(v, w, *self.now_fields.angles(), t)
            self._publish(motion.TOPIC_STATE, state, "(maniobra: %.2f s)" % t)
        self._try(go)

    # ------------------------------------------------------------ 3. coreografía

    def _render_steps(self):
        self.steps_list.controls = [
            ft.Row([
                ft.Text("Paso %d: %s" % (i + 1, model.describe_state(s)), size=13),
                ft.IconButton(icon=ft.Icons.CLOSE, icon_size=16, on_click=(lambda e, i=i: self._on_remove(i))),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            for i, s in enumerate(self.choreo.states)
        ]
        if self.choreo.states:
            x, y, th = self.choreo.end_pose()
            self.summary.value = "%d pasos, %.1f s en total. Termina en x=%.1f dm, y=%.1f dm, θ=%.0f° " \
                                 "(saliendo de (0, 0) mirando a +x)" % (len(self.choreo.states),
                                                                        self.choreo.total_s(), x, y, th)
        else:
            self.summary.value = "Sin pasos. Agregue pasos o cargue el ejemplo del enunciado."

    def _refresh_steps(self):
        self._render_steps()
        self.steps_list.update()
        self.summary.update()

    def _on_add_step(self, e):
        def go():
            self.choreo.add(self.step_fields.state())
            self._refresh_steps()
        self._try(go)

    def _on_remove(self, index):
        self.choreo.remove(index)
        self._refresh_steps()

    def _on_example(self, e):
        self.choreo.load_example()
        self.name_field.value = self.choreo.name
        self.name_field.update()
        self._refresh_steps()

    def _on_clear(self, e):
        self.choreo.clear()
        self._refresh_steps()

    def _upload(self):
        self.choreo.name = self.name_field.value.strip()
        self._publish(motion.TOPIC_SEQUENCE, self.choreo.create_payload(), "(create)")

    def _on_upload(self, e):
        self._try(self._upload)

    def _schedule(self, run_at):
        self._upload()
        payload = motion.build_schedule(self.choreo.name, run_at)
        when = "ya" if run_at == "now" else "a las %s (hora del PC) = %s UTC" % (model.local_time_text(run_at), run_at)
        self._publish(motion.TOPIC_SEQUENCE, payload, "(schedule: %s)" % when)

    def _on_run_now(self, e):
        self._try(lambda: self._schedule("now"))

    def _on_run_in(self, e):
        self._try(lambda: self._schedule(
            model.run_at_in(model.parse_float(self.in_seconds.value, "segundos"), model.utc_now_ms())))

    def _on_run_at(self, e):
        self._try(lambda: self._schedule(
            model.run_at_local_time(self.at_time.value, datetime.now().astimezone())))

    def _on_delete(self, e):
        def go():
            name = self.name_field.value.strip()
            if not name:
                raise ValueError("ponga el nombre de la coreografía a borrar")
            self._publish(motion.TOPIC_SEQUENCE, motion.build_delete(name), "(delete)")
        self._try(go)

    # ------------------------------------------------- entradas (hilo de paho)

    # En Flet 1.0, update() desde un hilo que Flet no creó no se pinta: se
    # reencola con page.run_thread(), que sí deja el contexto de la página listo.

    def _refresh(self, *controls):
        def run():
            for c in controls:
                c.update()
        self.page.run_thread(run)

    def on_link(self, connected, detail):
        self.broker_pill.content.value = "Broker: conectado" if connected else "Broker: %s" % (detail or "desconectado")
        self.broker_pill.bgcolor = ft.Colors.GREEN_700 if connected else ft.Colors.RED_700
        self._refresh(self.broker_pill)

    def on_message(self, topic, payload):
        try:
            data = json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return  # broker público: se ignora lo malformado
        local = topic[len(config.PREFIX):] if topic.startswith(config.PREFIX) else topic
        if local == motion.TOPIC_STATUS and isinstance(data, dict):
            self._show_status(data)
        elif local == motion.TOPIC_ONLINE and isinstance(data, dict):
            if data.get("online") is False:
                self.robot_pill.content.value = "Robot: desconectado"
                self.robot_pill.bgcolor = ft.Colors.RED_700
                self._refresh(self.robot_pill)
        elif local == motion.TOPIC_WATCHDOG and isinstance(data, dict):
            self.watchdog_text.value = "\n".join(oled_view.format_watchdog(data))
            self._refresh(self.watchdog_text)

    def _show_status(self, s):
        mode = s.get("mode")
        if mode == "sequence":
            pill = "Robot: '%s' paso %s/%s" % (s.get("name"), s.get("step"), s.get("steps"))
            color = ft.Colors.BLUE_700
        elif mode == "state":
            pill, color = "Robot: ejecutando estado", ft.Colors.BLUE_700
        else:
            pill, color = "Robot: quieto", ft.Colors.GREEN_700
        self.robot_pill.content.value = pill
        self.robot_pill.bgcolor = color

        synced = bool(s.get("clock_synced"))
        self.clock_pill.content.value = "Hora robot: OK (NTP)" if synced else "Hora robot: SIN sincronizar"
        self.clock_pill.bgcolor = ft.Colors.GREEN_700 if synced else ft.Colors.AMBER_800

        scheduled = s.get("scheduled") or {}
        lines = [
            "Brazo: %s°" % (s.get("arm_deg"),),
            "Secuencias cargadas: %s" % (", ".join(s.get("sequences") or []) or "ninguna"),
        ]
        for name, iso in scheduled.items():
            try:
                lines.append("Programada '%s' a las %s (hora del PC)" % (name, model.local_time_text(iso)))
            except ValueError:
                lines.append("Programada '%s': %s" % (name, iso))
        if scheduled and not synced:
            lines.append("¡Ojo! El robot no tiene la hora: arrancará cuando sincronice NTP.")
        self.robot_text.value = "\n".join(lines)
        self._refresh(self.robot_pill, self.clock_pill, self.robot_text)


def main(page: ft.Page):
    page.title = "Carrobot MeArm - %s" % config.PREFIX
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

    def send(topic, payload):
        client.publish(config.PREFIX + topic, payload)

    view = CoreoView(page, send)
    client = MqttClient(
        config.BROKER,
        config.PORT,
        [config.PREFIX + t for t in (motion.TOPIC_STATUS, motion.TOPIC_ONLINE, motion.TOPIC_WATCHDOG)],
        view.on_message,
        view.on_link,
    )
    page.on_close = lambda _: client.stop()
    client.start()


if __name__ == "__main__":
    ft.run(main)
