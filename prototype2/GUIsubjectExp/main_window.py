"""Main window and all pages for the subjectExperiment GUI.

Navigation: Connect -> Participant -> ExperimentSelect -> ModeConfig -> Session.
Back from a session returns to ExperimentSelect (re-queries firmware settings)
so the same participant can run multiple experiments without re-entering info.
"""

from __future__ import annotations

from pathlib import Path
from statistics import median

import serial
from PySide6.QtCore import QSettings, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from pyqtgraph import PlotWidget, ScatterPlotItem, mkBrush, mkPen

from participants import (
    DEFAULT_GROUP,
    GROUPS,
    list_participants,
    next_session_number,
    record_behavioral_session,
    record_grid_session,
    session_file_name,
)
from protocol import GET_KEYS, build_batch_command, parse_get_response, parse_resp, parse_stream_frame
from serial_link import SerialLink, find_teensy_port, list_all_ports

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AUTO_DETECT_RETRY_MS = 500
AUTO_DETECT_ATTEMPTS_BEFORE_FALLBACK = 6

GRID_STEPS = 10
GRID_STIMS = GRID_STEPS * GRID_STEPS

_PALETTE = {
    "rg": {
        "primary": "#f70404",
        "secondary": "#b1ff01",
        "reference": "#fabd04",
        "label_a": "Red",
        "label_b": "Green",
    },
    "bg": {
        "primary": "#0493ff",
        "secondary": "#b1ff01",
        "reference": "#50fefe",
        "label_a": "Blue",
        "label_b": "Green",
    },
}
_NEUTRAL_PRIMARY = "#888888"

_STYLE_TEMPLATE = """\
* {{ background-color: #0a0a0a; color: #d0d0d0; }}
QPushButton {{
    border: 1px solid {primary}; color: {primary};
    background: #141414; padding: 5px 14px;
}}
QPushButton:hover {{ background: #1e1e1e; }}
QPushButton:disabled {{ border-color: #333; color: #444; background: #0f0f0f; }}
QLineEdit, QComboBox, QSpinBox {{
    background: #141414; border: 1px solid #333; padding: 2px;
}}
QGroupBox {{ border: 1px solid #2a2a2a; margin-top: 12px; padding-top: 6px; }}
QGroupBox::title {{ color: {primary}; subcontrol-origin: margin; padding: 0 4px; }}
QProgressBar {{
    border: 1px solid #333; background: #141414;
    text-align: center; height: 18px;
}}
QProgressBar::chunk {{ background-color: {primary}; }}
QHeaderView::section {{
    background: #141414; color: {primary};
    border: 1px solid #222; padding: 2px;
}}
QTableWidget {{ gridline-color: #1e1e1e; background: #0a0a0a; }}
QStatusBar {{ background: #000; border-top: 1px solid #1a1a1a; }}
QRadioButton {{ spacing: 6px; }}
"""

# Parameters grayed out when running a behavioral experiment.
_GRID_ONLY_PARAMS = ("nBaselinesStart", "nBaselinesEnd", "order")

