#!/usr/bin/env python3
"""Offscreen verification for the configurableFirmware GUI (M7-M9).

Run (from project root, WSL/Linux):
    cd prototype2/GUI/configurableFirmware
    UV_PROJECT_ENVIRONMENT=.venv-linux uv run python test_offscreen.py

No hardware, no real serial port — FakeSerialLink replaces SerialLink.
"""

import os
import sys
import tempfile
import traceback
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, Signal
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication(sys.argv)

# Import after QApplication exists.
from config_io import load_config, save_config  # noqa: E402
from main_window import MainWindow  # noqa: E402
from param_form import ParamForm  # noqa: E402
from protocol import build_mode_command, build_set_command, parse_frame, parse_get_response  # noqa: E402


# ---------------------------------------------------------------------------
# Fake serial link — no real port opened
# ---------------------------------------------------------------------------

class FakeSerialLink(QObject):
    line_received = Signal(str)
    connection_lost = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.sent: list[str] = []

    def send(self, cmd: str) -> None:
        self.sent.append(cmd)

    def inject(self, line: str) -> None:
        self.line_received.emit(line)

    def start(self) -> None:
        pass

    def close(self) -> None:
        pass


def _frame(
    trial=1, red=0, yellow=0, green=0, blue=0, cyan=0,
    hue_r=-99, hue_g=-99, hue_b=-99, hue_ct=-99, hue_l=-99,
    leda="NONE", ledb="NONE", press=0, trigger=0,
) -> str:
    fields = (trial, red, yellow, green, blue, cyan, hue_r, hue_g, hue_b, hue_ct, hue_l, leda, ledb, press, trigger)
    return "FRAME@" + "@".join(str(f) for f in fields)


def _make_window() -> MainWindow:
    w = MainWindow()
    w._connect_page._timer.stop()
    return w


_LINEAR_DEFAULTS = {
    "freq": "10", "trialLength": "3000", "interTrialWait": "750", "steps": "10",
    "nBaselinesStart": "0", "nBaselinesEnd": "0",
    "LEDA": "NONE", "maxA": "3200", "minA": "0",
    "bgStim1Led": "NONE", "bgStim1Int": "0", "bgStim2Led": "NONE", "bgStim2Int": "0",
    "ref1Led": "NONE", "ref1Int": "0", "ref2Led": "NONE", "ref2Int": "0",
    "ref3Led": "NONE", "ref3Int": "0",
    "baselineLed1": "NONE", "baselineLed1Val": "0",
    "baselineLed2": "NONE", "baselineLed2Val": "0",
    "baselineLed3": "NONE", "baselineLed3Val": "0",
    "hue": "0",
}

_GRID_DEFAULTS = {
    **_LINEAR_DEFAULTS,
    "order": "1", "LEDB": "NONE", "maxB": "2000", "minB": "0",
}

_BEHAVIORAL_DEFAULTS = {
    "freq": "10", "interTrialWait": "750",
    "LEDA": "NONE", "maxA": "3200", "minA": "0",
    "LEDB": "NONE", "maxB": "2000", "minB": "0",
    "bgStim1Led": "NONE", "bgStim1Int": "0", "bgStim2Led": "NONE", "bgStim2Int": "0",
    "ref1Led": "NONE", "ref1Int": "0", "ref2Led": "NONE", "ref2Int": "0",
    "ref3Led": "NONE", "ref3Int": "0",
}

_DEFAULTS_BY_MODE = {"LINEAR": _LINEAR_DEFAULTS, "GRID": _GRID_DEFAULTS, "BEHAVIORAL": _BEHAVIORAL_DEFAULTS}


def _inject_get(fake: FakeSerialLink, mode: str, overrides: dict | None = None) -> None:
    base = dict(_DEFAULTS_BY_MODE[mode])
    base.update(overrides or {})
    for key, value in base.items():
        fake.inject(f"{key}={value}")
    fake.inject(f"mode={mode}")


def _navigate_to_config(mode: str, overrides: dict | None = None) -> tuple[MainWindow, FakeSerialLink]:
    """Connects, chooses `mode`, and answers the GET so the config page is shown."""
    w = _make_window()
    fake = _connect(w)
    w._mode_select_page.mode_chosen.emit(mode, False)
    _inject_get(fake, mode, overrides)
    return w, fake


def _connect(w: MainWindow) -> FakeSerialLink:
    fake = FakeSerialLink()
    w._on_connected(fake)
    return fake


