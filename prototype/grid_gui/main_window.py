"""Main window: Connect -> Participant -> Mode/Settings -> Session.

A monitor/controller for the grid (EEG) experiment: it configures and runs the
firmware and shows the stimulus grid filling in live, plus a progress bar. No
data is saved (the experiment's data is the EEG recording, trigger-synced).
"""

from __future__ import annotations

import serial
from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from pyqtgraph import PlotWidget, ScatterPlotItem, mkBrush

from protocol import (
    PHASE_BASELINE,
    PHASE_INTERTRIAL,
    PHASE_STIMULUS,
    SETTING_NAMES,
    Settings,
    build_set_command,
    parse_dataframe,
    parse_get_response,
)
from serial_link import SerialLink, find_teensy_port, list_all_ports

AUTO_DETECT_RETRY_MS = 500
AUTO_DETECT_ATTEMPTS_BEFORE_FALLBACK = 6  # ~3 s

GRID_STEPS = 10  # matches the firmware's kNumSteps (10x10 = 100 stimuli)
GRID_STIMS = GRID_STEPS * GRID_STEPS

GROUPS = ("HC", "PD", "MD", "Protan", "Deutan", "other")
DEFAULT_GROUP = "HC"

# SET name -> Settings attribute, for filling the form and reading it back.
_FIELD_TO_ATTR = {
    "flickerFrequencyHz": "flicker_frequency_hz",
    "amberValue": "amber_value",
    "minRed": "min_red",
    "maxRed": "max_red",
    "minGreen": "min_green",
    "maxGreen": "max_green",
    "trialLengthMs": "trial_length_ms",
    "interTrialWaitMs": "inter_trial_wait_ms",
    "baselinesStart": "baselines_start",
    "baselinesEnd": "baselines_end",
    "order": "order",
}


def _nearest_index(levels: list[int], value: int) -> int:
    return min(range(len(levels)), key=lambda i: abs(levels[i] - value))


