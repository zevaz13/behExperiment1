"""Shared parameter form for Linear/Grid/Behavioral config screens (M14).

`ParamForm` builds a `QGroupBox` per experiment stage (Timing/Stimulus/
Reference/Baseline/Hue) from an ordered key list, using `PARAM_SPEC` for each
key's widget kind, friendly label, unit, and stage. Naturally-paired firmware
params (a min/max range, or an LED assignment + its intensity) render as one
combined row instead of two. Every LED dropdown gets a color swatch and is
filtered against the other dropdowns in its `exclusion_group` so the same LED
can't be picked twice within one phase (stim/reference/baseline) — mirroring
the firmware's own validation, just applied before a command is even sent.

Values still round-trip as native Python types for both the firmware SET/GET
protocol (which uses strings) and JSON config files, via the same
`values()`/`set_values()`/`changed_values()` contract as before this
redesign — every widget is still registered individually in `self._widgets`
keyed by firmware param name, so callers (`linear_view.py` etc.) don't change.

`PhaseDiagram` and `SavingSection` are two small companion widgets used by the
Linear/Grid config pages alongside `ParamForm` (see their docstrings below).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

LED_NAMES = ("NONE", "RED", "YELLOW", "GREEN", "BLUE", "CYAN")

LED_COLORS = {
    "RED": "#f70404",
    "YELLOW": "#fabd04",
    "GREEN": "#b1ff01",
    "BLUE": "#0493ff",
    "CYAN": "#50fefe",
}

# Maps an assigned LED name to the FRAME@ column that carries its live intensity.
LED_FRAME_KEY = {"RED": "Red", "YELLOW": "Yellow", "GREEN": "Green", "BLUE": "Blue", "CYAN": "Cyan"}

# (led_key, value_key, phase_label) for every LED-role param outside LEDA/LEDB,
# used by format_led_assignments() to summarize what's attached to each phase,
# and by ParamForm to build combined LED+intensity rows (via _LED_PAIR_LABELS).
_LED_PHASE_FIELDS = (
    ("bgStim1Led", "bgStim1Int", "bgStim1"),
    ("bgStim2Led", "bgStim2Int", "bgStim2"),
    ("ref1Led", "ref1Int", "ref1"),
    ("ref2Led", "ref2Int", "ref2"),
    ("ref3Led", "ref3Int", "ref3"),
    ("baselineLed1", "baselineLed1Val", "baseline1"),
    ("baselineLed2", "baselineLed2Val", "baseline2"),
    ("baselineLed3", "baselineLed3Val", "baseline3"),
)

# led_key -> value_key, for building combined LED+intensity rows. The row's
# label comes from PARAM_SPEC[led_key].label, the same one used if the LED
# ever renders standalone (see _ROW_ORDER's bare fallback entries) — one
# source of truth for the label either way.
_LED_PAIR_BY_LED_KEY = {led_key: val_key for led_key, val_key, _phase in _LED_PHASE_FIELDS}

# (row_label, low_key, high_key) -> renders as one row: "label: [lo] to [hi]".
RANGE_PAIRS = [
    ("LEDA sweep range", "minA", "maxA"),
    ("LEDB sweep range", "minB", "maxB"),
]

# `order`'s firmware range is [0,4], but order 0 is identical to order 1 (no
# distinct meaning defined for 0 in gridMode.cpp) — the GUI only offers the 4
# meaningfully-distinct values.
_ORDER_LABELS = ["Standard", "Flip LEDB axis", "Flip LEDA axis", "Flip both axes"]
_ORDER_VALUES = [1, 2, 3, 4]


@dataclass(frozen=True)
class ParamMeta:
    kind: str  # "int" | "led" | "bool" | "order"
    span: tuple[int, int] | None  # (lo, hi) for "int"; unused otherwise
    label: str
    unit: str | None = None
    stage: str | None = None
    exclusion_group: str | None = None  # "stim" | "reference" | "baseline", "led" kind only


PARAM_SPEC: dict[str, ParamMeta] = {
    "freq":            ParamMeta("int", (1, 500), "Flicker frequency", unit="Hz", stage="Timing"),
    "trialLength":     ParamMeta("int", (200, 30000), "Stimulus duration", unit="ms", stage="Timing"),
    "interTrialWait":  ParamMeta("int", (50, 30000), "Inter-trial interval", unit="ms", stage="Timing"),
    "order":           ParamMeta("order", None, "Grid traversal order", stage="Timing"),
    "steps":           ParamMeta("int", (2, 50), "Number of steps", stage="Stimulus"),
    "nBaselinesStart": ParamMeta("int", (0, 50), "Baseline trials (start)", stage="Baseline"),
    "nBaselinesEnd":   ParamMeta("int", (0, 50), "Baseline trials (end)", stage="Baseline"),
    "maxA":            ParamMeta("int", (0, 4095), "LEDA max", stage="Stimulus"),
    "minA":            ParamMeta("int", (0, 4095), "LEDA min", stage="Stimulus"),
    "maxB":            ParamMeta("int", (0, 4095), "LEDB max", stage="Stimulus"),
    "minB":            ParamMeta("int", (0, 4095), "LEDB min", stage="Stimulus"),
    "LEDA":            ParamMeta("led", None, "Primary LED (LEDA)", stage="Stimulus", exclusion_group="stim"),
    "LEDB":            ParamMeta("led", None, "Secondary LED (LEDB)", stage="Stimulus", exclusion_group="stim"),
    "bgStim1Led":      ParamMeta("led", None, "Background LED 1", stage="Stimulus", exclusion_group="stim"),
    "bgStim1Int":      ParamMeta("int", (0, 4095), "Background 1 intensity", stage="Stimulus"),
    "bgStim2Led":      ParamMeta("led", None, "Background LED 2", stage="Stimulus", exclusion_group="stim"),
    "bgStim2Int":      ParamMeta("int", (0, 4095), "Background 2 intensity", stage="Stimulus"),
    "ref1Led":         ParamMeta("led", None, "Reference LED 1", stage="Reference", exclusion_group="reference"),
    "ref1Int":         ParamMeta("int", (0, 4095), "Reference 1 intensity", stage="Reference"),
    "ref2Led":         ParamMeta("led", None, "Reference LED 2", stage="Reference", exclusion_group="reference"),
    "ref2Int":         ParamMeta("int", (0, 4095), "Reference 2 intensity", stage="Reference"),
    "ref3Led":         ParamMeta("led", None, "Reference LED 3", stage="Reference", exclusion_group="reference"),
    "ref3Int":         ParamMeta("int", (0, 4095), "Reference 3 intensity", stage="Reference"),
    "baselineLed1":    ParamMeta("led", None, "Baseline LED 1", stage="Baseline", exclusion_group="baseline"),
    "baselineLed1Val": ParamMeta("int", (0, 4095), "Baseline 1 intensity", stage="Baseline"),
    "baselineLed2":    ParamMeta("led", None, "Baseline LED 2", stage="Baseline", exclusion_group="baseline"),
    "baselineLed2Val": ParamMeta("int", (0, 4095), "Baseline 2 intensity", stage="Baseline"),
    "baselineLed3":    ParamMeta("led", None, "Baseline LED 3", stage="Baseline", exclusion_group="baseline"),
    "baselineLed3Val": ParamMeta("int", (0, 4095), "Baseline 3 intensity", stage="Baseline"),
    "hue":             ParamMeta("bool", None, "Enable hue sensor", stage="Hue"),
    "knobShuffle":     ParamMeta("bool", None, "Randomize knob-LED mapping", stage="Stimulus"),
}

# Fixed display order for every possible column, spanning all three modes.
# Compound entries ("led_range"/"range"/"led_pair") render as one combined
# column only if *all* of their keys are present; each is followed by its own
# keys as plain bare fallback entries, which render individually if the
# compound didn't fire (already-consumed keys are skipped, see
# ParamForm.__init__). Tried most- to least-specific: an LED+its own range
# ("led_range") before a bare range ("range", for min/max without the LED),
# before the individual keys. Every PARAM_SPEC key must appear here at least
# once — see test_offscreen.py's coverage check.
_ROW_ORDER: list = [
    "freq", "trialLength", "interTrialWait", "order",
    ("led_range", "LEDA", "minA", "maxA"), ("range", *RANGE_PAIRS[0]), "LEDA", "minA", "maxA",
    ("led_range", "LEDB", "minB", "maxB"), ("range", *RANGE_PAIRS[1]), "LEDB", "minB", "maxB",
    "steps",
    ("led_pair", "bgStim1Led"), "bgStim1Led", "bgStim1Int",
    ("led_pair", "bgStim2Led"), "bgStim2Led", "bgStim2Int",
    ("led_pair", "ref1Led"), "ref1Led", "ref1Int",
    ("led_pair", "ref2Led"), "ref2Led", "ref2Int",
    ("led_pair", "ref3Led"), "ref3Led", "ref3Int",
    "nBaselinesStart", "nBaselinesEnd",
    ("led_pair", "baselineLed1"), "baselineLed1", "baselineLed1Val",
    ("led_pair", "baselineLed2"), "baselineLed2", "baselineLed2Val",
    ("led_pair", "baselineLed3"), "baselineLed3", "baselineLed3Val",
    "hue", "knobShuffle",
]


def _wrap(layout) -> QWidget:
    layout.setContentsMargins(0, 0, 0, 0)
    widget = QWidget()
    widget.setLayout(layout)
    return widget


def _set_swatch(swatch: QLabel, led_name: str) -> None:
    color = LED_COLORS.get(led_name, "#222")
    swatch.setStyleSheet(f"background: {color}; border: 1px solid #333;")


class ParamForm(QWidget):
    """A stage-grouped set of param widgets for a given ordered key list.

    Each stage is a QGroupBox laid out as one horizontal row of labeled
    columns (not a vertical list) — e.g. Timing shows Frequency/Duration/ITI/
    Order side by side, and a LED + its own range (LEDA + min/max) sit
    together in a single column rather than stacked across two rows.
    """

    values_changed = Signal()

    def __init__(self, keys: list[str], parent=None) -> None:
        super().__init__(parent)
        self._keys = keys
        self._widgets: dict[str, QSpinBox | QComboBox | QCheckBox] = {}
        self._swatches: dict[str, QLabel] = {}
        self._exclusion_groups: dict[str, list[str]] = {}

        keyset = set(keys)
        consumed: set[str] = set()
        stage_rows: dict[str, QHBoxLayout] = {}
        layout = QVBoxLayout(self)

        def box_for(stage: str) -> QHBoxLayout:
            if stage not in stage_rows:
                group = QGroupBox(stage)
                stage_rows[stage] = QHBoxLayout(group)
                layout.addWidget(group)
            return stage_rows[stage]

        for entry in _ROW_ORDER:
            if isinstance(entry, tuple) and entry[0] == "led_range":
                _, led_key, lo_key, hi_key = entry
                if led_key in keyset and lo_key in keyset and hi_key in keyset:
                    box_for(PARAM_SPEC[led_key].stage).addWidget(self._led_range_column(led_key, lo_key, hi_key))
                    consumed |= {led_key, lo_key, hi_key}
            elif isinstance(entry, tuple) and entry[0] == "range":
                _, label, lo_key, hi_key = entry
                if lo_key in keyset and hi_key in keyset and lo_key not in consumed and hi_key not in consumed:
                    box_for(PARAM_SPEC[lo_key].stage).addWidget(self._range_column(label, lo_key, hi_key))
                    consumed |= {lo_key, hi_key}
            elif isinstance(entry, tuple) and entry[0] == "led_pair":
                led_key = entry[1]
                val_key = _LED_PAIR_BY_LED_KEY[led_key]
                if led_key in keyset and val_key in keyset:
                    box_for(PARAM_SPEC[led_key].stage).addWidget(self._led_pair_column(led_key, val_key))
                    consumed |= {led_key, val_key}
            elif entry in keyset and entry not in consumed:
                key = entry
                meta = PARAM_SPEC[key]
                widget = self._build_widget(key)
                widgets = (self._swatches[key], widget) if meta.kind == "led" else (widget,)
                box_for(meta.stage).addWidget(self._column(meta.label, *widgets))
                consumed.add(key)

        for row in stage_rows.values():
            row.addStretch()
        layout.addStretch()
        self._refresh_exclusions()

    # --- column layout ---------------------------------------------------------

    def _column(self, label: str, *widgets: QWidget) -> QWidget:
        """One labeled column: a caption on top, its widget(s) side by side below."""
        col = QVBoxLayout()
        caption = QLabel(label)
        caption.setStyleSheet("font-weight: bold;")
        col.addWidget(caption)
        row = QHBoxLayout()
        for w in widgets:
            row.addWidget(w)
        col.addLayout(row)
        return _wrap(col)

    # --- widget construction -------------------------------------------------

    def _build_widget(self, key: str) -> QSpinBox | QComboBox | QCheckBox:
        meta = PARAM_SPEC[key]
        if meta.kind == "int":
            widget = QSpinBox()
            lo, hi = meta.span
            widget.setRange(lo, hi)
            if meta.unit:
                widget.setSuffix(f" {meta.unit}")
            widget.valueChanged.connect(lambda *_: self.values_changed.emit())
        elif meta.kind == "led":
            widget = QComboBox()
            widget.addItems(LED_NAMES)
            swatch = QLabel()
            swatch.setFixedSize(14, 14)
            self._swatches[key] = swatch
            widget.currentTextChanged.connect(lambda text, s=swatch: _set_swatch(s, text))
            widget.currentTextChanged.connect(lambda *_: self.values_changed.emit())
            if meta.exclusion_group:
                self._exclusion_groups.setdefault(meta.exclusion_group, []).append(key)
                widget.currentTextChanged.connect(lambda *_: self._refresh_exclusions())
            _set_swatch(swatch, widget.currentText())
        elif meta.kind == "order":
            widget = QComboBox()
            widget.addItems(_ORDER_LABELS)
            widget.currentIndexChanged.connect(lambda *_: self.values_changed.emit())
        else:
            widget = QCheckBox()
            widget.toggled.connect(lambda *_: self.values_changed.emit())
        self._widgets[key] = widget
        return widget

    def _range_column(self, label: str, lo_key: str, hi_key: str) -> QWidget:
        lo_widget = self._build_widget(lo_key)
        hi_widget = self._build_widget(hi_key)
        return self._column(label, lo_widget, QLabel("to"), hi_widget)

    def _led_pair_column(self, led_key: str, val_key: str) -> QWidget:
        led_widget = self._build_widget(led_key)
        val_widget = self._build_widget(val_key)
        label = PARAM_SPEC[led_key].label
        return self._column(label, self._swatches[led_key], led_widget, QLabel("intensity"), val_widget)

    def _led_range_column(self, led_key: str, lo_key: str, hi_key: str) -> QWidget:
        led_widget = self._build_widget(led_key)
        lo_widget = self._build_widget(lo_key)
        hi_widget = self._build_widget(hi_key)
        label = PARAM_SPEC[led_key].label
        return self._column(
            label, self._swatches[led_key], led_widget, QLabel("range"), lo_widget, QLabel("to"), hi_widget
        )

    # --- LED exclusion filtering ----------------------------------------------

    def _refresh_exclusions(self) -> None:
        """Disables (greys out, doesn't remove) an LED in every other dropdown
        of the same exclusion_group once it's picked in one of them — a GUI
        convenience only; the firmware's own duplicate-LED rejection remains
        the actual source of truth and is unaffected by this."""
        for group_keys in self._exclusion_groups.values():
            combos = {k: self._widgets[k] for k in group_keys}
            selections = {k: c.currentText() for k, c in combos.items()}
            for key, combo in combos.items():
                taken_elsewhere = {v for ok, v in selections.items() if ok != key and v != "NONE"}
                model = combo.model()
                for i in range(combo.count()):
                    text = combo.itemText(i)
                    enabled = text == "NONE" or text == selections[key] or text not in taken_elsewhere
                    model.item(i).setEnabled(enabled)

    # --- value round-trip (unchanged contract) --------------------------------

    def set_values(self, values: dict[str, str]) -> None:
        """Populates widgets from a GET-response-style dict (string values)."""
        for key, widget in self._widgets.items():
            raw = values.get(key)
            if raw is None:
                continue
            kind = PARAM_SPEC[key].kind
            if kind == "int":
                widget.setValue(int(raw))
            elif kind == "led":
                idx = widget.findText(str(raw))
                if idx >= 0:
                    widget.setCurrentIndex(idx)
            elif kind == "order":
                order_value = int(raw)
                idx = _ORDER_VALUES.index(order_value) if order_value in _ORDER_VALUES else _ORDER_VALUES.index(1)
                widget.setCurrentIndex(idx)
            else:
                widget.setChecked(str(raw) in ("1", "True", "true"))
        self._refresh_exclusions()

    def values(self) -> dict[str, int | str]:
        """Returns the current value of every field, natively typed."""
        result: dict[str, int | str] = {}
        for key, widget in self._widgets.items():
            kind = PARAM_SPEC[key].kind
            if kind == "int":
                result[key] = widget.value()
            elif kind == "led":
                result[key] = widget.currentText()
            elif kind == "order":
                result[key] = _ORDER_VALUES[widget.currentIndex()]
            else:
                result[key] = 1 if widget.isChecked() else 0
        return result

    def changed_values(self, baseline: dict[str, str]) -> dict[str, int | str]:
        """Returns only the fields whose current value differs from `baseline`
        (a GET-response-style dict), for building a minimal SET command."""
        current = self.values()
        return {k: v for k, v in current.items() if str(v) != str(baseline.get(k, ""))}


def format_led_assignments(settings: dict) -> str:
    """Summarizes every non-NONE background/reference/baseline LED and its phase
    and value, e.g. "bgStim1: GREEN=1000 | ref1: YELLOW=2000". LEDA/LEDB are
    shown separately by each session page since they're always the headline params.
    """
    parts = []
    for led_key, val_key, phase in _LED_PHASE_FIELDS:
        led = settings.get(led_key, "NONE")
        if led != "NONE":
            parts.append(f"{phase}: {led}={settings.get(val_key, '?')}")
    return " | ".join(parts) if parts else "no background/reference/baseline LEDs set"


class PhaseDiagram(QWidget):
    """Live 'what's on in each phase' summary: colored chips for whatever's
    currently assigned to the Stim phase (LEDA/LEDB/backgrounds) and the
    Reference phase (ref1/2/3), refreshed from a ParamForm's values_changed
    signal. No Baseline panel — that trial type is a single solid display, not
    a two-phase flicker, and its own group box (with swatches already) is
    self-explanatory without a diagram.
    """

    _STIM_ROLES = [("LEDA", "LEDA"), ("LEDB", "LEDB"), ("bgStim1Led", "BG1"), ("bgStim2Led", "BG2")]
    _REFERENCE_ROLES = [("ref1Led", "Ref1"), ("ref2Led", "Ref2"), ("ref3Led", "Ref3")]

    def __init__(self, form: ParamForm, parent=None) -> None:
        super().__init__(parent)
        self._form = form

        self._stim_row = QHBoxLayout()
        self._reference_row = QHBoxLayout()
        stim_col = QVBoxLayout()
        stim_col.addWidget(QLabel("Stim"))
        stim_col.addLayout(self._stim_row)
        reference_col = QVBoxLayout()
        reference_col.addWidget(QLabel("Reference"))
        reference_col.addLayout(self._reference_row)

        box = QGroupBox("Phase preview")
        box_row = QHBoxLayout(box)
        box_row.addLayout(stim_col)
        box_row.addLayout(reference_col)

        layout = QVBoxLayout(self)
        layout.addWidget(box)

        form.values_changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        values = self._form.values()
        self._fill(self._stim_row, self._STIM_ROLES, values)
        self._fill(self._reference_row, self._REFERENCE_ROLES, values)

    @staticmethod
    def _fill(row: QHBoxLayout, roles: list[tuple[str, str]], values: dict) -> None:
        while row.count():
            item = row.takeAt(0)
            widget = item.widget()
            if widget:
                # setParent(None) detaches it from the visible tree immediately;
                # deleteLater() alone leaves it painted at its old geometry until
                # the event loop gets around to it, which can be many refreshes
                # later during a set_values() burst (one per changed LED field).
                widget.setParent(None)
                widget.deleteLater()
        chips = 0
        for key, role_label in roles:
            led = values.get(key, "NONE")
            if led == "NONE":
                continue
            chip = QLabel(f" {role_label}: {led} ")
            chip.setStyleSheet(f"background: {LED_COLORS[led]}; color: black; border-radius: 3px;")
            row.addWidget(chip)
            chips += 1
        if chips == 0:
            row.addWidget(QLabel("(none)"))
        row.addStretch()


class SavingSection(QWidget):
    """Experiment name + hue-data-saving destination for Linear/Grid, decided
    on the config screen instead of via popups at Start (M14). `_on_start()`
    no longer needs to show any dialog: `hue_log_path()` returns an explicitly
    browsed-to path if one was chosen, otherwise the same default filename
    pattern used before, computed silently.
    """

    def __init__(self, mode: str, parent=None) -> None:
        super().__init__(parent)
        self._mode = mode  # "linear" | "grid" -> used in the default filename
        self._explicit_path: Path | None = None

        self._save_checkbox = QCheckBox("Save hue data to file")
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("optional")
        self._path_label = QLabel("(default location)")
        choose_btn = QPushButton("Choose file...")
        choose_btn.clicked.connect(self._on_choose_file)

        path_row = QHBoxLayout()
        path_row.addWidget(self._path_label, stretch=1)
        path_row.addWidget(choose_btn)

        box = QGroupBox("Saving")
        form = QFormLayout(box)
        form.addRow(self._save_checkbox)
        form.addRow("Experiment name", self._name_edit)
        form.addRow("Destination", _wrap(path_row))

        layout = QVBoxLayout(self)
        layout.addWidget(box)

        # The whole section is unavailable until the hue sensor is enabled.
        self.setEnabled(False)

    def set_hue_enabled(self, enabled: bool) -> None:
        self.setEnabled(enabled)

    def reset(self) -> None:
        self._explicit_path = None
        self._path_label.setText("(default location)")

    def _on_choose_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save hue data log", self._default_name(), "Text files (*.txt)")
        if path:
            self._explicit_path = Path(path)
            self._path_label.setText(str(self._explicit_path))

    def _default_name(self) -> str:
        name = self._name_edit.text().strip()
        suffix = f"_{name}" if name else ""
        return f"{self._mode}hue_exp{suffix}_{datetime.now():%Y%m%d_%H%M%S}.txt"

    def hue_log_path(self) -> Path | None:
        if not self._save_checkbox.isChecked():
            return None
        return self._explicit_path or Path(self._default_name())

    def experiment_name(self) -> str:
        return self._name_edit.text().strip()