# ---------------------------------------------------------------------------
# Protocol tests
# ---------------------------------------------------------------------------

def test_parse_frame_valid():
    line = _frame(trial=3, red=500, yellow=0, green=0, blue=0, cyan=0, leda="RED", ledb="NONE", press=1, trigger=1)
    frame = parse_frame(line)
    assert frame is not None, "Valid frame failed to parse"
    assert frame["TrialNumber"] == 3
    assert frame["Red"] == 500
    assert frame["LEDA"] == "RED"
    assert frame["LEDB"] == "NONE"
    assert frame["Press"] == 1
    assert frame["Trigger"] == 1
    print("  [OK] parse_frame parses a well-formed FRAME@ line")


def test_parse_frame_rejects_non_frame():
    assert parse_frame("OK MODE SOLID") is None
    assert parse_frame("ERR unknown param: LEDB RED") is None
    assert parse_frame("FRAME@1@2@3") is None  # wrong token count
    print("  [OK] parse_frame rejects non-frame and malformed lines")


def test_parse_get_response():
    lines = ["freq=10", "trialLength=3000", "LEDA=NONE", "mode=SOLID"]
    settings = parse_get_response(lines)
    assert settings is not None
    assert settings["freq"] == "10"
    assert settings["mode"] == "SOLID"
    assert parse_get_response(["freq=10"]) is None, "Incomplete GET (no mode=) should be None"
    print("  [OK] parse_get_response parses key=value lines and requires 'mode'")


def test_build_commands():
    assert build_mode_command("SOLID") == "MODE SOLID"
    cmd = build_set_command({"LEDA": "RED", "maxA": 3000})
    assert cmd == "SET LEDA RED, maxA 3000", f"Unexpected: {cmd}"
    print("  [OK] build_mode_command / build_set_command produce correct strings")


# ---------------------------------------------------------------------------
# Navigation tests (M8)
# ---------------------------------------------------------------------------

def test_connect_goes_to_mode_select():
    w = _make_window()
    _connect(w)
    assert w._stack.currentWidget() is w._mode_select_page
    print("  [OK] Connecting moves to ModeSelectPage")


def test_solid_auto_starts_without_hue():
    w = _make_window()
    fake = _connect(w)
    w._mode_select_page.mode_chosen.emit("SOLID", False)

    assert fake.sent == ["MODE SOLID", "START"], f"Unexpected sequence: {fake.sent}"
    assert w._stack.currentWidget() is w._solid_view
    assert w._solid_view._hue_enabled is False
    print("  [OK] Choosing Solid (no hue) sends MODE SOLID, START and shows SolidView")


def test_solid_auto_starts_with_hue():
    w = _make_window()
    fake = _connect(w)
    w._mode_select_page.mode_chosen.emit("SOLID", True)

    assert fake.sent == ["MODE SOLID", "SET hue 1", "START"], f"Unexpected sequence: {fake.sent}"
    assert w._solid_view._hue_enabled is True
    assert not w._solid_view._hue_plot.isHidden()
    print("  [OK] Choosing Solid with hue sends MODE SOLID, SET hue 1, START; hue panel shown")


def test_back_from_solid_sends_stop():
    w = _make_window()
    fake = _connect(w)
    w._mode_select_page.mode_chosen.emit("SOLID", False)
    fake.sent.clear()

    w._solid_view.back_requested.emit()

    assert fake.sent == ["STOP"], f"Unexpected: {fake.sent}"
    assert w._stack.currentWidget() is w._mode_select_page
    assert w._solid_view._link is None, "SolidView still attached after Back"
    print("  [OK] Back from Solid sends STOP, detaches, returns to ModeSelectPage")


def test_connection_lost_returns_to_connect():
    w = _make_window()
    fake = _connect(w)
    w._mode_select_page.mode_chosen.emit("SOLID", False)

    fake.connection_lost.emit("device unplugged")

    assert w._stack.currentWidget() is w._connect_page
    assert w._link is None
    assert w._solid_view._link is None, "SolidView still attached after connection loss"
    print("  [OK] Connection loss tears down the session and returns to Connect page")


# ---------------------------------------------------------------------------
# SolidView tests (M9)
# ---------------------------------------------------------------------------

