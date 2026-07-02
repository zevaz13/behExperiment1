"""Sub-mode A (Solid) view: 5 LED sliders + optional hue panel.

Solid has no config screen (see design spec); MainWindow sends MODE SOLID
(+ SET hue 1, if chosen on ModeSelectPage) and START before switching here, so
sliders are live immediately. Each slider sends SET <COLOR>LED <value> on
change. Incoming FRAME@ lines drive the hue bar plot and, while hue is active,
append a snapshot row every time Press=1 to both an in-memory log (the full
frame -- all LED values and hue params, saveable via "Save press data...")
and a visible press-count/table panel. "Save figure..." exports the hue plot.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from pyqtgraph import BarGraphItem, PlotWidget

from figure_export import save_plot_widgets
from param_form import LED_COLORS
from protocol import FRAME_FIELDS, build_set_command, parse_frame
from serial_link import SerialLink

LED_ORDER = ("RED", "YELLOW", "GREEN", "BLUE", "CYAN")
_SET_KEY = {led: f"{led}LED" for led in LED_ORDER}

_DEFAULT_HUE_SCALE = 1000

# M9.2: a fast slider drag can fire dozens of valueChanged events per second; sending
# a SET for each one floods the serial link and makes everything feel laggy. Debounce
# to one SET per pause in motion, and throttle the hue plot's redraw rate similarly.
_SET_DEBOUNCE_MS = 50
_HUE_REFRESH_MS = 300


class _LedColumn(QWidget):
    """One LED's color swatch, vertical slider, and synced value spinbox.

    value_changed is debounced: rapid changes (e.g. a slider drag) collapse
    into a single emission ~_SET_DEBOUNCE_MS after motion pauses, so the
    caller doesn't flood the serial link with a SET per pixel of drag.
    """

    value_changed = Signal(str, int)  # led, value

    def __init__(self, led: str, color: str, parent=None) -> None:
        super().__init__(parent)
        self._led = led
        self._pending_value = 0

        swatch = QLabel()
        swatch.setFixedSize(32, 20)
        swatch.setStyleSheet(f"background: {color}; border: 1px solid #333;")

        self._slider = QSlider(Qt.Vertical)
        self._slider.setRange(0, 4095)
        self._slider.setMinimumHeight(180)

        self._spin = QSpinBox()
        self._spin.setRange(0, 4095)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(_SET_DEBOUNCE_MS)
        self._debounce.timeout.connect(self._emit_pending)

        self._slider.valueChanged.connect(self._spin.setValue)
        self._spin.valueChanged.connect(self._slider.setValue)
        self._spin.valueChanged.connect(self._on_value_changed)

        layout = QVBoxLayout(self)
        layout.addWidget(swatch, alignment=Qt.AlignHCenter)
        layout.addWidget(self._slider, alignment=Qt.AlignHCenter)
        layout.addWidget(self._spin, alignment=Qt.AlignHCenter)

    def _on_value_changed(self, value: int) -> None:
        self._pending_value = value
        self._debounce.start()  # restarts the countdown if already running

    def _emit_pending(self) -> None:
        self.value_changed.emit(self._led, self._pending_value)

    def set_value_quiet(self, value: int) -> None:
        """Updates the displayed value without emitting value_changed (e.g. from a frame)."""
        self._spin.blockSignals(True)
        self._slider.blockSignals(True)
        self._spin.setValue(value)
        self._slider.setValue(value)
        self._spin.blockSignals(False)
        self._slider.blockSignals(False)

    def value(self) -> int:
        return self._spin.value()


class SolidView(QWidget):
    """5 LED sliders, optional hue bar plot, and a Back button."""

    back_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._link: SerialLink | None = None
        self._hue_enabled = False
        self._press_log: list[dict] = []
        self._latest_hue: tuple[int, int, int] | None = None

        self._hue_refresh_timer = QTimer(self)
        self._hue_refresh_timer.setInterval(_HUE_REFRESH_MS)
        self._hue_refresh_timer.timeout.connect(self._flush_hue_bars)

        self._columns: dict[str, _LedColumn] = {}
        sliders_row = QHBoxLayout()
        for led in LED_ORDER:
            col = _LedColumn(led, LED_COLORS[led])
            col.value_changed.connect(self._on_slider_changed)
            self._columns[led] = col
            sliders_row.addWidget(col)

        self._hue_plot = PlotWidget()
        self._hue_plot.setBackground("k")
        self._hue_plot.setFixedWidth(220)
        self._hue_plot.getAxis("bottom").setTicks([[(0, "R"), (1, "G"), (2, "B")]])
        self._hue_bars = BarGraphItem(
            x=[0, 1, 2], height=[0, 0, 0], width=0.6,
            brushes=[LED_COLORS["RED"], LED_COLORS["GREEN"], LED_COLORS["BLUE"]],
        )
        self._hue_plot.addItem(self._hue_bars)
        # Fixed range instead of pyqtgraph's default auto-range: auto-range re-tweens
        # the view toward a new target on every incoming frame, which both looks like
        # the bars are perpetually still settling and (via the resulting axis-label
        # width churn) drags the slider column's rendered size around too.
        self._hue_plot.setXRange(-0.6, 2.6, padding=0)
        self._hue_plot.setYRange(0, _DEFAULT_HUE_SCALE, padding=0)
        self._hue_plot.setVisible(False)

        self._hue_scale_spin = QSpinBox()
        self._hue_scale_spin.setRange(1, 65535)
        self._hue_scale_spin.setValue(_DEFAULT_HUE_SCALE)
        self._hue_scale_spin.valueChanged.connect(self._on_hue_scale_changed)
        self._hue_controls = QWidget()
        scale_row = QHBoxLayout(self._hue_controls)
        scale_row.addWidget(QLabel("Hue scale max:"))
        scale_row.addWidget(self._hue_scale_spin)
        self._hue_controls.setVisible(False)

        self._press_count_label = QLabel("Presses: 0")
        self._press_table = QTableWidget(0, 4)
        self._press_table.setHorizontalHeaderLabels(["Press #", "R", "G", "B"])
        self._press_table.verticalHeader().setVisible(False)
        self._press_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._press_table.setMaximumHeight(160)
        save_figure_btn = QPushButton("Save figure...")
        save_figure_btn.clicked.connect(self._on_save_figure)
        save_press_btn = QPushButton("Save press data...")
        save_press_btn.clicked.connect(self._on_save_press_log)
        hue_save_row = QHBoxLayout()
        hue_save_row.addWidget(save_figure_btn)
        hue_save_row.addWidget(save_press_btn)
        self._press_panel = QWidget()
        press_col = QVBoxLayout(self._press_panel)
        press_col.addWidget(self._press_count_label)
        press_col.addWidget(self._press_table)
        press_col.addLayout(hue_save_row)
        self._press_panel.setVisible(False)

        back_btn = QPushButton("Back to mode selection")
        back_btn.clicked.connect(self.back_requested)

        hue_col = QVBoxLayout()
        hue_col.addWidget(self._hue_controls)
        hue_col.addWidget(self._hue_plot)
        hue_col.addWidget(self._press_panel)

        body = QHBoxLayout()
        body.addLayout(sliders_row, stretch=1)
        body.addLayout(hue_col)

        layout = QVBoxLayout(self)
        layout.addLayout(body, stretch=1)
        layout.addWidget(back_btn)

    def start_session(self, link: SerialLink, hue_enabled: bool) -> None:
        self.detach()
        self._link = link
        self._link.line_received.connect(self._on_line)
        self._hue_enabled = hue_enabled
        self._press_log.clear()
        self._latest_hue = None
        self._hue_plot.setVisible(hue_enabled)
        self._hue_controls.setVisible(hue_enabled)
        self._press_panel.setVisible(hue_enabled)
        self._press_count_label.setText("Presses: 0")
        self._press_table.setRowCount(0)
        if hue_enabled:
            self._hue_refresh_timer.start()
        else:
            self._hue_refresh_timer.stop()
        for col in self._columns.values():
            col.set_value_quiet(0)

    def detach(self) -> None:
        """Disconnect from the link so a hidden view stops consuming the stream."""
        self._hue_refresh_timer.stop()
        if self._link is not None:
            try:
                self._link.line_received.disconnect(self._on_line)
            except (RuntimeError, TypeError):
                pass
            self._link = None

    def _on_slider_changed(self, led: str, value: int) -> None:
        if self._link is not None:
            self._link.send(build_set_command({_SET_KEY[led]: value}))

    def _on_hue_scale_changed(self, value: int) -> None:
        self._hue_plot.setYRange(0, value, padding=0)

    def _flush_hue_bars(self) -> None:
        if self._latest_hue is not None:
            self._hue_bars.setOpts(height=list(self._latest_hue))

    def _on_line(self, line: str) -> None:
        frame = parse_frame(line)
        if frame is None:
            return
        for led in LED_ORDER:
            self._columns[led].set_value_quiet(frame[led.capitalize()])
        if not self._hue_enabled:
            return
        # Cache the latest reading; _flush_hue_bars applies it on a slower,
        # fixed cadence so the plot isn't redrawn on every 100ms frame.
        self._latest_hue = (frame["HUE_R"], frame["HUE_G"], frame["HUE_B"])
        if frame["Press"] == 1:
            self._press_log.append(dict(frame))
            self._add_press_row(frame)

    def _on_save_figure(self) -> None:
        default_name = f"solidhue_figure_{datetime.now():%Y%m%d_%H%M%S}.png"
        save_plot_widgets(self, {"hue": self._hue_plot}, default_name)

    def _on_save_press_log(self) -> None:
        """Writes the full per-press record (all LED values + hue params, not
        just the R/G/B columns shown in the table) to a text file, same
        space-separated FRAME_FIELDS format as the Linear/Grid hue logs."""
        if not self._press_log:
            return
        default_name = f"solidhue_presses_{datetime.now():%Y%m%d_%H%M%S}.txt"
        path, _ = QFileDialog.getSaveFileName(self, "Save press data", default_name, "Text files (*.txt)")
        if not path:
            return
        with open(path, "w") as f:
            f.write(" ".join(FRAME_FIELDS) + "\n")
            for frame in self._press_log:
                f.write(" ".join(str(frame[field]) for field in FRAME_FIELDS) + "\n")

    def _add_press_row(self, frame: dict) -> None:
        row = self._press_table.rowCount()
        self._press_table.insertRow(row)
        for col, val in enumerate((row + 1, frame["HUE_R"], frame["HUE_G"], frame["HUE_B"])):
            self._press_table.setItem(row, col, QTableWidgetItem(str(val)))
        self._press_table.scrollToBottom()
        self._press_count_label.setText(f"Presses: {row + 1}")
