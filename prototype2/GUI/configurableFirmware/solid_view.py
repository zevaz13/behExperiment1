"""Sub-mode A (Solid) view: 5 LED sliders + optional hue panel.

Solid has no config screen (see design spec); MainWindow sends MODE SOLID
(+ SET hue 1, if chosen on ModeSelectPage) and START before switching here, so
sliders are live immediately. Each slider sends SET <COLOR>LED <value> on
change. Incoming FRAME@ lines drive the hue bar plot and, while hue is active,
append a snapshot row every time Press=1 (for saving later, once that
milestone lands).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QSpinBox, QVBoxLayout, QWidget
from pyqtgraph import BarGraphItem, PlotWidget

from protocol import build_set_command, parse_frame
from serial_link import SerialLink

LED_ORDER = ("RED", "YELLOW", "GREEN", "BLUE", "CYAN")
LED_COLORS = {
    "RED": "#f70404",
    "YELLOW": "#fabd04",
    "GREEN": "#b1ff01",
    "BLUE": "#0493ff",
    "CYAN": "#50fefe",
}
_SET_KEY = {led: f"{led}LED" for led in LED_ORDER}

_DEFAULT_HUE_SCALE = 1000


class _LedColumn(QWidget):
    """One LED's color swatch, vertical slider, and synced value spinbox."""

    value_changed = Signal(str, int)  # led, value

    def __init__(self, led: str, color: str, parent=None) -> None:
        super().__init__(parent)
        self._led = led

        swatch = QLabel()
        swatch.setFixedSize(32, 20)
        swatch.setStyleSheet(f"background: {color}; border: 1px solid #333;")

        self._slider = QSlider(Qt.Vertical)
        self._slider.setRange(0, 4095)
        self._slider.setMinimumHeight(180)

        self._spin = QSpinBox()
        self._spin.setRange(0, 4095)

        self._slider.valueChanged.connect(self._spin.setValue)
        self._spin.valueChanged.connect(self._slider.setValue)
        self._spin.valueChanged.connect(self._on_value_changed)

        layout = QVBoxLayout(self)
        layout.addWidget(swatch, alignment=Qt.AlignHCenter)
        layout.addWidget(self._slider, alignment=Qt.AlignHCenter)
        layout.addWidget(self._spin, alignment=Qt.AlignHCenter)

    def _on_value_changed(self, value: int) -> None:
        self.value_changed.emit(self._led, value)

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

        back_btn = QPushButton("Back to mode selection")
        back_btn.clicked.connect(self.back_requested)

        hue_col = QVBoxLayout()
        hue_col.addWidget(self._hue_controls)
        hue_col.addWidget(self._hue_plot)

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
        self._hue_plot.setVisible(hue_enabled)
        self._hue_controls.setVisible(hue_enabled)
        for col in self._columns.values():
            col.set_value_quiet(0)

    def detach(self) -> None:
        """Disconnect from the link so a hidden view stops consuming the stream."""
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

    def _on_line(self, line: str) -> None:
        frame = parse_frame(line)
        if frame is None:
            return
        for led in LED_ORDER:
            self._columns[led].set_value_quiet(frame[led.capitalize()])
        if not self._hue_enabled:
            return
        self._hue_bars.setOpts(height=[frame["HUE_R"], frame["HUE_G"], frame["HUE_B"]])
        if frame["Press"] == 1:
            self._press_log.append(dict(frame))