def test_slider_emits_set_command():
    w = _make_window()
    fake = _connect(w)
    w._mode_select_page.mode_chosen.emit("SOLID", False)
    fake.sent.clear()

    w._solid_view._columns["RED"]._spin.setValue(2048)
    QTest.qWait(150)  # M9.2: SET is debounced ~100ms after the last change

    assert fake.sent == ["SET REDLED 2048"], f"Unexpected: {fake.sent}"
    print("  [OK] Moving a slider/spinbox sends the matching SET <COLOR>LED command")


def test_slider_debounce_collapses_rapid_changes():
    """M9.2: a fast drag (many valueChanged events) must send only one SET,
    for the final value, instead of flooding the serial link per tick."""
    w = _make_window()
    fake = _connect(w)
    w._mode_select_page.mode_chosen.emit("SOLID", False)
    fake.sent.clear()

    col = w._solid_view._columns["BLUE"]
    for value in (100, 500, 1200, 2400, 3000):
        col._spin.setValue(value)  # no wait between — simulates a continuous drag
    assert fake.sent == [], "SET sent before the debounce window elapsed"

    QTest.qWait(150)
    assert fake.sent == ["SET BLUELED 3000"], \
        f"Expected exactly one SET with the final value, got {fake.sent}"
    print("  [OK] Rapid slider changes collapse into a single debounced SET")


def test_slider_and_spinbox_stay_synced():
    w = _make_window()
    _connect(w)
    w._mode_select_page.mode_chosen.emit("SOLID", False)
    col = w._solid_view._columns["CYAN"]

    col._slider.setValue(1500)
    assert col._spin.value() == 1500, "Spinbox did not follow slider"

    col._spin.setValue(2500)
    assert col._slider.value() == 2500, "Slider did not follow spinbox"
    print("  [OK] Slider and spinbox stay synced in both directions")


def test_hue_panel_hidden_without_hue():
    w = _make_window()
    _connect(w)
    w._mode_select_page.mode_chosen.emit("SOLID", False)
    assert w._solid_view._hue_plot.isHidden(), "Hue panel shown when hue not enabled"
    print("  [OK] Hue panel hidden when hue not enabled")


def test_frame_updates_sliders_without_resend():
    w = _make_window()
    fake = _connect(w)
    w._mode_select_page.mode_chosen.emit("SOLID", False)
    fake.sent.clear()

    fake.inject(_frame(red=777, yellow=111))

    assert w._solid_view._columns["RED"].value() == 777
    assert w._solid_view._columns["YELLOW"].value() == 111
    assert fake.sent == [], f"Frame-driven slider update should not re-send SET: {fake.sent}"
    print("  [OK] Incoming FRAME updates sliders without re-sending SET (no feedback loop)")


def test_hue_bars_update_from_frame():
    w = _make_window()
    fake = _connect(w)
    w._mode_select_page.mode_chosen.emit("SOLID", True)

    fake.inject(_frame(hue_r=100, hue_g=200, hue_b=300))
    QTest.qWait(350)  # M9.2: bars are flushed on a throttled ~300ms cadence, not per-frame

    assert w._solid_view._hue_bars.opts["height"] == [100, 200, 300]
    print("  [OK] Hue bar plot updates from FRAME HUE_R/G/B fields")


def test_hue_plot_throttled_not_per_frame():
    """M9.2: redrawing the bar plot on every 100ms frame adds GUI-thread work that
    competes with serial processing; it should only flush on the slower timer."""
    w = _make_window()
    fake = _connect(w)
    w._mode_select_page.mode_chosen.emit("SOLID", True)

    fake.inject(_frame(hue_r=10, hue_g=20, hue_b=30))
    fake.inject(_frame(hue_r=40, hue_g=50, hue_b=60))
    assert w._solid_view._hue_bars.opts["height"] == [0, 0, 0], \
        "Bars redrawn immediately instead of waiting for the throttle timer"

    QTest.qWait(350)
    assert w._solid_view._hue_bars.opts["height"] == [40, 50, 60], \
        "Bars should reflect the latest cached reading once the timer fires"
    print("  [OK] Hue plot only redraws on the throttled timer, using the latest cached reading")


