"""Shared parameter form for Linear/Grid config screens.

Each mode's config screen exposes a subset of the shared SET params via a
QFormLayout, built from PARAM_SPEC: a QSpinBox for numeric params, a
QComboBox (LED name or NONE) for LED-assignment params, and a QCheckBox for
the hue toggle. Values round-trip as native Python types for both the
firmware SET/GET protocol (which uses strings) and JSON config files.
"""

from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QSpinBox, QWidget

LED_NAMES = ("NONE", "RED", "YELLOW", "GREEN", "BLUE", "CYAN")

# Maps an assigned LED name to the FRAME@ column that carries its live intensity.
LED_FRAME_KEY = {"RED": "Red", "YELLOW": "Yellow", "GREEN": "Green", "BLUE": "Blue", "CYAN": "Cyan"}

# (led_key, value_key, phase_label) for every LED-role param outside LEDA/LEDB,
# used by format_led_assignments() to summarize what's attached to each phase.
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

# key -> (kind, range) where kind is "int" | "led" | "bool"; range is (lo, hi) for "int", else None.
PARAM_SPEC: dict[str, tuple[str, tuple[int, int] | None]] = {
    "freq":            ("int", (1, 500)),
    "trialLength":     ("int", (200, 30000)),
    "interTrialWait":  ("int", (50, 30000)),
    "steps":           ("int", (2, 50)),
    "order":           ("int", (0, 4)),
    "nBaselinesStart": ("int", (0, 50)),
    "nBaselinesEnd":   ("int", (0, 50)),
    "maxA":            ("int", (0, 4095)),
    "minA":            ("int", (0, 4095)),
    "maxB":            ("int", (0, 4095)),
    "minB":            ("int", (0, 4095)),
    "LEDA":            ("led", None),
    "LEDB":            ("led", None),
    "bgStim1Led":      ("led", None),
    "bgStim1Int":      ("int", (0, 4095)),
    "bgStim2Led":      ("led", None),
    "bgStim2Int":      ("int", (0, 4095)),
    "ref1Led":         ("led", None),
    "ref1Int":         ("int", (0, 4095)),
    "ref2Led":         ("led", None),
    "ref2Int":         ("int", (0, 4095)),
    "ref3Led":         ("led", None),
    "ref3Int":         ("int", (0, 4095)),
    "baselineLed1":    ("led", None),
    "baselineLed1Val": ("int", (0, 4095)),
    "baselineLed2":    ("led", None),
    "baselineLed2Val": ("int", (0, 4095)),
    "baselineLed3":    ("led", None),
    "baselineLed3Val": ("int", (0, 4095)),
    "hue":             ("bool", None),
}


class ParamForm(QWidget):
    """A QFormLayout of param widgets for a given ordered list of param keys."""

    def __init__(self, keys: list[str], parent=None) -> None:
        super().__init__(parent)
        self._keys = keys
        self._widgets: dict[str, QSpinBox | QComboBox | QCheckBox] = {}
        self._form = QFormLayout(self)
        for key in keys:
            kind, span = PARAM_SPEC[key]
            if kind == "int":
                widget = QSpinBox()
                lo, hi = span
                widget.setRange(lo, hi)
            elif kind == "led":
                widget = QComboBox()
                widget.addItems(LED_NAMES)
            else:
                widget = QCheckBox()
            self._form.addRow(key, widget)
            self._widgets[key] = widget

    def set_values(self, values: dict[str, str]) -> None:
        """Populates widgets from a GET-response-style dict (string values)."""
        for key, widget in self._widgets.items():
            raw = values.get(key)
            if raw is None:
                continue
            if isinstance(widget, QSpinBox):
                widget.setValue(int(raw))
            elif isinstance(widget, QComboBox):
                idx = widget.findText(str(raw))
                if idx >= 0:
                    widget.setCurrentIndex(idx)
            else:
                widget.setChecked(str(raw) in ("1", "True", "true"))

    def values(self) -> dict[str, int | str]:
        """Returns the current value of every field, natively typed."""
        result: dict[str, int | str] = {}
        for key, widget in self._widgets.items():
            if isinstance(widget, QSpinBox):
                result[key] = widget.value()
            elif isinstance(widget, QComboBox):
                result[key] = widget.currentText()
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
