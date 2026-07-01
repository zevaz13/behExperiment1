"""Main window and top-level pages for the configurableFirmware GUI.

Navigation: Connect -> ModeSelect -> per-mode view.
- Solid has no config screen: MainWindow sends MODE (+ SET hue) + START
  immediately and shows SolidView.
- Linear/Grid/Behavioral send MODE then GET, and once the full settings
  response arrives, show that mode's config screen (Start). The config
  screen's Start emits start_requested; MainWindow sends the changed-param
  SET batch + START and switches to the session screen.
Back from any per-mode view sends STOP and returns to ModeSelect.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
import serial

from behavioral_view import BehavioralConfigPage, BehavioralSessionPage
from grid_view import GridConfigPage, GridSessionPage
from linear_view import LinearConfigPage, LinearSessionPage
from protocol import build_mode_command, build_set_command, parse_get_response
from serial_link import SerialLink, find_teensy_port, list_all_ports
from solid_view import SolidView

AUTO_DETECT_RETRY_MS = 500
AUTO_DETECT_ATTEMPTS_BEFORE_FALLBACK = 6

MODES = ("SOLID", "LINEAR", "GRID", "BEHAVIORAL")
MODE_LABELS = {
    "SOLID": "Solid",
    "LINEAR": "Linear (Steps)",
    "GRID": "Grid",
    "BEHAVIORAL": "Behavioral",
}

_ACCENT = "#ff7256"
_STYLE = f"""\
* {{ background-color: #0a0a0a; color: #d0d0d0; }}
QPushButton {{
    border: 1px solid {_ACCENT}; color: {_ACCENT};
    background: #141414; padding: 5px 14px;
}}
QPushButton:hover {{ background: #1e1e1e; }}
QPushButton:disabled {{ border-color: #333; color: #444; background: #0f0f0f; }}
QLineEdit, QComboBox, QSpinBox {{
    background: #141414; border: 1px solid #333; padding: 2px;
}}
QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {_ACCENT}; }}
QCheckBox::indicator:checked {{ background: {_ACCENT}; }}
"""


# ---------------------------------------------------------------------------
# ConnectPage
# ---------------------------------------------------------------------------

class ConnectPage(QWidget):
    """Auto-detects the Teensy; falls back to manual port selection.
    Confirms identity by sending 'GET' and waiting for a mode= response line.
    """

    connected = Signal(SerialLink)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._link: SerialLink | None = None
        self._attempts = 0
        self._get_buffer: list[str] = []

        self._status_label = QLabel("Searching for Teensy...")
        self._port_combo = QComboBox()
        self._connect_button = QPushButton("Connect")
        self._connect_button.clicked.connect(self._connect_to_selected)
        self._port_combo.setVisible(False)
        self._connect_button.setVisible(False)

        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(self._status_label)
        manual_row = QHBoxLayout()
        manual_row.addWidget(self._port_combo)
        manual_row.addWidget(self._connect_button)
        layout.addLayout(manual_row)
        layout.addStretch()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._try_auto_detect)
        self._timer.start(AUTO_DETECT_RETRY_MS)

    def _try_auto_detect(self) -> None:
        self._attempts += 1
        port = find_teensy_port()
        if port is not None:
            self._timer.stop()
            self._open(port)
            return
        if self._attempts >= AUTO_DETECT_ATTEMPTS_BEFORE_FALLBACK:
            self._show_manual_fallback()

    def _show_manual_fallback(self) -> None:
        self._timer.stop()
        self._status_label.setText("Couldn't find a Teensy automatically. Select a port:")
        self._port_combo.clear()
        self._port_combo.addItems(list_all_ports())
        self._port_combo.setVisible(True)
        self._connect_button.setVisible(True)

    def _connect_to_selected(self) -> None:
        port = self._port_combo.currentText()
        if port:
            self._open(port)

    def _open(self, port: str) -> None:
        self._status_label.setText(f"Connecting to {port}...")
        try:
            self._link = SerialLink(port)
        except serial.SerialException as exc:
            self._status_label.setText(f"Couldn't open {port}: {exc}")
            self._show_manual_fallback()
            return
        self._get_buffer.clear()
        self._link.line_received.connect(self._on_line)
        self._link.connection_lost.connect(self._on_connection_lost)
        self._link.start()
        self._link.send("GET")
        self._status_label.setText(f"Connected to {port}. Verifying firmware...")

    def _on_line(self, line: str) -> None:
        self._get_buffer.append(line)
        settings = parse_get_response(self._get_buffer)
        if settings is not None and self._link is not None:
            link = self._link
            link.line_received.disconnect(self._on_line)
            try:
                link.connection_lost.disconnect(self._on_connection_lost)
            except (RuntimeError, TypeError):
                pass
            self._get_buffer.clear()
            self._link = None  # ownership transferred to MainWindow
            self.connected.emit(link)

    def _on_connection_lost(self, message: str) -> None:
        if self._link is not None:
            try:
                self._link.line_received.disconnect(self._on_line)
            except (RuntimeError, TypeError):
                pass
            self._link.close()
        self._status_label.setText(f"Connection lost: {message}")
        self._link = None
        self._attempts = 0
        self._get_buffer.clear()
        self._timer.start(AUTO_DETECT_RETRY_MS)

    def restart(self) -> None:
        """Reset to a fresh search (used after a mid-session disconnect)."""
        self._link = None
        self._attempts = 0
        self._get_buffer.clear()
        self._status_label.setText("Searching for Teensy...")
        self._port_combo.setVisible(False)
        self._connect_button.setVisible(False)
        self._timer.start(AUTO_DETECT_RETRY_MS)

    def close_link(self) -> None:
        """Close a link still owned by this page (not yet handed off)."""
        if self._link is not None:
            self._link.close()
            self._link = None


# ---------------------------------------------------------------------------
# ModeSelectPage
# ---------------------------------------------------------------------------

class ModeSelectPage(QWidget):
    """Sub-mode selector: SOLID / LINEAR / GRID / BEHAVIORAL.

    Solid has no config screen (per design), so its hue choice is made here,
    before the mode is entered. Linear/Grid ask for hue on their own config
    screens instead; Behavioral doesn't support hue at all.
    """

    mode_chosen = Signal(str, bool)  # mode, hue_enabled (hue only meaningful for SOLID)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._hue_checkbox = QCheckBox("Enable hue sensor")

        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(QLabel("Choose an experiment mode:"))
        for mode in MODES:
            row = QHBoxLayout()
            button = QPushButton(MODE_LABELS[mode])
            button.clicked.connect(lambda checked=False, m=mode: self._choose(m))
            row.addWidget(button)
            if mode == "SOLID":
                row.addWidget(self._hue_checkbox)
            layout.addLayout(row)
        layout.addStretch()

    def _choose(self, mode: str) -> None:
        self.mode_chosen.emit(mode, self._hue_checkbox.isChecked())


# ---------------------------------------------------------------------------
# MainWindow
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("configurableFirmware")

        self._connect_page = ConnectPage()
        self._mode_select_page = ModeSelectPage()
        self._solid_view = SolidView()
        self._linear_config_page = LinearConfigPage()
        self._linear_session_page = LinearSessionPage()
        self._grid_config_page = GridConfigPage()
        self._grid_session_page = GridSessionPage()
        self._behavioral_config_page = BehavioralConfigPage()
        self._behavioral_session_page = BehavioralSessionPage()

        self._stack = QStackedWidget()
        for page in (
            self._connect_page,
            self._mode_select_page,
            self._solid_view,
            self._linear_config_page,
            self._linear_session_page,
            self._grid_config_page,
            self._grid_session_page,
            self._behavioral_config_page,
            self._behavioral_session_page,
        ):
            self._stack.addWidget(page)
        self.setCentralWidget(self._stack)

        self._link: SerialLink | None = None
        self._active_page: QWidget | None = None
        self._get_buffer: list[str] = []
        self._pending_config_mode: str | None = None

        # mode -> (config page, session page, start handler)
        self._config_pages = {
            "LINEAR": self._linear_config_page,
            "GRID": self._grid_config_page,
            "BEHAVIORAL": self._behavioral_config_page,
        }

        self._connect_page.connected.connect(self._on_connected)
        self._mode_select_page.mode_chosen.connect(self._on_mode_chosen)
        self._solid_view.back_requested.connect(self._on_back_requested)
        self._linear_config_page.start_requested.connect(self._on_linear_start)
        self._linear_config_page.back_requested.connect(self._on_back_requested)
        self._linear_session_page.back_requested.connect(self._on_back_requested)
        self._grid_config_page.start_requested.connect(self._on_grid_start)
        self._grid_config_page.back_requested.connect(self._on_back_requested)
        self._grid_session_page.back_requested.connect(self._on_back_requested)
        self._behavioral_config_page.start_requested.connect(self._on_behavioral_start)
        self._behavioral_config_page.back_requested.connect(self._on_back_requested)
        self._behavioral_session_page.back_requested.connect(self._on_back_requested)

        QApplication.instance().setStyleSheet(_STYLE)

    # --- Navigation handlers ------------------------------------------------

    def _on_connected(self, link: SerialLink) -> None:
        self._link = link
        self._link.connection_lost.connect(self._on_connection_lost)
        self._stack.setCurrentWidget(self._mode_select_page)

    def _on_mode_chosen(self, mode: str, hue_enabled: bool) -> None:
        if self._link is None:
            return
        self._link.send(build_mode_command(mode))
        if mode == "SOLID":
            if hue_enabled:
                self._link.send(build_set_command({"hue": 1}))
            self._link.send("START")
            self._solid_view.start_session(self._link, hue_enabled)
            self._active_page = self._solid_view
            self._stack.setCurrentWidget(self._solid_view)
        else:
            self._pending_config_mode = mode
            self._get_buffer = []
            self._link.line_received.connect(self._on_get_response)
            self._link.send("GET")

    def _on_get_response(self, line: str) -> None:
        self._get_buffer.append(line)
        settings = parse_get_response(self._get_buffer)
        if settings is None:
            return
        self._link.line_received.disconnect(self._on_get_response)
        self._get_buffer = []
        config_page = self._config_pages[self._pending_config_mode]
        self._pending_config_mode = None
        config_page.setup(settings)
        self._active_page = config_page
        self._stack.setCurrentWidget(config_page)

    def _on_linear_start(self) -> None:
        self._start_experiment(self._linear_config_page, self._linear_session_page)

    def _on_grid_start(self) -> None:
        self._start_experiment(self._grid_config_page, self._grid_session_page)

    def _on_behavioral_start(self) -> None:
        if self._link is None:
            return
        config_page = self._behavioral_config_page
        changed = config_page.changed_values()
        if changed:
            self._link.send(build_set_command(changed))
        self._link.send("START")
        self._behavioral_session_page.start_session(self._link, config_page.full_settings())
        self._active_page = self._behavioral_session_page
        self._stack.setCurrentWidget(self._behavioral_session_page)

    def _start_experiment(self, config_page, session_page) -> None:
        if self._link is None:
            return
        changed = config_page.changed_values()
        if changed:
            self._link.send(build_set_command(changed))
        self._link.send("START")
        session_page.start_session(self._link, config_page.full_settings(), config_page.hue_log_path())
        self._active_page = session_page
        self._stack.setCurrentWidget(session_page)

    def _on_back_requested(self) -> None:
        if self._link is not None:
            self._link.send("STOP")
        if self._active_page is not None:
            self._active_page.detach()
            self._active_page = None
        self._stack.setCurrentWidget(self._mode_select_page)

    # --- Connection lifecycle ------------------------------------------------

    def _on_connection_lost(self, message: str) -> None:
        """Teensy unplugged or port died: tear down and return to the Connect page."""
        self._teardown_link()
        self._connect_page.restart()
        self._stack.setCurrentWidget(self._connect_page)

    def _teardown_link(self) -> None:
        if self._active_page is not None:
            self._active_page.detach()
            self._active_page = None
        link = self._link
        self._link = None
        if link is None:
            return
        link.connection_lost.disconnect(self._on_connection_lost)
        link.close()

    def closeEvent(self, event) -> None:
        self._teardown_link()
        self._connect_page.close_link()
        super().closeEvent(event)