def test_hue_plot_range_fixed_not_auto():
    """M9.1: the hue plot must not auto-range (that's what caused bars to visibly
    keep settling/moving long after the underlying value stopped changing)."""
    w = _make_window()
    fake = _connect(w)
    w._mode_select_page.mode_chosen.emit("SOLID", True)

    vb = w._solid_view._hue_plot.getViewBox()
    assert vb.autoRangeEnabled() == [False, False], \
        f"Hue plot should have auto-range disabled on both axes, got {vb.autoRangeEnabled()}"
    assert vb.viewRange()[1] == [0.0, 1000.0], \
        f"Default hue Y-range should be [0, 1000], got {vb.viewRange()[1]}"

    fake.inject(_frame(hue_r=50000, hue_g=1, hue_b=1))
    assert vb.viewRange()[1] == [0.0, 1000.0], \
        "A large hue value must not change the (now fixed) view range"
    print("  [OK] Hue plot range is fixed, not auto-scaling, and unaffected by frame values")


def test_hue_scale_spinbox_changes_range():
    w = _make_window()
    _connect(w)
    w._mode_select_page.mode_chosen.emit("SOLID", True)

    w._solid_view._hue_scale_spin.setValue(2000)

    vb = w._solid_view._hue_plot.getViewBox()
    assert vb.viewRange()[1] == [0.0, 2000.0], f"Expected Y-range [0, 2000], got {vb.viewRange()[1]}"
    print("  [OK] Hue scale spinbox updates the plot's fixed Y-range")


def test_hue_controls_visible_only_with_hue():
    w = _make_window()
    _connect(w)
    w._mode_select_page.mode_chosen.emit("SOLID", False)
    assert w._solid_view._hue_controls.isHidden(), "Hue scale controls shown when hue not enabled"

    w2 = _make_window()
    _connect(w2)
    w2._mode_select_page.mode_chosen.emit("SOLID", True)
    assert not w2._solid_view._hue_controls.isHidden(), "Hue scale controls hidden when hue enabled"
    print("  [OK] Hue scale controls visibility matches the hue plot's")


def test_press_log_only_when_hue_enabled():
    w = _make_window()
    fake = _connect(w)
    w._mode_select_page.mode_chosen.emit("SOLID", False)
    fake.inject(_frame(press=1))
    assert w._solid_view._press_log == [], "Press logged even though hue is disabled"

    w2 = _make_window()
    fake2 = _connect(w2)
    w2._mode_select_page.mode_chosen.emit("SOLID", True)
    fake2.inject(_frame(press=1, red=1234))
    assert len(w2._solid_view._press_log) == 1
    assert w2._solid_view._press_log[0]["Red"] == 1234
    print("  [OK] Press rows only accumulate while hue is enabled")


# ---------------------------------------------------------------------------
# param_form / config_io tests (M10/M11 shared infra)
# ---------------------------------------------------------------------------

def test_param_form_round_trip():
    form = ParamForm(["freq", "LEDA", "hue"])
    form.set_values({"freq": "20", "LEDA": "RED", "hue": "1"})
    values = form.values()
    assert values == {"freq": 20, "LEDA": "RED", "hue": 1}, f"Unexpected: {values}"
    print("  [OK] ParamForm round-trips int/led/bool fields")


def test_param_form_changed_values():
    form = ParamForm(["freq", "maxA", "LEDA"])
    baseline = {"freq": "10", "maxA": "3200", "LEDA": "NONE"}
    form.set_values(baseline)
    form._widgets["maxA"].setValue(3000)
    changed = form.changed_values(baseline)
    assert changed == {"maxA": 3000}, f"Expected only maxA changed, got {changed}"
    print("  [OK] ParamForm.changed_values() returns only the fields that differ from baseline")


def test_config_json_round_trip():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "linearParamConfig_test.json"
        params = {"freq": 15, "LEDA": "CYAN", "hue": 1}
        save_config(path, params)
        loaded = load_config(path)
        assert loaded == params, f"Round-trip mismatch: {loaded}"
    print("  [OK] config_io save_config/load_config round-trips a params dict")


# ---------------------------------------------------------------------------
# Linear view tests (M10)
# ---------------------------------------------------------------------------

def test_linear_mode_select_sends_mode_and_get():
    w, fake = _navigate_to_config("LINEAR")
    assert fake.sent == ["MODE LINEAR", "GET"], f"Unexpected: {fake.sent}"
    assert w._stack.currentWidget() is w._linear_config_page
    print("  [OK] Choosing Linear sends MODE LINEAR + GET, shows the config page once GET completes")


