"""Sub-mode D (Behavioral) views: config screen + experiment (session) screen.

No hue, no baselines, no fixed trial count — the firmware runs indefinitely
until STOP. Session screen mirrors GUIsubjectExp's BehavioralSessionPage: a
live LEDA/LEDB scatter marker, a press table, and a rolling median. The GUI's
Press button and the physical button have identical effect (both drive the
firmware's PRESS/button path).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from statistics import median

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from pyqtgraph import PlotWidget

from config_io import load_config, save_config
from param_form import LED_FRAME_KEY, ParamForm, format_led_assignments
from protocol import parse_frame
from serial_link import SerialLink

BEHAVIORAL_PARAM_KEYS = [
    "freq", "interTrialWait",
    "LEDA", "maxA", "minA", "LEDB", "maxB", "minB",
    "bgStim1Led", "bgStim1Int", "bgStim2Led", "bgStim2Int",
    "ref1Led", "ref1Int", "ref2Led", "ref2Int", "ref3Led", "ref3Int",
]


# ---------------------------------------------------------------------------
# BehavioralConfigPage
# ---------------------------------------------------------------------------

class BehavioralConfigPage(QWidget):
    """Configure screen for Behavioral mode (no hue)."""

    start_requested = Signal()
    back_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._baseline: dict[str, str] = {}

        self._form = ParamForm(BEHAVIORAL_PARAM_KEYS)

        load_btn = QPushButton("Load config...")
        load_btn.clicked.connect(self._on_load)
        save_btn = QPushButton("Save config...")
        save_btn.clicked.connect(self._on_save)
        start_btn = QPushButton("Start")
        start_btn.clicked.connect(self.start_requested)
        back_btn = QPushButton("Back to mode selection")
        back_btn.clicked.connect(self.back_requested)
        btn_row = QHBoxLayout()
        btn_row.addWidget(load_btn)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(start_btn)
        btn_row.addWidget(back_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Behavioral mode configuration"))
        layout.addWidget(self._form)
        layout.addLayout(btn_row)

    def setup(self, settings: dict[str, str]) -> None:
        self._baseline = settings
        self._form.set_values(settings)

    def _on_load(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load Behavioral config", "", "JSON files (*.json)")
        if path:
            self._form.set_values({k: str(v) for k, v in load_config(Path(path)).items()})

    def _on_save(self) -> None:
        default_name = f"beh_configparams_{datetime.now():%Y%m%d_%H%M%S}.json"
        path, _ = QFileDialog.getSaveFileName(self, "Save Behavioral config", default_name, "JSON files (*.json)")
        if path:
            save_config(Path(path), self._form.values())

    def changed_values(self) -> dict[str, int | str]:
        return self._form.changed_values(self._baseline)

    def full_settings(self) -> dict[str, str]:
        changed = {k: str(v) for k, v in self.changed_values().items()}
        return {**self._baseline, **changed}

    def detach(self) -> None:
        pass  # nothing attached to a link — config screen only reads GET once at setup()


# ---------------------------------------------------------------------------
# BehavioralSessionPage
# ---------------------------------------------------------------------------

class BehavioralSessionPage(QWidget):
    """Live LEDA/LEDB scatter marker, press table, and rolling median."""

    back_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._link: SerialLink | None = None
        self._settings: dict[str, str] = {}
        self._led_a = "NONE"
        self._led_b = "NONE"
        self._press_a: list[int] = []
        self._press_b: list[int] = []
        self._press_count = 0

        self._params_label = QLabel("")
        self._params_label.setWordWrap(True)
        self._status_label = QLabel("Not started")

        press_btn = QPushButton("Press")
        press_btn.clicked.connect(self._press)
        stop_btn = QPushButton("Stop")
        stop_btn.clicked.connect(self._stop)
        back_btn = QPushButton("Back to mode selection")
        back_btn.clicked.connect(self.back_requested)
        btn_row = QHBoxLayout()
        btn_row.addWidget(press_btn)
        btn_row.addWidget(stop_btn)
        btn_row.addWidget(back_btn)

        self._plot = PlotWidget()
        self._plot.setBackground("k")
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
        self._table.setHorizontalHeaderLabels(["Press #", "A", "B"])
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._median_label = QLabel("Median: —")

        table_col = QVBoxLayout()
        table_col.addWidget(self._table)
        table_col.addWidget(self._median_label)

        plot_and_table = QHBoxLayout()
        plot_and_table.addWidget(self._plot, stretch=3)
        plot_and_table.addLayout(table_col, stretch=1)

        layout = QVBoxLayout(self)
        layout.addWidget(self._params_label)
        layout.addLayout(btn_row)
        layout.addWidget(self._status_label)
        layout.addLayout(plot_and_table)

    def start_session(self, link: SerialLink, settings: dict[str, str]) -> None:
        self.detach()
        self._link = link
        self._link.line_received.connect(self._on_line)
        self._settings = settings
        self._led_a = settings.get("LEDA", "NONE")
        self._led_b = settings.get("LEDB", "NONE")
        self._press_a.clear()
        self._press_b.clear()
        self._press_count = 0
        self._current_marker.setData([], [])
        self._press_marks.setData([], [])
        self._median_marker.setData([], [])
        self._table.setRowCount(0)
        self._table.setHorizontalHeaderLabels(["Press #", self._led_a, self._led_b])
        self._median_label.setText("Median: —")
        self._status_label.setText("Running...")

        min_a, max_a = int(settings.get("minA", 0)), int(settings.get("maxA", 4095))
        min_b, max_b = int(settings.get("minB", 0)), int(settings.get("maxB", 4095))
        self._plot.setLabel("bottom", f"LEDA ({self._led_a})")
        self._plot.setLabel("left", f"LEDB ({self._led_b})")
        self._plot.setXRange(min_a, max_a, padding=0.05)
        self._plot.setYRange(min_b, max_b, padding=0.05)

        self._params_label.setText(
            f"BEHAVIORAL | freq={settings.get('freq', '?')}Hz | "
            f"LEDA ({self._led_a}) [{min_a}-{max_a}] | LEDB ({self._led_b}) [{min_b}-{max_b}] | "
            f"{format_led_assignments(settings)}"
        )

    def detach(self) -> None:
        """Disconnect from the link so a hidden page is inert."""
        if self._link is not None:
            try:
                self._link.line_received.disconnect(self._on_line)
            except (RuntimeError, TypeError):
                pass
            self._link = None

    def _press(self) -> None:
        if self._link is not None:
            self._link.send("PRESS")

    def _stop(self) -> None:
        if self._link is not None:
            self._link.send("STOP")
        self._status_label.setText("Stopped")

    def _on_line(self, line: str) -> None:
        if line.startswith("ERR "):
            self._status_label.setText(line)
            return
        frame = parse_frame(line)
        if frame is None:
            return

        a_key = LED_FRAME_KEY.get(self._led_a)
        b_key = LED_FRAME_KEY.get(self._led_b)
        if a_key is None or b_key is None:
            return
        a_val, b_val = frame[a_key], frame[b_key]
        self._current_marker.setData([a_val], [b_val])

        if frame["Press"] == 1:
            self._press_count += 1
            self._press_a.append(a_val)
            self._press_b.append(b_val)
            self._press_marks.setData(self._press_a, self._press_b)
            med_a, med_b = median(self._press_a), median(self._press_b)
            self._median_marker.setData([med_a], [med_b])
            self._median_label.setText(f"Median  {self._led_a}: {med_a:g}  {self._led_b}: {med_b:g}")
            row = self._table.rowCount()
            self._table.insertRow(row)
            for col, val in enumerate((self._press_count, a_val, b_val)):
                self._table.setItem(row, col, QTableWidgetItem(str(val)))
            self._table.scrollToBottom()
