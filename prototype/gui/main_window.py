"""Main window: Connect -> Mode/Settings -> Session, as a QStackedWidget."""

from __future__ import annotations

import serial
from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from pyqtgraph import PlotWidget

from protocol import SETTING_NAMES, Settings, build_set_command, parse_dataframe, parse_get_response
from serial_link import SerialLink, find_teensy_port, list_all_ports

AUTO_DETECT_RETRY_MS = 500
AUTO_DETECT_ATTEMPTS_BEFORE_FALLBACK = 6  # ~3 s


class ConnectPage(QWidget):
    """Auto-detects and connects to the Teensy; falls back to manual selection."""

    connected = Signal(SerialLink, Settings)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._link: SerialLink | None = None
        self._attempts = 0

        self._status_label = QLabel("Searching for Teensy...")
        self._port_combo = QComboBox()
        self._connect_button = QPushButton("Connect")
        self._connect_button.clicked.connect(self._connect_to_selected_port)
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
        self._status_label.setText("Couldn't find a Teensy automatically. Select a port:")
        self._port_combo.clear()
        self._port_combo.addItems(list_all_ports())
        self._port_combo.setVisible(True)
        self._connect_button.setVisible(True)

    def _connect_to_selected_port(self) -> None:
        port = self._port_combo.currentText()
        if port:
            self._timer.stop()
            self._open(port)

    def _open(self, port: str) -> None:
        self._status_label.setText(f"Connecting to {port}...")
        try:
            self._link = SerialLink(port)
        except serial.SerialException as exc:
            self._status_label.setText(f"Couldn't open {port}: {exc}")
            self._show_manual_fallback()
            return
        self._link.line_received.connect(self._on_line)
        self._link.connection_lost.connect(self._on_connection_lost)
        self._link.start()
        self._link.send("GET")

    def _on_line(self, line: str) -> None:
        settings = parse_get_response(line)
        if settings is not None and self._link is not None:
            self._link.line_received.disconnect(self._on_line)
            self.connected.emit(self._link, settings)

    def _on_connection_lost(self, message: str) -> None:
        self._status_label.setText(f"Connection lost: {message}")
        self._link = None
        self._attempts = 0
        self._timer.start(AUTO_DETECT_RETRY_MS)


class ModePage(QWidget):
    """Default vs Advanced mode selection, with the Advanced settings form."""

    mode_confirmed = Signal(Settings)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._link: SerialLink | None = None
        self._defaults: Settings | None = None

        self._default_radio = QRadioButton("Default")
        self._advanced_radio = QRadioButton("Advanced")
        self._default_radio.setChecked(True)
        self._default_radio.toggled.connect(self._update_form_enabled)

        self._fields: dict[str, QSpinBox] = {}
        form_layout = QFormLayout()
        for name in SETTING_NAMES:
            spin_box = QSpinBox()
            spin_box.setRange(0, 65535)
            form_layout.addRow(name, spin_box)
            self._fields[name] = spin_box
        self._form_group = QGroupBox("Advanced settings")
        self._form_group.setLayout(form_layout)
        self._form_group.setEnabled(False)

        continue_button = QPushButton("Continue")
        continue_button.clicked.connect(self._confirm)

        layout = QVBoxLayout(self)
        layout.addWidget(self._default_radio)
        layout.addWidget(self._advanced_radio)
        layout.addWidget(self._form_group)
        layout.addWidget(continue_button)

    def set_link_and_defaults(self, link: SerialLink, defaults: Settings) -> None:
        self._link = link
        self._defaults = defaults
        self._fields["flickerFrequencyHz"].setValue(defaults.flicker_frequency_hz)
        self._fields["amberValue"].setValue(defaults.amber_value)
        self._fields["maxRed"].setValue(defaults.max_red)
        self._fields["maxGreen"].setValue(defaults.max_green)
        self._fields["minRed"].setValue(defaults.min_red)
        self._fields["minGreen"].setValue(defaults.min_green)

    def _update_form_enabled(self) -> None:
        self._form_group.setEnabled(self._advanced_radio.isChecked())

    def _confirm(self) -> None:
        if self._link is None or self._defaults is None:
            return
        if self._default_radio.isChecked():
            self._link.send("MODE DEFAULT")
            self.mode_confirmed.emit(self._defaults)
            return

        values = {name: field.value() for name, field in self._fields.items()}
        self._link.send("MODE ADVANCED")
        self._link.send(build_set_command(values))
        resolved = Settings(
            mode="ADVANCED",
            flicker_frequency_hz=values["flickerFrequencyHz"],
            amber_value=values["amberValue"],
            max_red=values["maxRed"],
            max_green=values["maxGreen"],
            min_red=values["minRed"],
            min_green=values["minGreen"],
        )
        self.mode_confirmed.emit(resolved)


class SessionPage(QWidget):
    """Start/Stop controls plus the live red/green scatter plot."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._link: SerialLink | None = None

        self._status_label = QLabel("Not started")
        start_button = QPushButton("Start")
        stop_button = QPushButton("Stop")
        start_button.clicked.connect(lambda: self._send("START"))
        stop_button.clicked.connect(lambda: self._send("STOP"))

        self._plot = PlotWidget()
        self._plot.setLabel("bottom", "red")
        self._plot.setLabel("left", "green")
        self._scatter = self._plot.plot([], [], pen=None, symbol="o", symbolBrush="k", symbolSize=14)

        button_row = QHBoxLayout()
        button_row.addWidget(start_button)
        button_row.addWidget(stop_button)

        layout = QVBoxLayout(self)
        layout.addLayout(button_row)
        layout.addWidget(self._status_label)
        layout.addWidget(self._plot)

    def start_session(self, link: SerialLink, settings: Settings) -> None:
        self._link = link
        self._link.line_received.connect(self._on_line)
        self._plot.setXRange(settings.min_red, settings.max_red)
        self._plot.setYRange(settings.min_green, settings.max_green)

    def _send(self, command: str) -> None:
        if self._link is not None:
            self._link.send(command)

    def _on_line(self, line: str) -> None:
        frame = parse_dataframe(line)
        if frame is None:
            return
        self._scatter.setData([frame.red], [frame.green])
        self._status_label.setText(f"Search {frame.trial_number}, last Press={frame.press}")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Knobs Experiment")

        self._connect_page = ConnectPage()
        self._mode_page = ModePage()
        self._session_page = SessionPage()

        self._stack = QStackedWidget()
        self._stack.addWidget(self._connect_page)
        self._stack.addWidget(self._mode_page)
        self._stack.addWidget(self._session_page)
        self.setCentralWidget(self._stack)

        self._connect_page.connected.connect(self._on_connected)
        self._mode_page.mode_confirmed.connect(self._on_mode_confirmed)

    def _on_connected(self, link: SerialLink, settings: Settings) -> None:
        self._link = link
        self._mode_page.set_link_and_defaults(link, settings)
        self._stack.setCurrentWidget(self._mode_page)

    def _on_mode_confirmed(self, settings: Settings) -> None:
        self._session_page.start_session(self._link, settings)
        self._stack.setCurrentWidget(self._session_page)