def test_linear_config_prefilled_from_get():
    w, _fake = _navigate_to_config("LINEAR", {"freq": "25", "LEDA": "GREEN"})
    values = w._linear_config_page._form.values()
    assert values["freq"] == 25 and values["LEDA"] == "GREEN", f"Config not pre-filled: {values}"
    print("  [OK] Linear config form is pre-filled from the GET response")


def test_linear_start_sends_only_changed_params():
    w, fake = _navigate_to_config("LINEAR")
    fake.sent.clear()
    w._linear_config_page._form._widgets["LEDA"].setCurrentText("RED")
    w._linear_config_page._form._widgets["steps"].setValue(5)
    w._linear_config_page.start_requested.emit()

    assert len(fake.sent) == 2, f"Expected SET + START, got {fake.sent}"
    assert fake.sent[0] == "SET LEDA RED, steps 5" or fake.sent[0] == "SET steps 5, LEDA RED", \
        f"Unexpected SET batch: {fake.sent[0]}"
    assert fake.sent[1] == "START"
    assert w._stack.currentWidget() is w._linear_session_page
    assert w._linear_session_page._total_trials == 5  # 0 + 5 steps + 0 baselines
    print("  [OK] Linear Start sends only the changed params + START, shows the session page")


def test_linear_progress_robust_to_repeated_and_skipped_trials():
    """Progress must count each distinct TrialNumber once, whether it repeats
    across several 100ms frames or a trial's frames are never seen at all."""
    w, fake = _navigate_to_config("LINEAR", {"steps": "3"})
    w._linear_config_page.start_requested.emit()
    session = w._linear_session_page

    fake.inject(_frame(trial=1))
    fake.inject(_frame(trial=1))  # repeated — must not double-count
    assert session._progress.value() == 1

    fake.inject(_frame(trial=3))  # trial 2's frames never arrived — still counts what we saw
    assert session._progress.value() == 2
    assert session._rep_label.text() == "Trial 2 / 3"
    print("  [OK] Linear progress counts distinct trial numbers seen, robust to repeats/gaps")


def test_linear_hue_plots_and_mean_per_step():
    w, fake = _navigate_to_config("LINEAR", {"steps": "2", "hue": "1"})
    w._linear_config_page.start_requested.emit()
    session = w._linear_session_page
    assert not session._hue_widget.isHidden()

    fake.inject(_frame(trial=1, hue_r=100, hue_g=200, hue_b=300))
    fake.inject(_frame(trial=1, hue_r=200, hue_g=300, hue_b=400))
    assert session._cum["Red"] == [100, 200], "Cumulative plot should append every frame's reading"

    fake.inject(_frame(trial=2, hue_r=10, hue_g=10, hue_b=10))  # trial change flushes trial 1's mean
    assert session._mean_x == [1]
    assert session._mean["Red"] == [150.0], f"Expected mean of [100,200]=150, got {session._mean['Red']}"
    print("  [OK] Linear hue plots: cumulative appends every frame, mean-per-step flushes on trial change")


def test_linear_hue_log_file_written():
    w, fake = _navigate_to_config("LINEAR", {"steps": "2", "hue": "1"})
    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "linearhue_exp_test.txt"
        w._linear_config_page._hue_log_path = log_path
        w._linear_config_page.start_requested.emit()

        fake.inject(_frame(trial=1, hue_r=100, hue_g=200, hue_b=300))
        w._linear_session_page.detach()  # closes the file

        lines = log_path.read_text().splitlines()
        assert lines[0].split()[0] == "TrialNumber"
        assert lines[1].split()[0] == "1"
    print("  [OK] Linear hue log file is written with a header and one row per frame")


def test_linear_back_sends_stop():
    w, fake = _navigate_to_config("LINEAR")
    w._linear_config_page.start_requested.emit()
    fake.sent.clear()

    w._linear_session_page.back_requested.emit()

    assert fake.sent == ["STOP"], f"Unexpected: {fake.sent}"
    assert w._stack.currentWidget() is w._mode_select_page
    print("  [OK] Back from Linear session sends STOP and returns to ModeSelectPage")


# ---------------------------------------------------------------------------
# Grid view tests (M11)
# ---------------------------------------------------------------------------

def test_grid_mode_select_sends_mode_and_get():
    w, fake = _navigate_to_config("GRID")
    assert fake.sent == ["MODE GRID", "GET"], f"Unexpected: {fake.sent}"
    assert w._stack.currentWidget() is w._grid_config_page
    print("  [OK] Choosing Grid sends MODE GRID + GET, shows the config page once GET completes")