def _linspace(min_value: int, max_value: int) -> list[int]:
    return [min_value + (max_value - min_value) * i // (GRID_STEPS - 1) for i in range(GRID_STEPS)]


def _format_settings(s: Settings) -> str:
    return (
        f"Mode: {s.mode} | Flicker: {s.flicker_frequency_hz} Hz | Amber: {s.amber_value} | "
        f"Red: [{s.min_red}, {s.max_red}] | Green: [{s.min_green}, {s.max_green}] | "
        f"Trial: {s.trial_length_ms} ms | ITI: {s.inter_trial_wait_ms} ms | "
        f"Baselines: {s.baselines_start}/{s.baselines_end} | Order: {s.order}"
    )


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
        self._link.start()
        self._link.send("GET")

    def _on_line(self, line: str) -> None:
        settings = parse_get_response(line)
        if settings is not None and self._link is not None:
            self._link.line_received.disconnect(self._on_line)
            self.connected.emit(self._link, settings)


class ParticipantPage(QWidget):
    """Subject ID and group, carried into the run for display only (not saved)."""

    participant_confirmed = Signal(str, str)  # sub_id, group

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._sub_id_edit = QLineEdit()
        self._group_combo = QComboBox()
        self._group_combo.addItems(GROUPS)
        self._group_combo.setCurrentText(DEFAULT_GROUP)

        form = QFormLayout()
        form.addRow("Subject ID", self._sub_id_edit)
        form.addRow("Group", self._group_combo)

        note = QLabel("Shown during the run for reference only; nothing is saved yet.")
        note.setWordWrap(True)
        continue_button = QPushButton("Continue")
        continue_button.clicked.connect(self._confirm)

        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addLayout(form)
        layout.addWidget(note)
        layout.addWidget(continue_button)
        layout.addStretch()

    def _confirm(self) -> None:
        self.participant_confirmed.emit(self._sub_id_edit.text().strip(), self._group_combo.currentText())


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
            if name == "order":
                spin_box.setRange(1, 4)
            else:
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
        for name, attr in _FIELD_TO_ATTR.items():
            self._fields[name].setValue(getattr(defaults, attr))

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
        resolved = Settings(mode="ADVANCED", **{attr: values[name] for name, attr in _FIELD_TO_ATTR.items()})
        self.mode_confirmed.emit(resolved)


class SessionPage(QWidget):
    """Start/Stop, the live stimulus grid, a progress bar, and the active
    settings. "Back" is only enabled while no run is in progress."""

    back_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._link: SerialLink | None = None
        self._settings: Settings | None = None
        self._running = False

        self._red_levels: list[int] = []
        self._green_levels: list[int] = []
        self._visited: set[tuple[int, int]] = set()
        self._current: tuple[int, int] | None = None
        self._total_trials = 0
        self._completed = 0

        self._params_label = QLabel("")
        self._params_label.setWordWrap(True)

        self._start_button = QPushButton("Start")
        self._stop_button = QPushButton("Stop")
        self._back_button = QPushButton("Back to experiment selection")
        self._start_button.clicked.connect(self._start)
        self._stop_button.clicked.connect(self._stop)
        self._back_button.clicked.connect(self.back_requested)

        self._status_label = QLabel("Not started")
        self._progress = QProgressBar()

        self._plot = PlotWidget()
        self._plot.setBackground("k")
        self._plot.setLabel("bottom", "Red LED intensity (A/D)")
        self._plot.setLabel("left", "Green LED intensity (A/D)")
        self._scatter = ScatterPlotItem()
        self._plot.addItem(self._scatter)

        button_row = QHBoxLayout()
        button_row.addWidget(self._start_button)
        button_row.addWidget(self._stop_button)
        button_row.addWidget(self._back_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self._params_label)
        layout.addLayout(button_row)
        layout.addWidget(self._status_label)
        layout.addWidget(self._progress)
        layout.addWidget(self._plot, stretch=1)

        self._update_buttons()

    def start_session(self, link: SerialLink, settings: Settings, sub_id: str, group: str) -> None:
        if self._link is None:
            self._link = link
            self._link.line_received.connect(self._on_line)
        else:
            self._link = link
        self._settings = settings

        participant = f"   |   Participant: {sub_id} ({group})" if sub_id else ""
        self._params_label.setText(_format_settings(settings) + participant)

        self._running = False
        self._setup_grid(settings)
        self._status_label.setText("Not started")
        self._update_buttons()

    def _setup_grid(self, s: Settings) -> None:
        self._red_levels = _linspace(s.min_red, s.max_red)
        self._green_levels = _linspace(s.min_green, s.max_green)
        self._visited = set()
        self._current = None
        self._total_trials = s.baselines_start + GRID_STIMS + s.baselines_end
        self._completed = 0
        self._progress.setRange(0, self._total_trials)
        self._progress.setValue(0)
        self._plot.setXRange(s.min_red, s.max_red, padding=0.05)
        self._plot.setYRange(s.min_green, s.max_green, padding=0.05)
        self._refresh_scatter()

    def _refresh_scatter(self) -> None:
        spots = []
        for gi, green in enumerate(self._green_levels):
            for ri, red in enumerate(self._red_levels):
                key = (ri, gi)
                if key == self._current:
                    brush, size = mkBrush("r"), 20
                elif key in self._visited:
                    brush, size = mkBrush("y"), 15
                else:
                    brush, size = mkBrush(70, 70, 70), 10
                spots.append({"pos": (red, green), "brush": brush, "size": size, "pen": None})
        self._scatter.setData(spots)

    def _start(self) -> None:
        self._setup_grid(self._settings)  # clear any previous run's highlights
        self._send("GRIDSTART")
        self._running = True
        self._status_label.setText("Running...")
        self._update_buttons()

    def _stop(self) -> None:
        self._send("GRIDSTOP")
        self._running = False
        self._status_label.setText("Stopped")
        self._update_buttons()

    def _update_buttons(self) -> None:
        self._start_button.setEnabled(not self._running)
        self._stop_button.setEnabled(self._running)
        self._back_button.setEnabled(not self._running)

    def _send(self, command: str) -> None:
        if self._link is not None:
            self._link.send(command)

    def _on_line(self, line: str) -> None:
        if line == "GRID DONE":
            self._completed = self._total_trials
            self._progress.setValue(self._total_trials)
            self._current = None
            self._refresh_scatter()
            self._running = False
            self._status_label.setText("Finished")
            self._update_buttons()
            return

        frame = parse_dataframe(line)
        if frame is None:
            return

        if frame.phase == PHASE_STIMULUS:
            ri = _nearest_index(self._red_levels, frame.red)
            gi = _nearest_index(self._green_levels, frame.green)
            self._current = (ri, gi)
            self._visited.add((ri, gi))
            self._refresh_scatter()
            self._status_label.setText(f"Stimulus {frame.stim_number} / {GRID_STIMS}")
        elif frame.phase == PHASE_BASELINE:
            self._status_label.setText("Baseline trial")
        elif frame.phase == PHASE_INTERTRIAL:
            self._completed += 1
            self._progress.setValue(min(self._completed, self._total_trials))
            self._current = None
            self._refresh_scatter()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Grid EEG Experiment")

        self._connect_page = ConnectPage()
        self._participant_page = ParticipantPage()
        self._mode_page = ModePage()
        self._session_page = SessionPage()

        self._stack = QStackedWidget()
        self._stack.addWidget(self._connect_page)
        self._stack.addWidget(self._participant_page)
        self._stack.addWidget(self._mode_page)
        self._stack.addWidget(self._session_page)
        self.setCentralWidget(self._stack)

        self._link: SerialLink | None = None
        self._sub_id = ""
        self._group = ""

        self._connect_page.connected.connect(self._on_connected)
        self._participant_page.participant_confirmed.connect(self._on_participant_confirmed)
        self._mode_page.mode_confirmed.connect(self._on_mode_confirmed)
        self._session_page.back_requested.connect(self._on_back_requested)

    def _on_connected(self, link: SerialLink, settings: Settings) -> None:
        self._link = link
        self.statusBar().showMessage("Connected")
        self._stack.setCurrentWidget(self._participant_page)

    def _on_participant_confirmed(self, sub_id: str, group: str) -> None:
        self._sub_id = sub_id
        self._group = group
        # Re-query GET so the mode form reflects the firmware's current settings.
        self._link.line_received.connect(self._on_settings_for_mode)
        self._link.send("GET")

    def _on_settings_for_mode(self, line: str) -> None:
        settings = parse_get_response(line)
        if settings is None:
            return
        self._link.line_received.disconnect(self._on_settings_for_mode)
        self._mode_page.set_link_and_defaults(self._link, settings)
        self._stack.setCurrentWidget(self._mode_page)

    def _on_mode_confirmed(self, settings: Settings) -> None:
        self._session_page.start_session(self._link, settings, self._sub_id, self._group)
        self._stack.setCurrentWidget(self._session_page)

    def _on_back_requested(self) -> None:
        self._stack.setCurrentWidget(self._participant_page)