# SpinBox ranges for each parameter key.
_PARAM_RANGES: dict[str, tuple[int, int]] = {
    "freq":            (1,    100),
    "refAmber":        (0,   4095),
    "refCyan":         (0,   4095),
    "maxA":            (0,   4095),
    "minA":            (0,   4095),
    "maxB":            (0,   4095),
    "minB":            (0,   4095),
    "nBaselinesStart": (0,     20),
    "nBaselinesEnd":   (0,     20),
    "trialLength":     (100, 30000),
    "interTrialWait":  (0,  10000),
    "order":           (1,      4),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _apply_style(primary: str = _NEUTRAL_PRIMARY) -> None:
    app = QApplication.instance()
    if app is not None:
        app.setStyleSheet(_STYLE_TEMPLATE.format(primary=primary))


def _color_pair(mode_str: str) -> str:
    """Returns 'rg' or 'bg' from a mode string like 'beh-rg'."""
    return mode_str.split("-")[-1] if "-" in mode_str else ""


def _exp_type(mode_str: str) -> str:
    """Returns 'behavioral' or 'grid' from a mode string."""
    return "behavioral" if mode_str.startswith("beh") else "grid"


def _nearest_index(levels: list[int], value: int) -> int:
    return min(range(len(levels)), key=lambda i: abs(levels[i] - value))


def _linspace(lo: int, hi: int, n: int = GRID_STEPS) -> list[int]:
    if n == 1:
        return [lo]
    return [lo + (hi - lo) * i // (n - 1) for i in range(n)]


def _format_settings(mode_str: str, s: dict) -> str:
    pair = _color_pair(mode_str)
    pal = _PALETTE.get(pair, {})
    a, b = pal.get("label_a", "A"), pal.get("label_b", "B")
    return (
        f"{mode_str}  |  {s.get('freq', '?')} Hz  |  "
        f"{a}: [{s.get('minA', '?')}, {s.get('maxA', '?')}]  "
        f"{b}: [{s.get('minB', '?')}, {s.get('maxB', '?')}]"
    )


# ---------------------------------------------------------------------------
# ConnectPage
# ---------------------------------------------------------------------------

class ConnectPage(QWidget):
    """Auto-detects the Teensy; falls back to manual port selection.
    Confirms identity by sending 'get' and waiting for a mode= response line.
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
        self._link.send("get")
        self._status_label.setText(f"Connected to {port}. Verifying firmware...")

    def _on_line(self, line: str) -> None:
        self._get_buffer.append(line)
        settings = parse_get_response(self._get_buffer)
        if settings is not None and self._link is not None:
            self._link.line_received.disconnect(self._on_line)
            self._get_buffer.clear()
            self.connected.emit(self._link)

    def _on_connection_lost(self, message: str) -> None:
        self._status_label.setText(f"Connection lost: {message}")
        self._link = None
        self._attempts = 0
        self._get_buffer.clear()
        self._timer.start(AUTO_DETECT_RETRY_MS)


# ---------------------------------------------------------------------------
# ParticipantPage
# ---------------------------------------------------------------------------

class ParticipantPage(QWidget):
    """Pick a save folder, then select or create a participant."""

    participant_confirmed = Signal(str, str, str)  # sub_id, group, folder

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._qsettings = QSettings("behExperiment1", "SubjectExpGui")

        self._folder_edit = QLineEdit(self._qsettings.value("save_folder", ""))
        self._folder_edit.setReadOnly(True)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._choose_folder)
        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Save folder:"))
        folder_row.addWidget(self._folder_edit, 1)
        folder_row.addWidget(browse_btn)

        self._existing_radio = QRadioButton("Existing participant")
        self._new_radio = QRadioButton("New participant")
        self._new_radio.setChecked(True)
        self._existing_radio.toggled.connect(self._update_enabled)
        self._existing_combo = QComboBox()

        self._sub_id_edit = QLineEdit()
        self._group_combo = QComboBox()
        self._group_combo.addItems(GROUPS)
        self._group_combo.setCurrentText(DEFAULT_GROUP)
        new_form = QFormLayout()
        new_form.addRow("Subject ID", self._sub_id_edit)
        new_form.addRow("Group", self._group_combo)
        self._new_group = QGroupBox("New participant")
        self._new_group.setLayout(new_form)

        self._error_label = QLabel("")
        continue_btn = QPushButton("Continue")
        continue_btn.clicked.connect(self._confirm)

        layout = QVBoxLayout(self)
        layout.addLayout(folder_row)
        layout.addWidget(self._existing_radio)
        layout.addWidget(self._existing_combo)
        layout.addWidget(self._new_radio)
        layout.addWidget(self._new_group)
        layout.addWidget(self._error_label)
        layout.addStretch()
        layout.addWidget(continue_btn)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._reload_participants()

    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select save folder", self._folder_edit.text())
        if folder:
            self._folder_edit.setText(folder)
            self._qsettings.setValue("save_folder", folder)
            self._reload_participants()

    def _reload_participants(self) -> None:
        self._existing_combo.clear()
        folder = self._folder_edit.text()
        pairs = list_participants(Path(folder)) if folder else []
        for sub_id, group in pairs:
            self._existing_combo.addItem(f"{sub_id} ({group})", (sub_id, group))
        self._existing_radio.setEnabled(bool(pairs))
        if not pairs:
            self._new_radio.setChecked(True)
        self._update_enabled()

    def _update_enabled(self) -> None:
        existing = self._existing_radio.isChecked()
        self._existing_combo.setEnabled(existing)
        self._new_group.setEnabled(not existing)

    def _confirm(self) -> None:
        folder = self._folder_edit.text()
        if not folder:
            self._error_label.setText("Choose a save folder first.")
            return
        if self._existing_radio.isChecked():
            data = self._existing_combo.currentData()
            if data is None:
                self._error_label.setText("Select a participant.")
                return
            sub_id, group = data
        else:
            sub_id = self._sub_id_edit.text().strip()
            if not sub_id:
                self._error_label.setText("Enter a subject ID.")
                return
            existing_ids = {
                self._existing_combo.itemData(i)[0]
                for i in range(self._existing_combo.count())
                if self._existing_combo.itemData(i)
            }
            if sub_id in existing_ids:
                self._error_label.setText(f"{sub_id} already exists; select it under Existing participant.")
                return
            group = self._group_combo.currentText()
        self._error_label.setText("")
        self.participant_confirmed.emit(sub_id, group, folder)


# ---------------------------------------------------------------------------
# ExperimentSelectPage
# ---------------------------------------------------------------------------

class ExperimentSelectPage(QWidget):
    """Four-way choice of experiment type and color mode."""

    mode_selected = Signal(str)          # fired on Continue: "beh-rg" etc.
    color_mode_changed = Signal(str)     # fired on radio toggle: "rg" / "bg" / ""

    _MODES = [
        ("beh-rg", "Behavioral (knobs)  —  Red / Green"),
        ("beh-bg", "Behavioral (knobs)  —  Blue / Green"),
        ("grid-rg", "Grid (EEG)  —  Red / Green"),
        ("grid-bg", "Grid (EEG)  —  Blue / Green"),
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._radios: dict[str, QRadioButton] = {}

        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(QLabel("Choose an experiment:"))
        for mode_str, label in self._MODES:
            radio = QRadioButton(label)
            radio.toggled.connect(lambda checked, m=mode_str: self._on_toggle(checked, m))
            layout.addWidget(radio)
            self._radios[mode_str] = radio
        layout.addStretch()

        continue_btn = QPushButton("Continue")
        continue_btn.clicked.connect(self._confirm)
        layout.addWidget(continue_btn)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Re-emit current color mode so the stylesheet stays consistent.
        current = self._current_mode()
        self.color_mode_changed.emit(_color_pair(current) if current else "")

    def _on_toggle(self, checked: bool, mode_str: str) -> None:
        if checked:
            self.color_mode_changed.emit(_color_pair(mode_str))

    def _current_mode(self) -> str:
        for mode_str, radio in self._radios.items():
            if radio.isChecked():
                return mode_str
        return ""

    def _confirm(self) -> None:
        mode = self._current_mode()
        if mode:
            self.mode_selected.emit(mode)


# ---------------------------------------------------------------------------
# ModeConfigPage
# ---------------------------------------------------------------------------

class ModeConfigPage(QWidget):
    """Default / Advanced settings for the chosen mode.

    Default: navigates to the session page with no parameter changes.
    Advanced: sends a batch config command, then navigates to the session page.
    The session page's Start button issues the actual firmware start command.
    """

    mode_confirmed = Signal(str, dict)   # mode_str, settings dict

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._link: SerialLink | None = None
        self._mode_str = ""
        self._current_settings: dict = {}

        self._title_label = QLabel()

        self._default_radio = QRadioButton("Default (use current firmware settings)")
        self._advanced_radio = QRadioButton("Advanced (customize parameters)")
        self._default_radio.setChecked(True)
        self._default_radio.toggled.connect(self._update_form_enabled)

        self._fields: dict[str, QSpinBox] = {}
        form = QFormLayout()
        for key in GET_KEYS:
            spin = QSpinBox()
            lo, hi = _PARAM_RANGES.get(key, (0, 65535))
            spin.setRange(lo, hi)
            form.addRow(key, spin)
            self._fields[key] = spin
        self._form_group = QGroupBox("Parameters")
        self._form_group.setLayout(form)
        self._form_group.setEnabled(False)

        continue_btn = QPushButton("Continue")
        continue_btn.clicked.connect(self._confirm)

        layout = QVBoxLayout(self)
        layout.addWidget(self._title_label)
        layout.addWidget(self._default_radio)
        layout.addWidget(self._advanced_radio)
        layout.addWidget(self._form_group)
        layout.addStretch()
        layout.addWidget(continue_btn)

    def setup(self, link: SerialLink, mode_str: str, settings: dict) -> None:
        self._link = link
        self._mode_str = mode_str
        self._current_settings = settings
        self._title_label.setText(f"Mode: {mode_str}")

        is_behavioral = _exp_type(mode_str) == "behavioral"
        for key, spin in self._fields.items():
            spin.setValue(int(settings.get(key, spin.minimum())))
            spin.setEnabled(key not in _GRID_ONLY_PARAMS or not is_behavioral)

        self._default_radio.setChecked(True)
        self._update_form_enabled()

    def _update_form_enabled(self) -> None:
        self._form_group.setEnabled(self._advanced_radio.isChecked())

    def _confirm(self) -> None:
        if self._link is None:
            return
        if self._advanced_radio.isChecked():
            changed = {
                key: spin.value()
                for key, spin in self._fields.items()
                if spin.value() != int(self._current_settings.get(key, spin.minimum()))
                and spin.isEnabled()
            }
            if changed:
                self._link.send(build_batch_command(changed))
            settings = {**self._current_settings, **{k: str(v) for k, v in changed.items()}}
        else:
            settings = self._current_settings
        self.mode_confirmed.emit(self._mode_str, settings)


# ---------------------------------------------------------------------------
# BehavioralSessionPage
# ---------------------------------------------------------------------------

class BehavioralSessionPage(QWidget):
    """Live scatter plot, press table, and session file recording."""

    back_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._link: SerialLink | None = None
        self._mode_str = ""
        self._settings: dict = {}
        self._palette: dict = {}
        self._session_active = False

        self._folder: Path | None = None
        self._sub_id = ""
        self._group = ""
        self._session_number = 0
        self._run_file: Path | None = None

        self._press_a: list[int] = []
        self._press_b: list[int] = []

        self._status_label = QLabel("Not started")
        self._start_btn = QPushButton("Start")
        self._stop_btn = QPushButton("Stop")
        self._back_btn = QPushButton("Back to experiment selection")
        self._save_btn = QPushButton("Save Results...")
        self._start_btn.clicked.connect(self._start)
        self._stop_btn.clicked.connect(self._stop)
        self._back_btn.clicked.connect(self.back_requested)
        self._save_btn.clicked.connect(self._save_results)

        self._plot = PlotWidget()
        self._plot.setBackground("k")
        self._plot.setLabel("bottom", "Primary LED (A/D)")
        self._plot.setLabel("left", "Secondary LED (A/D)")

        self._current_marker = self._plot.plot(
            [], [], pen=None, symbol="o", symbolBrush="#fabd04", symbolPen=None, symbolSize=16
        )
        self._press_marks = self._plot.plot(
            [], [], pen=None, symbol="x", symbolBrush=None, symbolPen="gray", symbolSize=14
        )
        self._median_marker = self._plot.plot(
            [], [], pen=None, symbol="star", symbolBrush="#f70404", symbolPen=None, symbolSize=22
        )

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Trial", "Primary", "Secondary"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._median_label = QLabel("Median: —")

        btn_row = QHBoxLayout()
        btn_row.addWidget(self._start_btn)
        btn_row.addWidget(self._stop_btn)
        btn_row.addWidget(self._back_btn)
        btn_row.addWidget(self._save_btn)

        table_col = QVBoxLayout()
        table_col.addWidget(self._table)
        table_col.addWidget(self._median_label)

        plot_and_table = QHBoxLayout()
        plot_and_table.addWidget(self._plot, stretch=3)
        plot_and_table.addLayout(table_col, stretch=1)

        layout = QVBoxLayout(self)
        layout.addLayout(btn_row)
        layout.addWidget(self._status_label)
        layout.addLayout(plot_and_table)

        self._update_buttons()

    def set_participant(self, folder: Path, sub_id: str, group: str) -> None:
        self._folder = folder
        self._sub_id = sub_id
        self._group = group

    def start_session(self, link: SerialLink, mode_str: str, settings: dict, palette: dict) -> None:
        if self._link is None:
            self._link = link
            self._link.line_received.connect(self._on_line)
        else:
            self._link = link

        self._mode_str = mode_str
        self._settings = settings
        self._palette = palette
        self._session_active = False
        self._run_file = None
        self._press_a.clear()
        self._press_b.clear()
        self._current_marker.setData([], [])
        self._press_marks.setData([], [])
        self._median_marker.setData([], [])
        self._table.setRowCount(0)
        self._median_label.setText("Median: —")
        self._status_label.setText("Not started")

        # Apply palette to plot elements.
        self._current_marker.setSymbolBrush(palette["reference"])
        self._median_marker.setSymbolBrush(palette["primary"])
        self._plot.setLabel("bottom", f"{palette['label_a']} LED (A/D)")
        self._plot.setLabel("left", f"{palette['label_b']} LED (A/D)")
        self._table.setHorizontalHeaderLabels(["Trial", palette["label_a"], palette["label_b"]])

        min_a, max_a = int(settings.get("minA", 0)), int(settings.get("maxA", 4095))
        min_b, max_b = int(settings.get("minB", 0)), int(settings.get("maxB", 4095))
        self._plot.setXRange(min_a, max_a, padding=0)
        self._plot.setYRange(min_b, max_b, padding=0)
        self._update_buttons()

    def _start(self) -> None:
        if self._run_file is None:
            self._open_run_file()
        self._send(self._mode_str)
        self._session_active = True
        self._update_buttons()

    def _open_run_file(self) -> None:
        self._session_number = next_session_number(self._folder, self._sub_id, "behavioral")
        file_name = session_file_name(self._sub_id, self._session_number)
        self._run_file = self._folder / file_name
        with self._run_file.open("w") as f:
            f.write("Trial Primary Green\n")
        record_behavioral_session(
            self._folder, self._sub_id, self._group,
            self._session_number, file_name, self._settings
        )

    def _stop(self) -> None:
        self._send("stop")
        self._session_active = False
        self._update_buttons()

    def _update_buttons(self) -> None:
        self._start_btn.setEnabled(not self._session_active)
        self._stop_btn.setEnabled(self._session_active)
        self._back_btn.setEnabled(not self._session_active)

    def _send(self, cmd: str) -> None:
        if self._link is not None:
            self._link.send(cmd)

    def _on_line(self, line: str) -> None:
        # Press event.
        resp = parse_resp(line)
        if resp is not None:
            trial, a, b = resp
            self._press_a.append(a)
            self._press_b.append(b)
            self._press_marks.setData(self._press_a, self._press_b)
            med_a = median(self._press_a)
            med_b = median(self._press_b)
            self._median_marker.setData([med_a], [med_b])
            la, lb = self._palette.get("label_a", "A"), self._palette.get("label_b", "B")
            self._median_label.setText(f"Median  {la}: {med_a:g}  {lb}: {med_b:g}")
            self._append_table_row(trial, a, b)
            if self._run_file is not None:
                self._append_to_file(trial, a, b)
            return

        # Status messages: surface errors, ignore the rest.
        if line.startswith("ERR "):
            self._status_label.setText(line)
            return
        if line in ("DONE", "Stopped.") or line.startswith("START ") or line.startswith("SET "):
            return

        # Streaming telemetry frame — live position update.
        frame = parse_stream_frame(line)
        if frame is None:
            return
        primary = frame["RED"] if frame["Mode"] == "RG" else frame["BLUE"]
        self._current_marker.setData([primary], [frame["GREEN"]])
        self._status_label.setText(
            f"{self._sub_id}  session R{self._session_number}  —  trial {frame['STIM']}"
        )

    def _append_table_row(self, trial: int, a: int, b: int) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        for col, val in enumerate((trial, a, b)):
            self._table.setItem(row, col, QTableWidgetItem(str(val)))
        self._table.scrollToBottom()

    def _append_to_file(self, trial: int, a: int, b: int) -> None:
        with self._run_file.open("a") as f:
            f.write(f"{trial} {a} {b}\n")

    def _save_results(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save Results", "results.txt", "Text files (*.txt)")
        if not path:
            return
        with open(path, "w") as f:
            f.write("Trial Primary Secondary\n")
            for row in range(self._table.rowCount()):
                vals = (self._table.item(row, col).text() for col in range(3))
                f.write(" ".join(vals) + "\n")


# ---------------------------------------------------------------------------
# GridSessionPage
# ---------------------------------------------------------------------------

class GridSessionPage(QWidget):
    """10x10 stimulus grid, progress bar, and EEG trigger indicator."""

    back_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._link: SerialLink | None = None
        self._mode_str = ""
        self._settings: dict = {}
        self._palette: dict = {}
        self._running = False
        self._session_recorded = False

        self._folder: Path | None = None
        self._sub_id = ""
        self._group = ""
        self._session_number = 0

        self._a_levels: list[int] = []
        self._b_levels: list[int] = []
        self._visited: set[tuple[int, int]] = set()
        self._current: tuple[int, int] | None = None
        self._total_trials = 0
        self._completed = 0
        self._last_trig = 0

        self._params_label = QLabel("")
        self._params_label.setWordWrap(True)

        self._start_btn = QPushButton("Start")
        self._stop_btn = QPushButton("Stop")
        self._back_btn = QPushButton("Back to experiment selection")
        self._start_btn.clicked.connect(self._start)
        self._stop_btn.clicked.connect(self._stop)
        self._back_btn.clicked.connect(self.back_requested)

        self._status_label = QLabel("Not started")
        self._progress = QProgressBar()

        # Trigger LED indicator: small square that lights up on TRIG=1.
        self._trig_label = QLabel("TRIG")
        self._trig_label.setFixedSize(48, 20)
        self._trig_label.setStyleSheet("background: #222; color: #555; padding: 2px; border-radius: 3px;")

        self._plot = PlotWidget()
        self._plot.setBackground("k")
        self._plot.setLabel("bottom", "Primary LED (A/D)")
        self._plot.setLabel("left", "Secondary LED (A/D)")
        self._scatter = ScatterPlotItem()
        self._plot.addItem(self._scatter)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self._start_btn)
        btn_row.addWidget(self._stop_btn)
        btn_row.addWidget(self._back_btn)

        status_row = QHBoxLayout()
        status_row.addWidget(self._status_label, 1)
        status_row.addWidget(self._trig_label)

        layout = QVBoxLayout(self)
        layout.addWidget(self._params_label)
        layout.addLayout(btn_row)
        layout.addLayout(status_row)
        layout.addWidget(self._progress)
        layout.addWidget(self._plot, stretch=1)

        self._update_buttons()

    def set_participant(self, folder: Path, sub_id: str, group: str) -> None:
        self._folder = folder
        self._sub_id = sub_id
        self._group = group

    def start_session(self, link: SerialLink, mode_str: str, settings: dict, palette: dict) -> None:
        if self._link is None:
            self._link = link
            self._link.line_received.connect(self._on_line)
        else:
            self._link = link

        self._mode_str = mode_str
        self._settings = settings
        self._palette = palette
        self._session_recorded = False
        self._running = False
        self._last_trig = 0

        self._plot.setLabel("bottom", f"{palette['label_a']} LED (A/D)")
        self._plot.setLabel("left", f"{palette['label_b']} LED (A/D)")

        participant_note = f"   |   {self._sub_id}" if self._sub_id else ""
        self._params_label.setText(_format_settings(mode_str, settings) + participant_note)

        self._setup_grid(settings)
        self._status_label.setText("Not started")
        self._set_trig(0)
        self._update_buttons()

    def _setup_grid(self, s: dict) -> None:
        min_a, max_a = int(s.get("minA", 0)), int(s.get("maxA", 4095))
        min_b, max_b = int(s.get("minB", 0)), int(s.get("maxB", 4095))
        n_start = int(s.get("nBaselinesStart", 2))
        n_end   = int(s.get("nBaselinesEnd",   2))

        self._a_levels = _linspace(min_a, max_a)
        self._b_levels = _linspace(min_b, max_b)
        self._visited = set()
        self._current = None
        self._completed = 0
        self._total_trials = n_start + GRID_STIMS + n_end

        self._progress.setRange(0, self._total_trials)
        self._progress.setValue(0)
        self._plot.setXRange(min_a, max_a, padding=0.05)
        self._plot.setYRange(min_b, max_b, padding=0.05)
        self._refresh_scatter()

    def _refresh_scatter(self) -> None:
        pal = self._palette
        ref_brush   = mkBrush(pal.get("reference", "#fabd04"))
        prime_brush = mkBrush(pal.get("primary",   "#f70404"))
        gray_brush  = mkBrush(70, 70, 70)

        spots = []
        for gi, b_val in enumerate(self._b_levels):
            for ai, a_val in enumerate(self._a_levels):
                key = (ai, gi)
                if key == self._current:
                    brush, size = ref_brush, 20
                elif key in self._visited:
                    brush, size = prime_brush, 14
                else:
                    brush, size = gray_brush, 10
                spots.append({"pos": (a_val, b_val), "brush": brush, "size": size, "pen": None})
        self._scatter.setData(spots)

    def _start(self) -> None:
        if not self._session_recorded:
            self._record_session()
        self._setup_grid(self._settings)
        self._send(self._mode_str)
        self._running = True
        self._last_trig = 0
        self._status_label.setText("Running...")
        self._update_buttons()

    def _record_session(self) -> None:
        self._session_number = next_session_number(self._folder, self._sub_id, "grid")
        record_grid_session(
            self._folder, self._sub_id, self._group,
            self._session_number, self._settings
        )
        self._session_recorded = True

    def _stop(self) -> None:
        self._send("stop")
        self._running = False
        self._status_label.setText("Stopped")
        self._set_trig(0)
        self._update_buttons()

    def _update_buttons(self) -> None:
        self._start_btn.setEnabled(not self._running)
        self._stop_btn.setEnabled(self._running)
        self._back_btn.setEnabled(not self._running)

    def _send(self, cmd: str) -> None:
        if self._link is not None:
            self._link.send(cmd)

    def _set_trig(self, trig: int) -> None:
        ref = self._palette.get("reference", "#fabd04")
        if trig:
            self._trig_label.setStyleSheet(
                f"background: {ref}; color: #000; padding: 2px; border-radius: 3px;"
            )
        else:
            self._trig_label.setStyleSheet(
                "background: #222; color: #555; padding: 2px; border-radius: 3px;"
            )

    def _on_line(self, line: str) -> None:
        if line == "DONE":
            self._completed = self._total_trials
            self._progress.setValue(self._total_trials)
            self._current = None
            self._refresh_scatter()
            self._running = False
            self._status_label.setText("Done")
            self._set_trig(0)
            self._update_buttons()
            return

        if line.startswith("ERR "):
            self._status_label.setText(line)
            return

        frame = parse_stream_frame(line)
        if frame is None:
            return

        trig = frame["TRIG"]
        stim = frame["STIM"]
        mode = frame["Mode"]

        # Trigger indicator.
        self._set_trig(trig)

        # TRIG falling edge: trial just ended, increment progress.
        if trig == 0 and self._last_trig == 1:
            if self._current is not None:
                self._visited.add(self._current)
            self._current = None
            self._completed = min(self._completed + 1, self._total_trials)
            self._progress.setValue(self._completed)
            self._refresh_scatter()

        # Current stimulus position.
        if trig == 1 and stim <= GRID_STIMS:
            primary = frame["RED"] if mode == "RG" else frame["BLUE"]
            ai = _nearest_index(self._a_levels, primary)
            bi = _nearest_index(self._b_levels, frame["GREEN"])
            if (ai, bi) != self._current:
                self._current = (ai, bi)
                self._refresh_scatter()
            self._status_label.setText(f"Stimulus {stim} / {GRID_STIMS}")
        elif trig == 1 and stim > GRID_STIMS:
            self._status_label.setText("Baseline trial")

        self._last_trig = trig


# ---------------------------------------------------------------------------
# MainWindow
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("subjectExperiment")

        self._connect_page = ConnectPage()
        self._participant_page = ParticipantPage()
        self._experiment_select_page = ExperimentSelectPage()
        self._mode_config_page = ModeConfigPage()
        self._behavioral_session_page = BehavioralSessionPage()
        self._grid_session_page = GridSessionPage()

        self._stack = QStackedWidget()
        for page in (
            self._connect_page,
            self._participant_page,
            self._experiment_select_page,
            self._mode_config_page,
            self._behavioral_session_page,
            self._grid_session_page,
        ):
            self._stack.addWidget(page)
        self.setCentralWidget(self._stack)

        self._link: SerialLink | None = None
        self._folder: Path | None = None
        self._sub_id = ""
        self._group = ""
        self._active_mode = ""
        self._active_palette: dict = {}
        self._get_buffer: list[str] = []

        self._settings_label = QLabel("Not connected")
        self.statusBar().addPermanentWidget(self._settings_label, 1)

        # Wiring
        self._connect_page.connected.connect(self._on_connected)
        self._participant_page.participant_confirmed.connect(self._on_participant_confirmed)
        self._experiment_select_page.mode_selected.connect(self._on_mode_selected)
        self._experiment_select_page.color_mode_changed.connect(self._on_color_mode_changed)
        self._mode_config_page.mode_confirmed.connect(self._on_mode_confirmed)
        self._behavioral_session_page.back_requested.connect(self._on_back_requested)
        self._grid_session_page.back_requested.connect(self._on_back_requested)

        _apply_style()

    # --- Navigation handlers ------------------------------------------------

    def _on_connected(self, link: SerialLink) -> None:
        self._link = link
        self._settings_label.setText("Connected")
        self._stack.setCurrentWidget(self._participant_page)

    def _on_participant_confirmed(self, sub_id: str, group: str, folder: str) -> None:
        self._sub_id = sub_id
        self._group = group
        self._folder = Path(folder)
        self._stack.setCurrentWidget(self._experiment_select_page)

    def _on_mode_selected(self, mode_str: str) -> None:
        """User clicked Continue on ExperimentSelect; query firmware settings."""
        self._active_mode = mode_str
        self._get_buffer.clear()
        self._link.line_received.connect(self._on_get_response)
        self._link.send("get")

    def _on_get_response(self, line: str) -> None:
        self._get_buffer.append(line)
        settings = parse_get_response(self._get_buffer)
        if settings is None:
            return
        self._link.line_received.disconnect(self._on_get_response)
        self._get_buffer.clear()
        self._mode_config_page.setup(self._link, self._active_mode, settings)
        self._settings_label.setText(_format_settings(self._active_mode, settings))
        self._stack.setCurrentWidget(self._mode_config_page)

    def _on_mode_confirmed(self, mode_str: str, settings: dict) -> None:
        self._active_mode = mode_str
        self._settings_label.setText(_format_settings(mode_str, settings))
        palette = _PALETTE[_color_pair(mode_str)]
        self._active_palette = palette

        if _exp_type(mode_str) == "behavioral":
            self._behavioral_session_page.set_participant(self._folder, self._sub_id, self._group)
            self._behavioral_session_page.start_session(self._link, mode_str, settings, palette)
            self._stack.setCurrentWidget(self._behavioral_session_page)
        else:
            self._grid_session_page.set_participant(self._folder, self._sub_id, self._group)
            self._grid_session_page.start_session(self._link, mode_str, settings, palette)
            self._stack.setCurrentWidget(self._grid_session_page)

    def _on_back_requested(self) -> None:
        self._stack.setCurrentWidget(self._experiment_select_page)

    # --- Color theming -------------------------------------------------------

    def _on_color_mode_changed(self, color_pair: str) -> None:
        primary = _PALETTE[color_pair]["primary"] if color_pair in _PALETTE else _NEUTRAL_PRIMARY
        _apply_style(primary)