def test_grid_start_total_trials_and_axes():
    w, fake = _navigate_to_config("GRID", {"steps": "2", "minA": "500", "maxA": "3000", "minB": "1000", "maxB": "2000"})
    w._grid_config_page._form._widgets["LEDA"].setCurrentText("RED")
    w._grid_config_page._form._widgets["LEDB"].setCurrentText("GREEN")
    w._grid_config_page.start_requested.emit()

    session = w._grid_session_page
    assert session._total_trials == 4  # 2x2 grid, no baselines
    assert session._a_levels == [500, 3000]
    assert session._b_levels == [1000, 2000]
    print("  [OK] Grid Start computes total trials and axis levels from steps/min/max")


def test_grid_visited_cells_stay_marked_through_iti():
    """ITI frames (Trigger=0, LEDs zeroed) must not move the marker to (0,0);
    presented cells stay marked as new trials arrive."""
    w, fake = _navigate_to_config("GRID", {"steps": "2", "minA": "500", "maxA": "3000", "minB": "1000", "maxB": "2000"})
    w._grid_config_page._form._widgets["LEDA"].setCurrentText("RED")
    w._grid_config_page._form._widgets["LEDB"].setCurrentText("GREEN")
    w._grid_config_page.start_requested.emit()
    session = w._grid_session_page

    fake.inject(_frame(trial=1, red=500, green=1000, leda="RED", ledb="GREEN", trigger=1))
    assert session._current == (0, 0)
    assert (0, 0) in session._visited

    fake.inject(_frame(trial=1, red=0, green=0, leda="RED", ledb="GREEN", trigger=0))  # ITI
    assert session._current == (0, 0), "Marker jumped to origin during ITI"
    assert (0, 0) in session._visited

    fake.inject(_frame(trial=2, red=3000, green=2000, leda="RED", ledb="GREEN", trigger=1))
    assert session._current == (1, 1)
    assert (0, 0) in session._visited and (1, 1) in session._visited
    print("  [OK] Grid visited cells stay marked; ITI frames don't move the marker")


def test_grid_baseline_trials_excluded_from_grid_position():
    w, fake = _navigate_to_config(
        "GRID", {"steps": "2", "minA": "500", "maxA": "3000", "minB": "1000", "maxB": "2000", "nBaselinesStart": "1"}
    )
    w._grid_config_page._form._widgets["LEDA"].setCurrentText("RED")
    w._grid_config_page._form._widgets["LEDB"].setCurrentText("GREEN")
    w._grid_config_page.start_requested.emit()
    session = w._grid_session_page

    fake.inject(_frame(trial=1001, red=0, green=0, leda="RED", ledb="GREEN", trigger=1))
    assert session._current is None, "Baseline trial should not be plotted as a grid cell"
    assert session._progress.value() == 1  # still counts toward progress
    print("  [OK] Baseline trials count toward progress but are excluded from the grid plot")


def test_grid_back_sends_stop():
    w, fake = _navigate_to_config("GRID")
    w._grid_config_page.start_requested.emit()
    fake.sent.clear()

    w._grid_session_page.back_requested.emit()

    assert fake.sent == ["STOP"], f"Unexpected: {fake.sent}"
    assert w._stack.currentWidget() is w._mode_select_page
    print("  [OK] Back from Grid session sends STOP and returns to ModeSelectPage")


# ---------------------------------------------------------------------------
# M11.1 fixes: opt-in hue-data saving + LED-phase-assignment summary
# ---------------------------------------------------------------------------

def test_format_led_assignments():
    from param_form import format_led_assignments

    settings = {**_LINEAR_DEFAULTS, "bgStim1Led": "GREEN", "bgStim1Int": "1000", "ref1Led": "YELLOW", "ref1Int": "2000"}
    text = format_led_assignments(settings)
    assert "bgStim1: GREEN=1000" in text
    assert "ref1: YELLOW=2000" in text
    assert format_led_assignments(_LINEAR_DEFAULTS) == "no background/reference/baseline LEDs set"
    print("  [OK] format_led_assignments lists every non-NONE phase LED with its value")


def test_linear_summary_includes_led_phase_assignments():
    w, fake = _navigate_to_config("LINEAR", {"ref1Led": "YELLOW", "ref1Int": "2000"})
    w._linear_config_page.start_requested.emit()
    assert "ref1: YELLOW=2000" in w._linear_session_page._params_label.text()
    print("  [OK] Linear session summary lists non-LEDA LED phase assignments")


