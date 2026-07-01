#!/usr/bin/env python3
"""Offscreen verification for the configurableFirmware GUI (M7-M9).

Run (from project root, WSL/Linux):
    cd prototype2/GUI/configurableFirmware
    UV_PROJECT_ENVIRONMENT=.venv-linux uv run python test_offscreen.py

No hardware, no real serial port — FakeSerialLink replaces SerialLink.
"""

import os
import sys
import traceback

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication(sys.argv)

# Import after QApplication exists.
from main_window import MainWindow  # noqa: E402
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


def test_placeholder_for_unbuilt_modes():
    for mode in ("LINEAR", "GRID", "BEHAVIORAL"):
        w = _make_window()
        fake = _connect(w)
        w._mode_select_page.mode_chosen.emit(mode, False)

        assert fake.sent == [f"MODE {mode}"], f"{mode}: unexpected sent commands {fake.sent}"
        assert w._stack.currentWidget() is w._placeholder_page, f"{mode}: not on placeholder page"
        assert "isn't implemented yet" in w._placeholder_page._label.text()
    print("  [OK] Linear/Grid/Behavioral route to the placeholder page, no START sent")


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


def test_back_from_placeholder_sends_stop():
    w = _make_window()
    fake = _connect(w)
    w._mode_select_page.mode_chosen.emit("GRID", False)
    fake.sent.clear()

    w._placeholder_page.back_requested.emit()

    assert fake.sent == ["STOP"], f"Unexpected: {fake.sent}"
    assert w._stack.currentWidget() is w._mode_select_page
    print("  [OK] Back from placeholder sends STOP and returns to ModeSelectPage")


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

    assert fake.sent == ["SET REDLED 2048"], f"Unexpected: {fake.sent}"
    print("  [OK] Moving a slider/spinbox sends the matching SET <COLOR>LED command")


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

    assert w._solid_view._hue_bars.opts["height"] == [100, 200, 300]
    print("  [OK] Hue bar plot updates from FRAME HUE_R/G/B fields")


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
    test_placeholder_for_unbuilt_modes,
    test_back_from_solid_sends_stop,
    test_back_from_placeholder_sends_stop,
    test_connection_lost_returns_to_connect,
    test_slider_emits_set_command,
    test_slider_and_spinbox_stay_synced,
    test_hue_panel_hidden_without_hue,
    test_frame_updates_sliders_without_resend,
    test_hue_bars_update_from_frame,
    test_hue_plot_range_fixed_not_auto,
    test_hue_scale_spinbox_changes_range,
    test_hue_controls_visible_only_with_hue,
    test_press_log_only_when_hue_enabled,
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
