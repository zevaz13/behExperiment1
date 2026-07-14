"""Sub-mode C (Grid) views: config screen + experiment (session) screen.

Same load-or-configure config pattern as Linear, plus LEDB/maxB/minB/order.
Session screen layout (M13.3): a square visited/current-point scatter plot
(x = LEDA, y = LEDB, axes labeled with the assigned LED names) on the left,
mirroring GUIsubjectExp's GridSessionPage; a thin cumulative-hue plot stacked
over a thin mean-per-step plot on the right, spanning the same height as the
grid; and, below both, one small per-cell heatmap per hue channel (R/G/B),
each cell showing that (LEDA, LEDB) grid point's mean-per-step value, filled
in as stim trials complete. Progress counting and hue-log-file writing are
otherwise the same approach as Linear.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Signal
from pyqtgraph import ColorMap, ImageItem, PlotWidget, ScatterPlotItem, mkBrush, mkPen

from config_io import load_config, save_config
from figure_export import save_plot_widgets
from param_form import LED_FRAME_KEY, ParamForm, PhaseDiagram, SavingSection, format_led_assignments
from protocol import FRAME_FIELDS, parse_frame
from serial_link import SerialLink

GRID_PARAM_KEYS = [
    "freq", "trialLength", "interTrialWait", "steps", "order",
    "nBaselinesStart", "nBaselinesEnd",
    "LEDA", "maxA", "minA", "LEDB", "maxB", "minB",
    "bgStim1Led", "bgStim1Int", "bgStim2Led", "bgStim2Int",
    "ref1Led", "ref1Int", "ref2Led", "ref2Int", "ref3Led", "ref3Int",
    "baselineLed1", "baselineLed1Val", "baselineLed2", "baselineLed2Val",
    "baselineLed3", "baselineLed3Val",
    "hue",
]

_RGB_PENS = {"Red": mkPen("#f70404"), "Green": mkPen("#b1ff01"), "Blue": mkPen("#0493ff")}

_CONFIG_PREFIX = "gridParamConfig"

_HEATMAP_COLORS = {"Red": "#DA2C43", "Green": "#ACE1AF", "Blue": "#89CFF0"}
_HEATMAP_CLIM = (0, 3500)


def _heat_colormap(hex_color: str) -> ColorMap:
    return ColorMap(pos=[0.0, 1.0], color=["#000000", hex_color])


def _is_baseline_trial(trial: int) -> bool:
    return trial >= 1001


def _linspace(lo: int, hi: int, n: int) -> list[int]:
    if n == 1:
        return [lo]
    return [lo + (hi - lo) * i // (n - 1) for i in range(n)]


def _nearest_index(levels: list[int], value: int) -> int:
    return min(range(len(levels)), key=lambda i: abs(levels[i] - value))


# ---------------------------------------------------------------------------
# GridConfigPage
# ---------------------------------------------------------------------------

class GridConfigPage(QWidget):
    """Load-or-configure screen for Grid mode."""

    start_requested = Signal()
    back_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._baseline: dict[str, str] = {}

        self._form = ParamForm(GRID_PARAM_KEYS)
        self._diagram = PhaseDiagram(self._form)

        # Data saving is opt-in: hue can be on just to watch the live plots
        # without necessarily wanting a file written every session.
        self._saving = SavingSection("grid")
        self._form._widgets["hue"].toggled.connect(self._saving.set_hue_enabled)

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
        layout.addWidget(QLabel("Grid mode configuration"))
        layout.addWidget(self._form)
        layout.addWidget(self._diagram)
        layout.addWidget(self._saving)
        layout.addLayout(btn_row)

    def setup(self, settings: dict[str, str]) -> None:
        self._baseline = settings
        self._saving.reset()
        self._form.set_values(settings)
        self._saving.set_hue_enabled(bool(self._form.values().get("hue")))

    def _on_load(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Grid config", "", f"Grid config ({_CONFIG_PREFIX}*.json)"
        )
        if not path:
            return
        if not Path(path).name.startswith(_CONFIG_PREFIX):
            QMessageBox.warning(self, "Wrong config file", f"Please select a {_CONFIG_PREFIX}*.json file.")
            return
        self._form.set_values({k: str(v) for k, v in load_config(Path(path)).items()})

    def _on_save(self) -> None:
        default_name = f"{_CONFIG_PREFIX}_{datetime.now():%Y%m%d_%H%M%S}.json"
        path, _ = QFileDialog.getSaveFileName(self, "Save Grid config", default_name, "JSON files (*.json)")
        if path:
            save_config(Path(path), self._form.values())

    def changed_values(self) -> dict[str, int | str]:
        return self._form.changed_values(self._baseline)

    def full_settings(self) -> dict[str, str]:
        changed = {k: str(v) for k, v in self.changed_values().items()}
        return {**self._baseline, **changed}

    def hue_log_path(self) -> Path | None:
        return self._saving.hue_log_path()

    def detach(self) -> None:
        pass  # nothing attached to a link — config screen only reads GET once at setup()


# ---------------------------------------------------------------------------
# GridSessionPage
# ---------------------------------------------------------------------------

class GridSessionPage(QWidget):
    """Progress bar, visited/current grid plot, and conditional hue plots for a Grid run."""

    back_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._link: SerialLink | None = None
        self._settings: dict[str, str] = {}
        self._hue_enabled = False
        self._log_file = None

        self._led_a = "NONE"
        self._led_b = "NONE"
        self._a_levels: list[int] = []
        self._b_levels: list[int] = []
        self._visited: set[tuple[int, int]] = set()
        self._current: tuple[int, int] | None = None
        self._steps = 0

        self._total_trials = 0
        self._n_start = 0
        self._n_end = 0
        self._n_exp = 0
        self._seen_trials: set[int] = set()
        self._last_trial: int | None = None
        self._trial_hue_samples: list[tuple[int, int, int]] = []
        self._mean_point_open = False

        self._cum_x: list[int] = []
        self._cum: dict[str, list[int]] = {"Red": [], "Green": [], "Blue": []}
        self._mean_x: list[int] = []
        self._mean: dict[str, list[float]] = {"Red": [], "Green": [], "Blue": []}
        self._heat_data: dict[str, np.ndarray] = {c: np.zeros((1, 1)) for c in ("Red", "Green", "Blue")}

        self._params_label = QLabel("")
        self._params_label.setWordWrap(True)
        self._status_label = QLabel("Not started")
        self._rep_label = QLabel("Trial 0 / 0")
        self._progress = QProgressBar()

        stop_btn = QPushButton("Stop")
        stop_btn.clicked.connect(self._stop)
        save_figure_btn = QPushButton("Save figure...")
        save_figure_btn.clicked.connect(self._on_save_figure)
        back_btn = QPushButton("Back to mode selection")
        back_btn.clicked.connect(self.back_requested)
        btn_row = QHBoxLayout()
        btn_row.addWidget(stop_btn)
        btn_row.addWidget(save_figure_btn)
        btn_row.addWidget(back_btn)

        self._grid_plot = PlotWidget()
        self._grid_plot.setBackground("k")
        # No aspect lock: it forces 1:1 unit-per-pixel scaling, which stretches
        # one axis past its requested range whenever minA-maxA and minB-maxB
        # spans don't match the widget's pixel proportions — fighting the
        # "exact axis limits" requirement below. Exact ranges win over the
        # squarish look from M13.3.
        self._scatter = ScatterPlotItem()
        self._grid_plot.addItem(self._scatter)

        self._cum_plot = PlotWidget()
        self._cum_plot.setBackground("k")
        self._cum_plot.setTitle("Hue — cumulative (per frame)")
        self._cum_curves = {c: self._cum_plot.plot([], [], pen=_RGB_PENS[c]) for c in ("Red", "Green", "Blue")}

        self._mean_plot = PlotWidget()
        self._mean_plot.setBackground("k")
        self._mean_plot.setTitle("Hue — mean per step")
        self._mean_curves = {c: self._mean_plot.plot([], [], pen=_RGB_PENS[c]) for c in ("Red", "Green", "Blue")}

        self._hue_col_widget = QWidget()
        hue_col = QVBoxLayout(self._hue_col_widget)
        hue_col.addWidget(self._cum_plot)
        hue_col.addWidget(self._mean_plot)
        self._hue_col_widget.setVisible(False)

        top_row = QHBoxLayout()
        top_row.addWidget(self._grid_plot, stretch=1)
        top_row.addWidget(self._hue_col_widget, stretch=1)

        self._heat_clim = _HEATMAP_CLIM
        self._heat_clim_spin = QSpinBox()
        self._heat_clim_spin.setRange(1, 65535)
        self._heat_clim_spin.setValue(_HEATMAP_CLIM[1])
        self._heat_clim_spin.valueChanged.connect(self._on_heat_clim_changed)
        heat_clim_row = QHBoxLayout()
        heat_clim_row.addWidget(QLabel("Heatmap color max:"))
        heat_clim_row.addWidget(self._heat_clim_spin)
        heat_clim_row.addStretch()

        self._heat_plots: dict[str, PlotWidget] = {}
        self._heat_images: dict[str, ImageItem] = {}
        heat_row = QHBoxLayout()
        for name in ("Red", "Green", "Blue"):
            heat_plot = PlotWidget()
            heat_plot.setBackground("k")
            heat_plot.setTitle(f"{name} — mean per cell")
            heat_plot.setAspectLocked(True)
            heat_plot.getPlotItem().hideAxis("left")
            heat_plot.getPlotItem().hideAxis("bottom")
            image = ImageItem()
            image.setColorMap(_heat_colormap(_HEATMAP_COLORS[name]))
            heat_plot.addItem(image)
            self._heat_plots[name] = heat_plot
            self._heat_images[name] = image
            heat_row.addWidget(heat_plot)

        self._heat_widget = QWidget()
        heat_col = QVBoxLayout(self._heat_widget)
        heat_col.addLayout(heat_clim_row)
        heat_col.addLayout(heat_row)
        self._heat_widget.setVisible(False)

        layout = QVBoxLayout(self)
        layout.addWidget(self._params_label)
        layout.addLayout(btn_row)
        layout.addWidget(self._status_label)
        layout.addWidget(self._rep_label)
        layout.addWidget(self._progress)
        layout.addLayout(top_row, stretch=2)
        layout.addWidget(self._heat_widget, stretch=1)

    def start_session(self, link: SerialLink, settings: dict[str, str], hue_log_path: Path | None) -> None:
        self.detach()
        self._link = link
        self._link.line_received.connect(self._on_line)
        self._settings = settings
        self._hue_enabled = str(settings.get("hue", "0")) in ("1", "True", "true")

        self._log_file = None
        if hue_log_path is not None:
            self._log_file = hue_log_path.open("w")
            self._log_file.write(" ".join(FRAME_FIELDS) + "\n")

        n_start = int(settings.get("nBaselinesStart", 0))
        n_end = int(settings.get("nBaselinesEnd", 0))
        self._steps = int(settings.get("steps", 10))
        self._n_start = n_start
        self._n_end = n_end
        self._n_exp = self._steps * self._steps
        self._total_trials = n_start + self._steps * self._steps + n_end
        self._seen_trials = set()
        self._last_trial = None
        self._trial_hue_samples = []
        self._mean_point_open = False
        self._cum_x = []
        self._cum = {"Red": [], "Green": [], "Blue": []}
        self._mean_x = []
        self._mean = {"Red": [], "Green": [], "Blue": []}
        for curve in {**self._cum_curves, **self._mean_curves}.values():
            curve.setData([], [])
        self._apply_mean_axis()
        self._heat_data = {c: np.zeros((self._steps, self._steps)) for c in ("Red", "Green", "Blue")}
        for name, image in self._heat_images.items():
            image.setImage(self._heat_data[name], levels=self._heat_clim)

        self._led_a = settings.get("LEDA", "NONE")
        self._led_b = settings.get("LEDB", "NONE")
        min_a, max_a = int(settings.get("minA", 0)), int(settings.get("maxA", 4095))
        min_b, max_b = int(settings.get("minB", 0)), int(settings.get("maxB", 4095))
        self._a_levels = _linspace(min_a, max_a, self._steps)
        self._b_levels = _linspace(min_b, max_b, self._steps)
        self._visited = set()
        self._current = None
        self._grid_plot.setLabel("bottom", f"LEDA ({self._led_a})")
        self._grid_plot.setLabel("left", f"LEDB ({self._led_b})")
        # Small padding (not 0) so the marker circles at the min/max edge
        # points aren't clipped by the axis border once visited.
        self._grid_plot.setXRange(min_a, max_a, padding=0.05)
        self._grid_plot.setYRange(min_b, max_b, padding=0.05)
        self._refresh_scatter()

        self._progress.setRange(0, self._total_trials)
        self._progress.setValue(0)
        self._rep_label.setText(f"Trial 0 / {self._total_trials}")
        self._status_label.setText("Running...")

        self._params_label.setText(
            f"GRID | freq={settings.get('freq', '?')}Hz | "
            f"LEDA ({self._led_a}) [{min_a}-{max_a}] | LEDB ({self._led_b}) [{min_b}-{max_b}] | "
            f"steps={self._steps} | order={settings.get('order', '?')} | "
            f"baselines {n_start}/{n_end} | hue={'on' if self._hue_enabled else 'off'} | "
            f"{format_led_assignments(settings)}"
        )
        self._hue_col_widget.setVisible(self._hue_enabled)
        self._heat_widget.setVisible(self._hue_enabled)

    def detach(self) -> None:
        """Disconnect from the link and close the hue log so a hidden page is inert."""
        if self._link is not None:
            try:
                self._link.line_received.disconnect(self._on_line)
            except (RuntimeError, TypeError):
                pass
            self._link = None
        if self._log_file is not None:
            self._log_file.close()
            self._log_file = None

    def set_status(self, text: str) -> None:
        self._status_label.setText(text)

    def _stop(self) -> None:
        if self._link is not None:
            self._link.send("STOP")
        self._status_label.setText("Stopped")

    def _on_heat_clim_changed(self, value: int) -> None:
        self._heat_clim = (0, value)
        for name, image in self._heat_images.items():
            image.setImage(self._heat_data[name], levels=self._heat_clim)

    def _on_save_figure(self) -> None:
        plots = {"grid": self._grid_plot}
        if self._hue_enabled:
            plots["hue_cumulative"] = self._cum_plot
            plots["hue_mean"] = self._mean_plot
            for name, heat_plot in self._heat_plots.items():
                plots[f"heat_{name.lower()}"] = heat_plot
        default_name = f"grid_figure_{datetime.now():%Y%m%d_%H%M%S}.png"
        save_plot_widgets(self, plots, default_name)

    def _refresh_scatter(self) -> None:
        spots = []
        for gi, b_val in enumerate(self._b_levels):
            for ai, a_val in enumerate(self._a_levels):
                key = (ai, gi)
                if key == self._current:
                    brush, size = mkBrush("#fabd04"), 20
                elif key in self._visited:
                    brush, size = mkBrush("#f70404"), 14
                else:
                    brush, size = mkBrush(70, 70, 70), 10
                spots.append({"pos": (a_val, b_val), "brush": brush, "size": size, "pen": None})
        self._scatter.setData(spots)

    def _mean_x_for(self, trial: int) -> int:
        """Map a trial number to its x-slot on the mean-per-step plot.

        Stimulus trials keep their number (1..N, N=steps*steps). Baselines get
        their own slots outside that range: start baselines at -n_start..-1
        (left of trial 1), end baselines at N+1..N+n_end (right of trial N).
        """
        if not _is_baseline_trial(trial):
            return trial
        idx = trial - 1001  # 0-based order across start-then-end baselines
        if idx < self._n_start:
            return idx - self._n_start
        return self._n_exp + 1 + (idx - self._n_start)

    def _apply_mean_axis(self) -> None:
        """Label baseline slots B1, B2, ... (globally, start then end) and the
        stimulus trials with their numbers (a capped subset when many)."""
        ticks = [(i - self._n_start, f"B{i + 1}") for i in range(self._n_start)]
        n = self._n_exp
        stride = max(1, n // 12)
        ticks += [(i, str(i)) for i in range(1, n + 1, stride)]
        ticks += [(n + 1 + e, f"B{self._n_start + e + 1}") for e in range(self._n_end)]
        self._mean_plot.getAxis("bottom").setTicks([ticks])

    def _update_mean_point(self) -> None:
        """Draw/refresh the current trial's mean point (and its heatmap cell)
        live, so the last trial (including an end baseline) is plotted without
        waiting for a next trial or a Stop. Opens the point on the trial's first
        hue sample and updates it in place as more samples arrive."""
        n = len(self._trial_hue_samples)
        if n == 0 or self._last_trial is None:
            return
        rs, gs, bs = (sum(v) / n for v in zip(*self._trial_hue_samples))
        if not self._mean_point_open:
            self._mean_x.append(self._mean_x_for(self._last_trial))
            for name, val in (("Red", rs), ("Green", gs), ("Blue", bs)):
                self._mean[name].append(val)
            self._mean_point_open = True
        else:
            for name, val in (("Red", rs), ("Green", gs), ("Blue", bs)):
                self._mean[name][-1] = val
        for name in ("Red", "Green", "Blue"):
            self._mean_curves[name].setData(self._mean_x, self._mean[name])
        # Heatmap cells are stimulus-only (baselines map to no grid cell).
        # `_current` is the current trial's cell — its Trigger=1 position update
        # runs earlier in the same _on_line call, before this hue block.
        if not _is_baseline_trial(self._last_trial) and self._current is not None:
            ai, bi = self._current
            for name, val in (("Red", rs), ("Green", gs), ("Blue", bs)):
                self._heat_data[name][ai, bi] = val
                self._heat_images[name].setImage(self._heat_data[name], levels=self._heat_clim)

    def _on_line(self, line: str) -> None:
        if line.startswith("ERR "):
            self._status_label.setText(line)
            return
        frame = parse_frame(line)
        if frame is None:
            return

        trial = frame["TrialNumber"]
        if trial != self._last_trial:
            self._last_trial = trial
            self._trial_hue_samples = []
            self._mean_point_open = False
        self._seen_trials.add(trial)
        completed = min(len(self._seen_trials), self._total_trials)
        self._progress.setValue(completed)
        self._rep_label.setText(f"Trial {completed} / {self._total_trials}")

        # Grid position only from active-presentation frames (Trigger=1) of stim
        # trials: during the ITI the firmware zeroes the LEDs, and baseline
        # trials (>=1001) don't correspond to a grid cell.
        if (
            frame["Trigger"] == 1
            and not _is_baseline_trial(trial)
            and self._led_a in LED_FRAME_KEY
            and self._led_b in LED_FRAME_KEY
        ):
            a_val = frame[LED_FRAME_KEY[self._led_a]]
            b_val = frame[LED_FRAME_KEY[self._led_b]]
            cell = (_nearest_index(self._a_levels, a_val), _nearest_index(self._b_levels, b_val))
            if cell != self._current:
                self._current = cell
                self._visited.add(cell)
                self._refresh_scatter()

        if not self._hue_enabled:
            return

        if frame["HUE_R"] != -99:
            idx = len(self._cum_x)
            self._cum_x.append(idx)
            for name in ("Red", "Green", "Blue"):
                self._cum[name].append(frame[f"HUE_{name[0]}"])
                self._cum_curves[name].setData(self._cum_x, self._cum[name])
            self._trial_hue_samples.append((frame["HUE_R"], frame["HUE_G"], frame["HUE_B"]))
            self._update_mean_point()

        if self._log_file is not None:
            self._log_file.write(" ".join(str(frame[f]) for f in FRAME_FIELDS) + "\n")
            self._log_file.flush()