def test_grid_summary_includes_led_phase_assignments():
    w, fake = _navigate_to_config("GRID", {"baselineLed1": "CYAN", "baselineLed1Val": "500"})
    w._grid_config_page.start_requested.emit()
    assert "baseline1: CYAN=500" in w._grid_session_page._params_label.text()
    print("  [OK] Grid session summary lists non-LEDA/LEDB LED phase assignments")


def test_linear_hue_save_checkbox_disabled_without_hue():
    w, fake = _navigate_to_config("LINEAR")
    assert not w._linear_config_page._save_hue_checkbox.isEnabled()
    w._linear_config_page._form._widgets["hue"].setChecked(True)
    assert w._linear_config_page._save_hue_checkbox.isEnabled()
    print("  [OK] Linear 'Save hue data to file' checkbox only enabled when hue is on")


def test_linear_hue_on_without_save_checkbox_does_not_log():
    """M11.1: hue can be enabled just to watch the live plots, without forcing a file save."""
    w, fake = _navigate_to_config("LINEAR", {"hue": "1"})
    assert not w._linear_config_page._save_hue_checkbox.isChecked()  # opt-in, defaults off
    w._linear_config_page.start_requested.emit()
    assert w._linear_config_page.hue_log_path() is None
    assert w._linear_session_page._log_file is None
    print("  [OK] Hue enabled without checking 'Save to file' does not open a log file")


def test_grid_hue_save_checkbox_disabled_without_hue():
    w, fake = _navigate_to_config("GRID")
    assert not w._grid_config_page._save_hue_checkbox.isEnabled()
    w._grid_config_page._form._widgets["hue"].setChecked(True)
    assert w._grid_config_page._save_hue_checkbox.isEnabled()
    print("  [OK] Grid 'Save hue data to file' checkbox only enabled when hue is on")


# ---------------------------------------------------------------------------
# Behavioral view tests (M12)
# ---------------------------------------------------------------------------

def test_behavioral_mode_select_sends_mode_and_get():
    w, fake = _navigate_to_config("BEHAVIORAL")
    assert fake.sent == ["MODE BEHAVIORAL", "GET"], f"Unexpected: {fake.sent}"
    assert w._stack.currentWidget() is w._behavioral_config_page
    print("  [OK] Choosing Behavioral sends MODE BEHAVIORAL + GET, shows the config page")


def test_behavioral_start_sends_only_changed_params():
    w, fake = _navigate_to_config("BEHAVIORAL")
    fake.sent.clear()
    w._behavioral_config_page._form._widgets["LEDA"].setCurrentText("RED")
    w._behavioral_config_page._form._widgets["LEDB"].setCurrentText("GREEN")
    w._behavioral_config_page.start_requested.emit()

    assert fake.sent[0] in ("SET LEDA RED, LEDB GREEN", "SET LEDB GREEN, LEDA RED"), f"Unexpected: {fake.sent[0]}"
    assert fake.sent[1] == "START"
    assert w._stack.currentWidget() is w._behavioral_session_page
    print("  [OK] Behavioral Start sends only the changed params + START, shows the session page")


def test_behavioral_live_marker_and_press_table():
    w, fake = _navigate_to_config("BEHAVIORAL")
    w._behavioral_config_page._form._widgets["LEDA"].setCurrentText("RED")
    w._behavioral_config_page._form._widgets["LEDB"].setCurrentText("GREEN")
    w._behavioral_config_page.start_requested.emit()
    session = w._behavioral_session_page

    fake.inject(_frame(red=1500, green=1000, leda="RED", ledb="GREEN"))
    x, y = session._current_marker.getData()
    assert list(x) == [1500] and list(y) == [1000], f"Live marker wrong: {x}, {y}"
    assert session._table.rowCount() == 0, "Press table should be empty before any press"

    fake.inject(_frame(red=1600, green=1100, leda="RED", ledb="GREEN", press=1))
    assert session._table.rowCount() == 1
    assert session._median_label.text() == "Median  RED: 1600  GREEN: 1100"
    print("  [OK] Behavioral live marker tracks frames; press appends a table row and updates the median")


