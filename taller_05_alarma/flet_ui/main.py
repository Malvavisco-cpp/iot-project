"""Interfaz Flet de la alarma: un monitor en tiempo real del Pico.

Ejecutar desde la carpeta del taller:   python -m flet_ui.main

Mayormente solo muestra: la clave se digita únicamente en el control IR, así que
esta ventana no puede armar ni desarmar la alarma, y si se cierra (o el PC se
apaga) la alarma sigue funcionando en el Pico. La única acción que sí envía es
el botón "simular puerta", pensado para el Pico virtual (`tools/pico_simulator.py`):
contra el hardware real no tiene efecto, porque ahí la puerta es un sensor físico
y la Pico real no escucha comandos por MQTT.
"""

import threading
import time
from typing import Callable

import flet as ft

from common import config, messages
from common.alarm import STATE_ARMED, STATE_DISARMED, STATE_TRIGGERED
from flet_ui.monitor import (
    LEVEL_DANGER,
    LEVEL_INFO,
    LEVEL_SUCCESS,
    LEVEL_WARNING,
    LINK_OFFLINE,
    LINK_ONLINE,
    LINK_SILENT,
    LINK_WAITING,
    STATE_UNKNOWN,
    AlarmMonitor,
    detail_for,
    headline_for,
)
from flet_ui.mqtt_client import MqttClient

BLINK_PERIOD_S = 0.5

# estado -> (color, icono). El disparo alterna entre dos rojos (parpadeo).
STATE_LOOK = {
    STATE_UNKNOWN: (ft.Colors.BLUE_GREY_700, ft.Icons.HELP_OUTLINE),
    STATE_DISARMED: (ft.Colors.GREEN_700, ft.Icons.LOCK_OPEN),
    STATE_ARMED: (ft.Colors.BLUE_700, ft.Icons.LOCK),
    STATE_TRIGGERED: (ft.Colors.RED_600, ft.Icons.NOTIFICATIONS_ACTIVE),
}
TRIGGERED_ALT_COLOR = ft.Colors.RED_900

LEVEL_COLOR = {
    LEVEL_INFO: ft.Colors.BLUE_GREY_200,
    LEVEL_SUCCESS: ft.Colors.GREEN_300,
    LEVEL_WARNING: ft.Colors.AMBER_300,
    LEVEL_DANGER: ft.Colors.RED_300,
}

LINK_TEXT = {
    LINK_WAITING: ("Pico: esperando datos", ft.Colors.BLUE_GREY_700),
    LINK_ONLINE: ("Pico: en línea", ft.Colors.GREEN_700),
    LINK_OFFLINE: ("Pico: desconectado", ft.Colors.RED_700),
    LINK_SILENT: ("Pico: sin señal", ft.Colors.AMBER_800),
}


def _pill(text: str, color: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(text, size=13, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
        border_radius=ft.BorderRadius.all(20),
        bgcolor=color,
    )


def _info_card(icon: str, title: str) -> tuple[ft.Container, ft.Icon, ft.Text]:
    """Tarjeta pequeña con icono, título y un valor que la vista actualiza."""
    icon_control = ft.Icon(icon, size=28)
    value = ft.Text("-", size=18, weight=ft.FontWeight.BOLD)
    card = ft.Container(
        content=ft.Row(
            [
                icon_control,
                ft.Column([ft.Text(title, size=12, color=ft.Colors.BLUE_GREY_300), value], spacing=2),
            ],
            spacing=12,
        ),
        padding=ft.Padding.all(16),
        border_radius=ft.BorderRadius.all(12),
        bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE),
        width=250,
    )
    return card, icon_control, value


