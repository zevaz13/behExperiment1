"""Sub-mode B (Linear) views: config screen + experiment (session) screen.

Config screen: a ParamForm pre-filled from the firmware's GET response, with
Load/Save JSON buttons (edit the form directly = "configure"; Load = "load
experimental setup") and a Start button. Session screen: progress bar,
trial/total label, config summary, and (only if hue was enabled) a growing
cumulative R/G/B time-series plot plus a mean-per-step plot, with all frames
logged to a .txt file while hue is active.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Signal
from pyqtgraph import PlotWidget, mkPen

from config_io import load_config, save_config
from param_form import ParamForm, format_led_assignments
from protocol import FRAME_FIELDS, parse_frame
from serial_link import SerialLink

LINEAR_PARAM_KEYS = [
    "freq", "trialLength", "interTrialWait", "steps",
    "nBaselinesStart", "nBaselinesEnd",
    "LEDA", "maxA", "minA",
    "bgStim1Led", "bgStim1Int", "bgStim2Led", "bgStim2Int",
    "ref1Led", "ref1Int", "ref2Led", "ref2Int", "ref3Led", "ref3Int",
    "baselineLed1", "baselineLed1Val", "baselineLed2", "baselineLed2Val",
    "baselineLed3", "baselineLed3Val",
    "hue",
]

_RGB_PENS = {"Red": mkPen("#f70404"), "Green": mkPen("#b1ff01"), "Blue": mkPen("#0493ff")}


def _is_baseline_trial(trial: int) -> bool:
    return trial >= 1001


# ---------------------------------------------------------------------------
# LinearConfigPage
# ---------------------------------------------------------------------------

class LinearConfigPage(QWidget):
    """Load-or-configure screen for Linear mode."""

    start_requested = Signal()
    back_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._baseline: dict[str, str] = {}
        self._hue_log_path: Path | None = None

        self._form = ParamForm(LINEAR_PARAM_KEYS)

        # Data saving is opt-in: hue can be on just to watch the live plots
        # without necessarily wanting a file written every session.
        self._save_hue_checkbox = QCheckBox("Save hue data to file")
        self._save_hue_checkbox.setEnabled(False)
        self._form._widgets["hue"].toggled.connect(self._save_hue_checkbox.setEnabled)

        load_btn = QPushButton("Load config...")
        load_btn.clicked.connect(self._on_load)
        save_btn = QPushButton("Save config...")
        save_btn.clicked.connect(self._on_save)
        start_btn = QPushButton("Start")
        start_btn.clicked.connect(self._on_start)
        back_btn = QPushButton("Back to mode selection")
        back_btn.clicked.connect(self.back_requested)

        btn_row = QHBoxLayout()
        btn_row.addWidget(load_btn)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(start_btn)
        btn_row.addWidget(back_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Linear mode configuration"))
        layout.addWidget(self._form)
        layout.addWidget(self._save_hue_checkbox)
        layout.addLayout(btn_row)

    def setup(self, settings: dict[str, str]) -> None:
        self._baseline = settings
        self._hue_log_path = None
        self._form.set_values(settings)
        self._save_hue_checkbox.setEnabled(bool(self._form.values().get("hue")))

    def _on_load(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load Linear config", "", "JSON files (*.json)")
        if path:
            self._form.set_values({k: str(v) for k, v in load_config(Path(path)).items()})

    def _on_save(self) -> None:
        default_name = f"linearParamConfig_{datetime.now():%Y%m%d_%H%M%S}.json"
        path, _ = QFileDialog.getSaveFileName(self, "Save Linear config", default_name, "JSON files (*.json)")
        if path:
            save_config(Path(path), self._form.values())

    def _on_start(self) -> None:
        self._hue_log_path = None
        if self._form.values().get("hue") and self._save_hue_checkbox.isChecked():
            default_name = f"linearhue_exp_{datetime.now():%Y%m%d_%H%M%S}.txt"
            path, _ = QFileDialog.getSaveFileName(self, "Save hue data log", default_name, "Text files (*.txt)")
            if path:
                self._hue_log_path = Path(path)
        self.start_requested.emit()

    def changed_values(self) -> dict[str, int | str]:
        return self._form.changed_values(self._baseline)

    def full_settings(self) -> dict[str, str]:
        changed = {k: str(v) for k, v in self.changed_values().items()}
        return {**self._baseline, **changed}

    def hue_log_path(self) -> Path | None:
        return self._hue_log_path

    def detach(self) -> None:
        pass  # nothing attached to a link — config screen only reads GET once at setup()


# ---------------------------------------------------------------------------
# LinearSessionPage
# ---------------------------------------------------------------------------

class LinearSessionPage(QWidget):
    """Progress bar, config summary, and conditional hue plots for a Linear run."""

    back_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._link: SerialLink | None = None
        self._settings: dict[str, str] = {}
        self._hue_enabled = False
        self._log_file = None

        self._total_trials = 0
        self._seen_trials: set[int] = set()
        self._last_trial: int | None = None
        self._trial_hue_samples: list[tuple[int, int, int]] = []

        self._cum_x: list[int] = []
        self._cum: dict[str, list[int]] = {"Red": [], "Green": [], "Blue": []}
        self._mean_x: list[int] = []
        self._mean: dict[str, list[float]] = {"Red": [], "Green": [], "Blue": []}

        self._params_label = QLabel("")
        self._params_label.setWordWrap(True)
        self._status_label = QLabel("Not started")
        self._rep_label = QLabel("Trial 0 / 0")
        self._progress = QProgressBar()

        stop_btn = QPushButton("Stop")
        stop_btn.clicked.connect(self._stop)
        back_btn = QPushButton("Back to mode selection")
        back_btn.clicked.connect(self.back_requested)
        btn_row = QHBoxLayout()
        btn_row.addWidget(stop_btn)
        btn_row.addWidget(back_btn)

        self._cum_plot = PlotWidget()
        self._cum_plot.setBackground("k")
        self._cum_plot.setTitle("Hue — cumulative (per frame)")
        self._cum_curves = {c: self._cum_plot.plot([], [], pen=_RGB_PENS[c]) for c in ("Red", "Green", "Blue")}

        self._mean_plot = PlotWidget()
        self._mean_plot.setBackground("k")
        self._mean_plot.setTitle("Hue — mean per step")
        self._mean_curves = {
            c: self._mean_plot.plot([], [], pen=_RGB_PENS[c], symbol="o") for c in ("Red", "Green", "Blue")
        }

        self._hue_widget = QWidget()
        hue_row = QHBoxLayout(self._hue_widget)
        hue_row.addWidget(self._cum_plot)
        hue_row.addWidget(self._mean_plot)
        self._hue_widget.setVisible(False)

        layout = QVBoxLayout(self)
        layout.addWidget(self._params_label)
        layout.addLayout(btn_row)
        layout.addWidget(self._status_label)
        layout.addWidget(self._rep_label)
        layout.addWidget(self._progress)
        layout.addWidget(self._hue_widget, stretch=1)

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
        steps = int(settings.get("steps", 10))
        self._total_trials = n_start + steps + n_end
        self._seen_trials = set()
        self._last_trial = None
        self._trial_hue_samples = []
        self._cum_x = []
        self._cum = {"Red": [], "Green": [], "Blue": []}
        self._mean_x = []
        self._mean = {"Red": [], "Green": [], "Blue": []}
        for curve in {**self._cum_curves, **self._mean_curves}.values():
            curve.setData([], [])

        self._progress.setRange(0, self._total_trials)
        self._progress.setValue(0)
        self._rep_label.setText(f"Trial 0 / {self._total_trials}")
        self._status_label.setText("Running...")

        led_a = settings.get("LEDA", "NONE")
        self._params_label.setText(
            f"LINEAR | freq={settings.get('freq', '?')}Hz | "
            f"LEDA ({led_a}) [{settings.get('minA', '?')}-{settings.get('maxA', '?')}] | "
            f"steps={steps} | baselines {n_start}/{n_end} | "
            f"hue={'on' if self._hue_enabled else 'off'} | "
            f"{format_led_assignments(settings)}"
        )
        self._hue_widget.setVisible(self._hue_enabled)

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

    def _stop(self) -> None:
        if self._link is not None:
            self._link.send("STOP")
        self._flush_trial_mean()
        self._status_label.setText("Stopped")

    def _flush_trial_mean(self) -> None:
        if not self._trial_hue_samples or self._last_trial is None or _is_baseline_trial(self._last_trial):
            self._trial_hue_samples = []
            return
        n = len(self._trial_hue_samples)
        rs, gs, bs = (sum(v) / n for v in zip(*self._trial_hue_samples))
        self._mean_x.append(self._last_trial)
        for name, val in (("Red", rs), ("Green", gs), ("Blue", bs)):
            self._mean[name].append(val)
            self._mean_curves[name].setData(self._mean_x, self._mean[name])
        self._trial_hue_samples = []

    def _on_line(self, line: str) -> None:
        if line.startswith("ERR "):
            self._status_label.setText(line)
            return
        frame = parse_frame(line)
        if frame is None:
            return

        trial = frame["TrialNumber"]
        if trial != self._last_trial:
            self._flush_trial_mean()
            self._last_trial = trial
        self._seen_trials.add(trial)
        completed = min(len(self._seen_trials), self._total_trials)
        self._progress.setValue(completed)
        self._rep_label.setText(f"Trial {completed} / {self._total_trials}")

        if not self._hue_enabled:
            return

        if frame["HUE_R"] != -99:
            idx = len(self._cum_x)
            self._cum_x.append(idx)
            for name in ("Red", "Green", "Blue"):
                self._cum[name].append(frame[f"HUE_{name[0]}"])
                self._cum_curves[name].setData(self._cum_x, self._cum[name])
            if not _is_baseline_trial(trial):
                self._trial_hue_samples.append((frame["HUE_R"], frame["HUE_G"], frame["HUE_B"]))

        if self._log_file is not None:
            self._log_file.write(" ".join(str(frame[f]) for f in FRAME_FIELDS) + "\n")
            self._log_file.flush()