def test_behavioral_press_button_sends_press():
    w, fake = _navigate_to_config("BEHAVIORAL")
    w._behavioral_config_page.start_requested.emit()
    fake.sent.clear()

    w._behavioral_session_page._press()

    assert fake.sent == ["PRESS"], f"Unexpected: {fake.sent}"
    print("  [OK] Behavioral Press button sends the PRESS command directly")


def test_behavioral_back_sends_stop():
    w, fake = _navigate_to_config("BEHAVIORAL")
    w._behavioral_config_page.start_requested.emit()
    fake.sent.clear()

    w._behavioral_session_page.back_requested.emit()

    assert fake.sent == ["STOP"], f"Unexpected: {fake.sent}"
    assert w._stack.currentWidget() is w._mode_select_page
    print("  [OK] Back from Behavioral session sends STOP and returns to ModeSelectPage")


def test_behavioral_config_save_load_round_trip():
    """M12.1: Behavioral config supports save/load like Linear/Grid, using
    beh_configparams_ naming."""
    w, fake = _navigate_to_config("BEHAVIORAL")
    w._behavioral_config_page._form._widgets["LEDA"].setCurrentText("RED")
    w._behavioral_config_page._form._widgets["freq"].setValue(25)

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "beh_configparams_test.json"
        save_config(path, w._behavioral_config_page._form.values())

        w2, _fake2 = _navigate_to_config("BEHAVIORAL")
        w2._behavioral_config_page._form.set_values({k: str(v) for k, v in load_config(path).items()})
        values = w2._behavioral_config_page._form.values()
        assert values["LEDA"] == "RED" and values["freq"] == 25, f"Round-trip mismatch: {values}"
    print("  [OK] Behavioral config save/load round-trips form values")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

TESTS = [
    test_parse_frame_valid,
    test_parse_frame_rejects_non_frame,
    test_parse_get_response,
    test_build_commands,
    test_connect_goes_to_mode_select,
    test_solid_auto_starts_without_hue,
    test_solid_auto_starts_with_hue,
    test_back_from_solid_sends_stop,
    test_connection_lost_returns_to_connect,
    test_slider_emits_set_command,
    test_slider_debounce_collapses_rapid_changes,
    test_slider_and_spinbox_stay_synced,
    test_hue_panel_hidden_without_hue,
    test_frame_updates_sliders_without_resend,
    test_hue_bars_update_from_frame,
    test_hue_plot_throttled_not_per_frame,
    test_hue_plot_range_fixed_not_auto,
    test_hue_scale_spinbox_changes_range,
    test_hue_controls_visible_only_with_hue,
    test_press_log_only_when_hue_enabled,
    test_param_form_round_trip,
    test_param_form_changed_values,
    test_config_json_round_trip,
    test_linear_mode_select_sends_mode_and_get,
    test_linear_config_prefilled_from_get,
    test_linear_start_sends_only_changed_params,
    test_linear_progress_robust_to_repeated_and_skipped_trials,
    test_linear_hue_plots_and_mean_per_step,
    test_linear_hue_log_file_written,
    test_linear_back_sends_stop,
    test_grid_mode_select_sends_mode_and_get,
    test_grid_start_total_trials_and_axes,
    test_grid_visited_cells_stay_marked_through_iti,
    test_grid_baseline_trials_excluded_from_grid_position,
    test_grid_back_sends_stop,
    test_format_led_assignments,
    test_linear_summary_includes_led_phase_assignments,
    test_grid_summary_includes_led_phase_assignments,
    test_linear_hue_save_checkbox_disabled_without_hue,
    test_linear_hue_on_without_save_checkbox_does_not_log,
    test_grid_hue_save_checkbox_disabled_without_hue,
    test_behavioral_mode_select_sends_mode_and_get,
    test_behavioral_start_sends_only_changed_params,
    test_behavioral_live_marker_and_press_table,
    test_behavioral_press_button_sends_press,
    test_behavioral_back_sends_stop,
    test_behavioral_config_save_load_round_trip,
]


def main() -> int:
    passed = failed = 0
    print(f"Running {len(TESTS)} offscreen tests...\n")
    for test_fn in TESTS:
        try:
            test_fn()
            passed += 1
        except Exception as exc:
            print(f"  [FAIL] {test_fn.__name__}: {exc}")
            traceback.print_exc()
            failed += 1
    print(f"\n{'=' * 40}")
    print(f"  {passed} passed  |  {failed} failed")
    print(f"{'=' * 40}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
