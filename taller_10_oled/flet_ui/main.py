"""Interfaz Flet de la OLED: manda texto a la pantalla por oled/text.

Ejecutar desde la carpeta del taller:   python -m flet_ui.main

    - Texto, posición (x, y) y color
    - "Borrar antes de escribir" (clear)
    - Borrar pantalla
"""

import flet as ft

from common import config, messages
from flet_ui.mqtt_client import MqttClient


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


class OledView:

    def __init__(self, page, send):
        self.page = page
        self._send = send
        self._build()

    # ------------------------------------------------------------ construcción

    def _build(self):
        self.broker_pill = _pill("Broker: conectando...", ft.Colors.BLUE_GREY_700)

        self.text_field = ft.TextField(label="Texto", value="Hola OLED", width=320)
        self.x_field = ft.TextField(label=f"x (0-{config.OLED_WIDTH - 1})", value="0", width=120)
        self.y_field = ft.TextField(label=f"y (0-{config.OLED_HEIGHT - 1})", value="0", width=120)
        self.color_dropdown = ft.Dropdown(
            label="Color",
            value="1",
            width=160,
            options=[ft.dropdown.Option("1", "1 (encendido)"), ft.dropdown.Option("0", "0 (borra)")],
        )
        self.clear_checkbox = ft.Checkbox(label="Borrar la pantalla antes de escribir (clear)", value=False)
        send_btn = ft.Button(content="Enviar", icon=ft.Icons.SEND, on_click=self._on_send_click)
        clear_btn = ft.Button(
            content="Borrar pantalla",
            icon=ft.Icons.CLEAR_ALL,
            bgcolor=ft.Colors.RED_700,
            color=ft.Colors.WHITE,
            on_click=self._on_clear_click,
        )

        self.last_text = ft.Text("Todavía no se ha enviado nada.", size=14)
        self.status_text = ft.Text("", size=13, color=ft.Colors.AMBER_300)

        self.page.add(
            ft.Row([ft.Text("Pantalla OLED", size=22, weight=ft.FontWeight.BOLD), self.broker_pill], wrap=True, spacing=12),
            _card(
                "Escribir texto",
                [
                    self.text_field,
                    ft.Row([self.x_field, self.y_field, self.color_dropdown], wrap=True, spacing=12),
                    self.clear_checkbox,
                    ft.Row([send_btn, clear_btn], wrap=True, spacing=12),
                    ft.Text(
                        f"La fuente mide {messages.CHAR_PX}x{messages.CHAR_PX} px: "
                        f"{config.OLED_WIDTH // messages.CHAR_PX} columnas (x múltiplo de 8) y "
                        f"{config.OLED_HEIGHT // messages.CHAR_PX} renglones (y múltiplo de 8).",
                        size=12,
                        italic=True,
                    ),
                ],
            ),
            _card("Último mensaje", [self.last_text]),
            self.status_text,
        )

    # ---------------------------------------------------------------- envío

    def _error(self, text):
        self.status_text.value = text
        self.status_text.update()

    def _send_text(self, msg):
        self._send(messages.TOPIC_TEXT, msg)
        self.last_text.value = f"{messages.TOPIC_TEXT}  {msg}"
        self.status_text.value = ""
        self.last_text.update()
        self.status_text.update()

    def _on_send_click(self, e):
        try:
            msg = messages.build_text(
                self.text_field.value,
                int(self.x_field.value),
                int(self.y_field.value),
                int(self.color_dropdown.value),
                self.clear_checkbox.value,
            )
            messages.validate_text(msg)
        except ValueError as err:
            self._error(f"Mensaje inválido: {err}")
            return
        self._send_text(msg)

    def _on_clear_click(self, e):
        self._send_text(messages.build_text("", clear=True))

    # ------------------------------------------------- entradas (hilo de paho)

    # En Flet 1.0, update() desde un hilo que Flet no creó no se pinta: se
    # reencola con page.run_thread(), que sí deja el contexto de la página listo.

    def on_link(self, connected, detail):
        self.broker_pill.content.value = "Broker: conectado" if connected else f"Broker: {detail or 'desconectado'}"
        self.broker_pill.bgcolor = ft.Colors.GREEN_700 if connected else ft.Colors.RED_700
        self.page.run_thread(self.broker_pill.update)

    def on_message(self, topic, payload):
        pass  # la OLED no publica nada: esta app solo escribe


def main(page: ft.Page):
    page.title = "Pantalla OLED"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

    def send(topic, payload):
        client.publish(config.PREFIX + topic, payload)

    view = OledView(page, send)
    client = MqttClient(config.BROKER, config.PORT, [], view.on_message, view.on_link)

    page.on_close = lambda _: client.stop()
    client.start()


if __name__ == "__main__":
    ft.run(main)