class AlarmView:
    """Construye la pantalla y la redibuja a partir de un AlarmMonitor."""

    def __init__(
        self,
        page: ft.Page,
        monitor: AlarmMonitor,
        simulate_door: Callable[[bool], None] | None = None,
    ):
        self.page = page
        self.monitor = monitor
        self._simulate_door = simulate_door
        self._lock = threading.RLock()
        self._blink = False
        self._running = True
        self._broker_ok = False
        self._broker_detail = "conectando..."
        self._log_version_drawn = -1
        self._build()
        self.render()

    # ------------------------------------------------------------ construcción

    def _build(self) -> None:
        self.broker_pill = _pill("Broker: conectando...", ft.Colors.BLUE_GREY_700)
        self.pico_pill = _pill(*LINK_TEXT[LINK_WAITING])

        self.status_icon = ft.Icon(ft.Icons.HELP_OUTLINE, size=72, color=ft.Colors.WHITE)
        self.status_headline = ft.Text("", size=30, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
        self.status_detail = ft.Text("", size=15, color=ft.Colors.WHITE_70)
        self.key_dots = [
            ft.Icon(ft.Icons.CIRCLE_OUTLINED, size=18, color=ft.Colors.WHITE)
            for _ in range(config.PASSWORD_LENGTH)
        ]
        self.status_card = ft.Container(
            content=ft.Row(
                [
                    self.status_icon,
                    ft.Column(
                        [
                            self.status_headline,
                            self.status_detail,
                            ft.Row([ft.Text("Clave:", size=13, color=ft.Colors.WHITE_70), *self.key_dots], spacing=6),
                        ],
                        spacing=6,
                    ),
                ],
                spacing=24,
            ),
            padding=ft.Padding.all(24),
            border_radius=ft.BorderRadius.all(16),
            animate=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT),
        )

        self.banner = ft.Container(
            content=ft.Text(
                "Sin conexión con el Pico. Lo que ve aquí puede estar desactualizado; "
                "la alarma sigue funcionando en el dispositivo.",
                size=13,
                color=ft.Colors.WHITE,
            ),
            padding=ft.Padding.all(12),
            border_radius=ft.BorderRadius.all(10),
            bgcolor=ft.Colors.AMBER_900,
            visible=False,
        )

        door_card, self.door_icon, self.door_value = _info_card(ft.Icons.DOOR_FRONT_DOOR, "PUERTA 1")
        self.door_sim_open_btn = ft.ElevatedButton(
            "Abrir", icon=ft.Icons.LOCK_OPEN, on_click=lambda e: self._on_simulate_door(True)
        )
        self.door_sim_close_btn = ft.ElevatedButton(
            "Cerrar", icon=ft.Icons.LOCK, on_click=lambda e: self._on_simulate_door(False)
        )
        door_column = ft.Column(
            [
                door_card,
                ft.Text("Simular puerta (solo Pico virtual):", size=11, color=ft.Colors.BLUE_GREY_300),
                ft.Row([self.door_sim_open_btn, self.door_sim_close_btn], spacing=8),
            ],
            spacing=6,
        )
        attempts_card, self.attempts_icon, self.attempts_value = _info_card(
            ft.Icons.PASSWORD, "CLAVES INCORRECTAS"
        )
        system_card, self.system_icon, self.system_value = _info_card(ft.Icons.MEMORY, "SISTEMA (Pico)")
        self.system_value.size = 13

        self.log_list = ft.ListView(spacing=2, height=260)
        log_card = ft.Container(
            content=ft.Column(
                [
                    ft.Row([ft.Icon(ft.Icons.HISTORY, size=20), ft.Text("Bitácora", size=16, weight=ft.FontWeight.BOLD)]),
                    self.log_list,
                ],
                spacing=8,
            ),
            padding=ft.Padding.all(16),
            border_radius=ft.BorderRadius.all(12),
            bgcolor=ft.Colors.with_opacity(0.08, ft.Colors.WHITE),
        )

        self.page.add(
            ft.Row(
                [ft.Text("Control de acceso · Alarma", size=22, weight=ft.FontWeight.BOLD), self.broker_pill, self.pico_pill],
                wrap=True,
                spacing=12,
                run_spacing=8,
            ),
            self.banner,
            self.status_card,
            ft.Row([door_column, attempts_card, system_card], wrap=True, spacing=12, run_spacing=12),
            log_card,
        )

    # ---------------------------------------------------------------- dibujado

    def render(self) -> None:
        with self._lock:
            status = self.monitor.status
            link = self.monitor.link()
            stale = link in (LINK_OFFLINE, LINK_SILENT)

            color, icon = STATE_LOOK.get(status.state, STATE_LOOK[STATE_UNKNOWN])
            if status.state == STATE_TRIGGERED and self._blink:
                color = TRIGGERED_ALT_COLOR
            self.status_card.bgcolor = color
            self.status_card.opacity = 0.55 if stale else 1.0
            self.status_icon.icon = icon
            self.status_headline.value = headline_for(status)
            self.status_detail.value = detail_for(status)
            for index, dot in enumerate(self.key_dots):
                dot.icon = ft.Icons.CIRCLE if index < status.keys_entered else ft.Icons.CIRCLE_OUTLINED

            self.banner.visible = stale

            broker_text = "Broker: conectado" if self._broker_ok else f"Broker: {self._broker_detail}"
            self.broker_pill.content.value = broker_text
            self.broker_pill.bgcolor = ft.Colors.GREEN_700 if self._broker_ok else ft.Colors.RED_700
            pico_text, pico_color = LINK_TEXT[link]
            self.pico_pill.content.value = pico_text
            self.pico_pill.bgcolor = pico_color

            self._render_cards()
            self._render_log()
            self.page.update()

    def _render_cards(self) -> None:
        status = self.monitor.status
        known = status.state != STATE_UNKNOWN

        if not known:
            self.door_value.value = "-"
            self.door_icon.color = ft.Colors.BLUE_GREY_300
        elif status.door_open:
            self.door_value.value = "ABIERTA"
            self.door_icon.color = ft.Colors.AMBER_400
        else:
            self.door_value.value = "CERRADA"
            self.door_icon.color = ft.Colors.GREEN_400

        self.attempts_value.value = str(status.wrong_attempts) if known else "-"
        self.attempts_icon.color = ft.Colors.AMBER_400 if status.wrong_attempts else ft.Colors.BLUE_GREY_300

        system = self.monitor.system
        parts = []
        if known:
            parts.append(f"activo {status.uptime_s // 60} min")
        if system.mem_free_bytes is not None:
            parts.append(f"RAM libre {system.mem_free_bytes // 1024} KB")
        if system.rssi is not None:
            parts.append(f"WiFi {system.rssi} dBm")
        if system.temperature_c is not None:
            parts.append(f"{system.temperature_c:.1f} °C")
        self.system_value.value = "\n".join(parts) if parts else "-"

    def _render_log(self) -> None:
        # Se reconstruye solo cuando hay eventos nuevos (el parpadeo redibuja 2 veces por segundo).
        if self._log_version_drawn == self.monitor.log_version:
            return
        self._log_version_drawn = self.monitor.log_version
        self.log_list.controls = [
            ft.Text(
                f"{time.strftime('%H:%M:%S', time.localtime(entry.received_at))}   {entry.text}",
                size=13,
                color=LEVEL_COLOR[entry.level],
            )
            for entry in self.monitor.log
        ]

    # ------------------------------------------------------ entradas (hilos MQTT)

    def on_message(self, topic: str, payload: bytes) -> None:
        with self._lock:
            changed = self.monitor.handle_message(topic, payload)
        if changed:
            self.render()

    def on_link(self, connected: bool, detail: str) -> None:
        with self._lock:
            self._broker_ok = connected
            self._broker_detail = detail or "desconectado"
        self.render()

    # -------------------------------------------------------- salida (botón)

    def _on_simulate_door(self, is_open: bool) -> None:
        if self._simulate_door is not None:
            self._simulate_door(is_open)

    # -------------------------------------------------------------- animación

    def run_ticker(self) -> None:
        """Hilo de fondo: hace parpadear la alarma y detecta cuando el Pico deja de reportar."""
        while self._running:
            time.sleep(BLINK_PERIOD_S)
            try:
                with self._lock:
                    self._blink = not self._blink
                self.render()
            except Exception:
                self._running = False  # la ventana ya se cerró

    def stop(self) -> None:
        self._running = False


def main(page: ft.Page) -> None:
    page.title = "Alarma · Control de acceso"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

    monitor = AlarmMonitor(config.PREFIX)

    def simulate_door(is_open: bool) -> None:
        client.publish(config.PREFIX + messages.TOPIC_DOOR_SIM, messages.build_door_set(is_open))

    view = AlarmView(page, monitor, simulate_door=simulate_door)
    client = MqttClient(config.BROKER, config.PORT, monitor.topics, view.on_message, view.on_link)

    def on_close(_) -> None:
        view.stop()
        client.stop()

    page.on_close = on_close
    client.start()
    threading.Thread(target=view.run_ticker, daemon=True).start()


if __name__ == "__main__":
    ft.run(main)
