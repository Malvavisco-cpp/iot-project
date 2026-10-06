"""Interfaz Flet del carro: manda las maniobras del taller por MQTT.

Ejecutar desde la carpeta del taller:   python -m flet_ui.main

    - Avanzar en línea recta 1 m
    - 1/4 de círculo de 1 m de radio a la derecha
    - 1/4 de círculo de 1 m de radio a la izquierda
    - Comando manual (v, w, t), útil para calibrar
    - DETENER
"""

import json
import math

import flet as ft

from common import config, maneuvers, messages
from common.kinematics import inverse
from flet_ui.mqtt_client import MqttClient

DISTANCE_M = 1.0
RADIUS_M = 1.0


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


def describe(cmd):
    """Texto con el comando y lo que implica en cada rueda (cinemática inversa)."""
    v, w, t = cmd["v"], cmd["w"], cmd["t"]
    v_l, v_r = inverse(v, w, config.WHEEL_HALF_TRACK_M)
    return (
        f"v = {v:.3f} m/s   w = {w:.3f} rad/s   t = {t:.2f} s\n"
        f"v_l = {v_l:.3f} m/s   v_r = {v_r:.3f} m/s   (d = {config.WHEEL_HALF_TRACK_M} m)\n"
        f"recorre {v * t:.2f} m y gira {math.degrees(w * t):.1f}°"
    )


class CarView:

    def __init__(self, page, send):
        self.page = page
        self._send = send
        self._build()

    # ------------------------------------------------------------ construcción

    def _build(self):
        self.broker_pill = _pill("Broker: conectando...", ft.Colors.BLUE_GREY_700)
        self.car_pill = _pill("Carro: sin datos", ft.Colors.BLUE_GREY_700)

        self.speed_field = ft.TextField(label="Rapidez v (m/s)", value=str(config.DEFAULT_SPEED_M_S), width=180)

        straight_btn = ft.Button(
            content=f"Línea recta {DISTANCE_M:g} m",
            icon=ft.Icons.ARROW_UPWARD,
            on_click=lambda e: self._maneuver(lambda v: maneuvers.straight(DISTANCE_M, v)),
        )
        right_btn = ft.Button(
            content=f"1/4 círculo R={RADIUS_M:g} m a la derecha",
            icon=ft.Icons.TURN_RIGHT,
            on_click=lambda e: self._maneuver(lambda v: maneuvers.quarter_circle(RADIUS_M, v, maneuvers.RIGHT)),
        )
        left_btn = ft.Button(
            content=f"1/4 círculo R={RADIUS_M:g} m a la izquierda",
            icon=ft.Icons.TURN_LEFT,
            on_click=lambda e: self._maneuver(lambda v: maneuvers.quarter_circle(RADIUS_M, v, maneuvers.LEFT)),
        )

        self.v_field = ft.TextField(label="v (m/s)", value="0.2", width=120)
        self.w_field = ft.TextField(label="w (rad/s)", value="0", width=120)
        self.t_field = ft.TextField(label="t (s)", value="5", width=120)
        manual_btn = ft.Button(content="Enviar", icon=ft.Icons.SEND, on_click=self._on_manual_click)

        stop_btn = ft.Button(
            content="DETENER",
            icon=ft.Icons.STOP,
            bgcolor=ft.Colors.RED_700,
            color=ft.Colors.WHITE,
            on_click=self._on_stop_click,
        )

        self.last_text = ft.Text("Todavía no se ha enviado nada.", size=14)
        self.status_text = ft.Text("", size=13, color=ft.Colors.AMBER_300)

        self.page.add(
            ft.Row(
                [ft.Text("Carro diferencial", size=22, weight=ft.FontWeight.BOLD), self.broker_pill, self.car_pill],
                wrap=True,
                spacing=12,
            ),
            _card("Maniobras", [self.speed_field, ft.Row([straight_btn, right_btn, left_btn], wrap=True, spacing=12)]),
            _card("Comando manual", [ft.Row([self.v_field, self.w_field, self.t_field, manual_btn], wrap=True, spacing=12)]),
            stop_btn,
            _card("Último comando", [self.last_text]),
            self.status_text,
        )

    # ---------------------------------------------------------------- envío

    def _send_cmd(self, cmd):
        self._send(messages.TOPIC_CMD, cmd)
        self.last_text.value = describe(cmd)
        self.status_text.value = ""
        self.last_text.update()
        self.status_text.update()

    def _error(self, text):
        self.status_text.value = text
        self.status_text.update()

    def _maneuver(self, build):
        try:
            cmd = build(float(self.speed_field.value))
        except ValueError as e:
            self._error(f"Revise la rapidez: {e}")
            return
        self._send_cmd(cmd)

    def _on_manual_click(self, e):
        try:
            cmd = messages.build_cmd(float(self.v_field.value), float(self.w_field.value), float(self.t_field.value))
            messages.validate_cmd(cmd)
        except ValueError as e:
            self._error(f"Comando inválido: {e}")
            return
        self._send_cmd(cmd)

    def _on_stop_click(self, e):
        self._send(messages.TOPIC_STOP, {})
        self.last_text.value = "DETENER enviado."
        self.last_text.update()

    # ------------------------------------------------- entradas (hilo de paho)

    # En Flet 1.0, update() desde un hilo que Flet no creó no se pinta: se
    # reencola con page.run_thread(), que sí deja el contexto de la página listo.

    def on_link(self, connected, detail):
        self.broker_pill.content.value = "Broker: conectado" if connected else f"Broker: {detail or 'desconectado'}"
        self.broker_pill.bgcolor = ft.Colors.GREEN_700 if connected else ft.Colors.RED_700
        self.page.run_thread(self.broker_pill.update)

    def on_message(self, topic, payload):
        if topic != config.PREFIX + messages.TOPIC_STATE:
            return
        try:
            state = json.loads(payload.decode("utf-8"))
            messages.validate_state(state)
        except (ValueError, UnicodeDecodeError):
            return  # broker público: se ignora lo malformado
        if state["moving"]:
            self.car_pill.content.value = f"Carro: moviéndose ({state['t']:.1f} s)"
            self.car_pill.bgcolor = ft.Colors.BLUE_700
        else:
            self.car_pill.content.value = "Carro: detenido"
            self.car_pill.bgcolor = ft.Colors.GREEN_700
        self.page.run_thread(self.car_pill.update)


def main(page: ft.Page):
    page.title = "Carro diferencial"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

    def send(topic, payload):
        client.publish(config.PREFIX + topic, payload)

    view = CarView(page, send)
    client = MqttClient(
        config.BROKER,
        config.PORT,
        [config.PREFIX + messages.TOPIC_STATE],
        view.on_message,
        view.on_link,
    )

    page.on_close = lambda _: client.stop()
    client.start()


if __name__ == "__main__":
    ft.run(main)
