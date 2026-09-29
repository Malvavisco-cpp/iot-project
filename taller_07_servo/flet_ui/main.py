"""Interfaz Flet: arma una secuencia de pasos (ángulo / esperar) y la ejecuta
contra el servo del Pico por MQTT.

Ejecutar desde la carpeta del taller:   python -m flet_ui.main

Formato de pasos sin estandarizar todavía (queda para la próxima clase): por
ahora son solo "poner el servo a X grados" y "esperar N segundos", en el
orden en que se agregan.
"""

import threading
import time

import flet as ft

from common import config, messages
from flet_ui.mqtt_client import MqttClient
from flet_ui.steps import STEP_ANGLE, StepSequence


def _pill(text: str, color: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(text, size=13, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
        border_radius=ft.BorderRadius.all(20),
        bgcolor=color,
    )


class StepsView:

    def __init__(self, page: ft.Page, publish_angle):
        self.page = page
        self._publish_angle = publish_angle
        self.sequence = StepSequence()
        self._lock = threading.RLock()
        self._running = False
        self._cancel = False
        self._broker_ok = False
        self._build()
        self._render_steps()

    # ------------------------------------------------------------ construcción

    def _build(self) -> None:
        self.broker_pill = _pill("Broker: conectando...", ft.Colors.BLUE_GREY_700)

        self.kind_dropdown = ft.Dropdown(
            label="Tipo de paso",
            width=160,
            value=STEP_ANGLE,
            options=[
                ft.dropdown.Option(STEP_ANGLE, "Ángulo"),
                ft.dropdown.Option("wait", "Esperar"),
            ],
        )
        self.value_field = ft.TextField(label="Valor (° o s)", width=140, value="0")
        self.add_button = ft.Button(content="Agregar paso", on_click=self._on_add_click)

        self.steps_list = ft.ListView(spacing=4, height=260)

        self.run_button = ft.Button(content="Ejecutar", icon=ft.Icons.PLAY_ARROW, on_click=self._on_run_click)
        self.stop_button = ft.Button(content="Detener", icon=ft.Icons.STOP, on_click=self._on_stop_click, disabled=True)
        self.clear_button = ft.Button(content="Limpiar", icon=ft.Icons.DELETE_SWEEP, on_click=self._on_clear_click)

        self.status_text = ft.Text("Listo.", size=13, color=ft.Colors.BLUE_GREY_300)

        self.page.add(
            ft.Row(
                [ft.Text("Control de servo · Pasos", size=22, weight=ft.FontWeight.BOLD), self.broker_pill],
                spacing=12,
            ),
            ft.Row([self.kind_dropdown, self.value_field, self.add_button], spacing=12),
            ft.Container(
                content=ft.Column([ft.Text("Secuencia", size=16, weight=ft.FontWeight.BOLD), self.steps_list], spacing=8),
                padding=ft.Padding.all(16),
                border_radius=ft.BorderRadius.all(12),
                bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE),
            ),
            ft.Row([self.run_button, self.stop_button, self.clear_button], spacing=12),
            self.status_text,
        )

    # ---------------------------------------------------------------- pasos

    def _on_add_click(self, e) -> None:
        try:
            value = float(self.value_field.value)
        except (TypeError, ValueError):
            self.status_text.value = "El valor debe ser un número."
            self.status_text.update()
            return
        if self.kind_dropdown.value == STEP_ANGLE:
            self.sequence.add_angle(value)
        else:
            self.sequence.add_wait(value)
        self.status_text.value = "Listo."
        self._render_steps()
        self.status_text.update()
        self.steps_list.update()

    def _on_remove_click(self, index: int) -> None:
        self.sequence.remove(index)
        self._render_steps()
        self.steps_list.update()

    def _on_clear_click(self, e) -> None:
        if self._running:
            return
        self.sequence.clear()
        self._render_steps()
        self.steps_list.update()

    def _render_steps(self) -> None:
        self.steps_list.controls = [
            ft.Row(
                [
                    ft.Text(f"Paso {index + 1}: {step.describe()}", size=14),
                    ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        icon_size=16,
                        on_click=(lambda e, i=index: self._on_remove_click(i)),
                        disabled=self._running,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
            for index, step in enumerate(self.sequence.steps)
        ]

    # ------------------------------------------------------------ ejecución

    def _on_run_click(self, e) -> None:
        with self._lock:
            if self._running or not self.sequence.steps:
                return
            self._running = True
            self._cancel = False
        self.run_button.disabled = True
        self.stop_button.disabled = False
        self.status_text.value = "Ejecutando..."
        self.run_button.update()
        self.stop_button.update()
        self.status_text.update()
        self.page.run_thread(self._run_sequence)

    def _on_stop_click(self, e) -> None:
        with self._lock:
            self._cancel = True

    def _run_sequence(self) -> None:
        def set_angle(angle: float) -> None:
            self._publish_angle(angle)

        def wait(seconds: float) -> None:
            time.sleep(max(0.0, seconds))

        def on_step(index, step) -> None:
            self.status_text.value = f"Paso {index + 1}/{len(self.sequence.steps)}: {step.describe()}"
            self.status_text.update()

        def is_cancelled() -> bool:
            with self._lock:
                return self._cancel

        self.sequence.run(set_angle, wait, on_step=on_step, is_cancelled=is_cancelled)

        with self._lock:
            cancelled = self._cancel
            self._running = False
            self._cancel = False
        self.status_text.value = "Detenido." if cancelled else "Secuencia terminada."
        self.run_button.disabled = False
        self.stop_button.disabled = True
        self._render_steps()
        self.status_text.update()
        self.run_button.update()
        self.stop_button.update()
        self.steps_list.update()

    # -------------------------------------------------------------- enlace

    def on_link(self, connected: bool, detail: str) -> None:
        self._broker_ok = connected
        self.broker_pill.content.value = "Broker: conectado" if connected else f"Broker: {detail or 'desconectado'}"
        self.broker_pill.bgcolor = ft.Colors.GREEN_700 if connected else ft.Colors.RED_700
        self.page.run_thread(self.broker_pill.update)


def main(page: ft.Page) -> None:
    page.title = "Control de servo · Pasos"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

    def publish_angle(angle: float) -> None:
        client.publish(config.PREFIX + messages.TOPIC_SERVO_ANGLE, messages.build_angle(angle))

    view = StepsView(page, publish_angle)
    client = MqttClient(config.BROKER, config.PORT, view.on_link)

    def on_close(_) -> None:
        client.stop()

    page.on_close = on_close
    client.start()


if __name__ == "__main__":
    ft.run(main)
