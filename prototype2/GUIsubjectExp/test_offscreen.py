#!/usr/bin/env python3
"""M2.5 offscreen verification for the subjectExperiment GUI.

Run (from project root, WSL/Linux):
    cd prototype2/GUIsubjectExp
    UV_PROJECT_ENVIRONMENT=.venv-linux uv run python test_offscreen.py

Each test function receives a fresh tmp_path (tempfile.TemporaryDirectory).
No hardware, no real serial port — FakeSerialLink replaces SerialLink.
"""

import csv
import os
import sys
import tempfile
import traceback
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication(sys.argv)

# Import after QApplication exists.
from main_window import MainWindow, _color_pair, _exp_type  # noqa: E402


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

    def inject_get(self, mode: str) -> None:
        for line in (
            "freq=10", "refAmber=2400", "refCyan=0",
            "maxA=3200", "minA=0", "maxB=2000", "minB=0",
            "nBaselinesStart=2", "nBaselinesEnd=2",
            "trialLength=3000", "interTrialWait=750", "order=1",
            f"mode={mode}",
            "# use defaults-rg / defaults-bg to restore color-pair defaults",
        ):
            self.inject(line)

    def start(self) -> None:
        pass

    def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Frame templates
# ---------------------------------------------------------------------------

def _rg_frame(stim: int, red: int, green: int, trig: int) -> str:
    return f"&@STIM:{stim},Mode:RG,RED:{red},GREEN:{green},BLUE:0,AMBER:0,CYAN:0,TRIG:{trig}%!"


def _bg_frame(stim: int, blue: int, green: int, trig: int) -> str:
    return f"&@STIM:{stim},Mode:BG,RED:0,GREEN:{green},BLUE:{blue},AMBER:0,CYAN:0,TRIG:{trig}%!"


# ---------------------------------------------------------------------------
# Navigation helpers
# ---------------------------------------------------------------------------

def _make_window() -> MainWindow:
    w = MainWindow()
    w._connect_page._timer.stop()
    return w


def _navigate_to_mode_config(
    w: MainWindow,
    mode_str: str,
    sub_id: str = "S01",
    group: str = "HC",
    folder: Path | None = None,
) -> FakeSerialLink:
    """Drive MainWindow from ConnectPage all the way to ModeConfigPage."""
    fake = FakeSerialLink()
    w._on_connected(fake)
    w._on_participant_confirmed(sub_id, group, str(folder or Path(tempfile.mkdtemp())))
    w._on_mode_selected(mode_str)
    fake.inject_get(mode_str)
    return fake


def _confirm_default(w: MainWindow) -> None:
    page = w._mode_config_page
    page._default_radio.setChecked(True)
    page._confirm()


def _confirm_advanced(w: MainWindow, overrides: dict[str, int]) -> None:
    page = w._mode_config_page
    page._advanced_radio.setChecked(True)
    for key, val in overrides.items():
        page._fields[key].setValue(val)
    page._confirm()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_all_modes_default(tmp: Path) -> None:
    """All 4 modes navigate to the correct session page via Default config."""
    for mode_str in ("beh-rg", "beh-bg", "grid-rg", "grid-bg"):
        w = _make_window()
        fake = _navigate_to_mode_config(w, mode_str, folder=tmp)
        _confirm_default(w)

        if _exp_type(mode_str) == "behavioral":
            assert w._stack.currentWidget() is w._behavioral_session_page, \
                f"{mode_str}: expected behavioral session page"
        else:
            assert w._stack.currentWidget() is w._grid_session_page, \
                f"{mode_str}: expected grid session page"

        batch_cmds = [c for c in fake.sent if ";" in c and "=" in c]
        assert not batch_cmds, f"{mode_str}: unexpected batch command in Default mode: {batch_cmds}"

    print("  [OK] All 4 modes reach correct session page via Default")


def test_advanced_sends_batch(tmp: Path) -> None:
    """Advanced config sends exactly one batch command with only changed params."""
    w = _make_window()
    fake = _navigate_to_mode_config(w, "beh-rg", folder=tmp)
    _confirm_advanced(w, {"freq": 20, "maxA": 3000})

    batch_cmds = [c for c in fake.sent if ";" in c and "=" in c]
    assert len(batch_cmds) == 1, f"Expected 1 batch command, got {batch_cmds}"
    parts = dict(tok.split("=") for tok in batch_cmds[0].split(";"))
    assert parts.get("freq") == "20", f"freq missing/wrong in batch: {parts}"
    assert parts.get("maxA") == "3000", f"maxA missing/wrong in batch: {parts}"
    # Unchanged params must not appear
    assert "minA" not in parts, f"unchanged param minA in batch: {parts}"

    print("  [OK] Advanced sends correct batch command (changed params only)")


def test_behavioral_csvs_and_file(tmp: Path) -> None:
    """Start creates session file + writes behavioral and master CSV rows."""
    w = _make_window()
    _navigate_to_mode_config(w, "beh-rg", sub_id="P01", group="HC", folder=tmp)
    _confirm_default(w)
    w._behavioral_session_page._start()

    # Master CSV
    master = tmp / "participants_master.csv"
    assert master.exists(), "participants_master.csv not created"
    rows = list(csv.DictReader(master.open()))
    assert rows[-1]["sub_id"] == "P01"
    assert rows[-1]["experiment"] == "behavioral"
    assert rows[-1]["session"] == "1"

    # Behavioral CSV
    beh_csv = tmp / "participants_behavioral.csv"
    assert beh_csv.exists(), "participants_behavioral.csv not created"
    rows = list(csv.DictReader(beh_csv.open()))
    assert rows[-1]["sub_id"] == "P01"
    assert rows[-1]["mode"] == "beh-rg"
    fname = rows[-1].get("file", "")
    assert fname.startswith("P01_R"), f"file field wrong: {fname}"

    # Session data file
    sess = tmp / "P01_R1.txt"
    assert sess.exists(), "P01_R1.txt not created"
    header = sess.read_text().splitlines()[0]
    assert header == "Trial Primary Green", f"Wrong header: {header!r}"

    print("  [OK] Behavioral CSVs and session file created correctly on Start")


def test_press_accumulation(tmp: Path) -> None:
    """RESP events accumulate in table, session file, and median marker."""
    w = _make_window()
    fake = _navigate_to_mode_config(w, "beh-rg", sub_id="P02", group="HC", folder=tmp)
    _confirm_default(w)
    page = w._behavioral_session_page
    page._start()

    presses = [(1, 1600, 1000), (2, 1800, 900), (3, 1400, 1100)]
    for trial, a, b in presses:
        fake.inject(f"RESP,Trial:{trial},A:{a},B:{b}")

    assert page._table.rowCount() == 3, \
        f"Expected 3 table rows, got {page._table.rowCount()}"

    sess = tmp / "P02_R1.txt"
    lines = sess.read_text().splitlines()
    assert len(lines) == 4, f"Expected header + 3 data lines, got {lines}"
    assert lines[1] == "1 1600 1000"
    assert lines[2] == "2 1800 900"
    assert lines[3] == "3 1400 1100"

    x, _ = page._median_marker.getData()
    assert x is not None and len(x) == 1, "Median marker not updated"

    print("  [OK] Press accumulation: table, file, median marker all correct")


def test_live_position_rg(tmp: Path) -> None:
    """Stream frames (RG) update the live position marker using RED field."""
    w = _make_window()
    fake = _navigate_to_mode_config(w, "beh-rg", sub_id="P03", folder=tmp)
    _confirm_default(w)
    page = w._behavioral_session_page
    page._start()

    fake.inject(_rg_frame(1, red=1600, green=1000, trig=1))
    x, y = page._current_marker.getData()
    assert x is not None and len(x) == 1 and x[0] == 1600, f"X wrong: {x}"
    assert y is not None and len(y) == 1 and y[0] == 1000, f"Y wrong: {y}"

    print("  [OK] Live position marker updated from RG stream frame (RED field)")


def test_live_position_bg(tmp: Path) -> None:
    """Stream frames (BG) update the live position marker using BLUE field."""
    w = _make_window()
    fake = _navigate_to_mode_config(w, "beh-bg", sub_id="P04", folder=tmp)
    _confirm_default(w)
    page = w._behavioral_session_page
    page._start()

    fake.inject(_bg_frame(1, blue=1400, green=1000, trig=1))
    x, y = page._current_marker.getData()
    assert x is not None and len(x) == 1 and x[0] == 1400, \
        f"Expected BLUE=1400 on X axis, got {x}"

    print("  [OK] Live position marker updated from BG stream frame (BLUE field)")


def test_grid_csvs(tmp: Path) -> None:
    """Grid Start writes participants_grid.csv and master CSV."""
    w = _make_window()
    _navigate_to_mode_config(w, "grid-rg", sub_id="G01", group="PD", folder=tmp)
    _confirm_default(w)
    w._grid_session_page._start()

    master_rows = list(csv.DictReader((tmp / "participants_master.csv").open()))
    assert master_rows[-1]["sub_id"] == "G01"
    assert master_rows[-1]["experiment"] == "grid"
    assert master_rows[-1]["session"] == "1"

    grid_csv = tmp / "participants_grid.csv"
    assert grid_csv.exists(), "participants_grid.csv not created"
    rows = list(csv.DictReader(grid_csv.open()))
    r = rows[-1]
    assert r["sub_id"] == "G01"
    assert r["mode"] == "grid-rg"
    assert "nBaselinesStart" in r and "nBaselinesEnd" in r and "order" in r
    assert "file" not in r or r.get("file") == "", \
        "Grid CSV should not have a file column"

    print("  [OK] Grid CSVs written correctly on Start")


def test_grid_done(tmp: Path) -> None:
    """DONE line fills progress bar, ends session, re-enables Back button."""
    w = _make_window()
    fake = _navigate_to_mode_config(w, "grid-rg", sub_id="G02", folder=tmp)
    _confirm_default(w)
    page = w._grid_session_page
    page._start()

    # One trigger cycle then DONE
    fake.inject(_rg_frame(1, red=1600, green=1000, trig=1))
    fake.inject(_rg_frame(1, red=1600, green=1000, trig=0))
    fake.inject("DONE")

    assert page._progress.value() == page._total_trials, \
        f"Progress {page._progress.value()} != total {page._total_trials}"
    assert not page._running, "Session still running after DONE"
    assert page._back_btn.isEnabled(), "Back button still disabled after DONE"
    assert page._status_label.text() == "Done"

    print("  [OK] Grid DONE: progress fills, session ends, Back re-enables")


def test_grid_progress_increments_on_trig_edge(tmp: Path) -> None:
    """Progress bar increments on TRIG 1→0 falling edge, not on rise."""
    w = _make_window()
    fake = _navigate_to_mode_config(w, "grid-rg", sub_id="G03", folder=tmp)
    _confirm_default(w)
    page = w._grid_session_page
    page._start()

    assert page._progress.value() == 0

    fake.inject(_rg_frame(1, red=1600, green=1000, trig=1))
    assert page._progress.value() == 0, "Progress incremented on rising edge (wrong)"

    fake.inject(_rg_frame(1, red=1600, green=1000, trig=0))
    assert page._progress.value() == 1, \
        f"Progress should be 1 after falling edge, got {page._progress.value()}"

    print("  [OK] Grid progress increments on TRIG falling edge")


def test_back_reentry(tmp: Path) -> None:
    """Back from session returns to ExperimentSelect; re-entry re-queries GET."""
    w = _make_window()
    fake = _navigate_to_mode_config(w, "beh-rg", sub_id="P05", folder=tmp)
    _confirm_default(w)

    w._on_back_requested()
    assert w._stack.currentWidget() is w._experiment_select_page, \
        "Not back on ExperimentSelect after back_requested"

    sent_before = len(fake.sent)
    w._on_mode_selected("grid-bg")
    fake.inject_get("grid-bg")

    get_cmds = [c for c in fake.sent[sent_before:] if c == "get"]
    assert get_cmds, "GET not re-sent after Back re-entry"
    assert w._stack.currentWidget() is w._mode_config_page, \
        "Not on ModeConfigPage after re-entry with new mode"
    assert w._mode_config_page._mode_str == "grid-bg"

    print("  [OK] Back re-entry: GET re-sent, ModeConfigPage updated to new mode")


def test_session_number_increments(tmp: Path) -> None:
    """Repeated sessions for same subject get sequential session numbers."""
    for expected_n in (1, 2):
        w = _make_window()
        _navigate_to_mode_config(w, "beh-rg", sub_id="P06", folder=tmp)
        _confirm_default(w)
        w._behavioral_session_page._start()

    rows = list(csv.DictReader((tmp / "participants_master.csv").open()))
    sessions = [int(r["session"]) for r in rows if r["sub_id"] == "P06"]
    assert sessions == [1, 2], f"Session numbers wrong: {sessions}"

    print("  [OK] Session numbers increment correctly across repeated sessions")


def test_session_numbers_independent_per_exp_type(tmp: Path) -> None:
    """Behavioral and grid session numbers are independent per subject."""
    w = _make_window()
    _navigate_to_mode_config(w, "beh-rg", sub_id="Q01", folder=tmp)
    _confirm_default(w)
    w._behavioral_session_page._start()

    w2 = _make_window()
    _navigate_to_mode_config(w2, "grid-rg", sub_id="Q01", folder=tmp)
    _confirm_default(w2)
    w2._grid_session_page._start()

    beh_rows = list(csv.DictReader((tmp / "participants_behavioral.csv").open()))
    grid_rows = list(csv.DictReader((tmp / "participants_grid.csv").open()))
    assert beh_rows[-1]["session"] == "1"
    assert grid_rows[-1]["session"] == "1", \
        "Grid session should start at 1 independently of behavioral"

    print("  [OK] Session numbers independent per experiment type")


def test_color_theming(tmp: Path) -> None:
    """Stylesheet updates with correct primary color on mode change."""
    w = _make_window()

    w._on_color_mode_changed("rg")
    ss = QApplication.instance().styleSheet()
    assert "#f70404" in ss, f"RG primary (#f70404) not in stylesheet"

    w._on_color_mode_changed("bg")
    ss = QApplication.instance().styleSheet()
    assert "#0493ff" in ss, f"BG primary (#0493ff) not in stylesheet"

    print("  [OK] Color theming: stylesheet reflects primary color for RG and BG")


def test_grid_only_params_disabled_for_behavioral(tmp: Path) -> None:
    """nBaselinesStart, nBaselinesEnd, order spin boxes disabled in behavioral mode."""
    w = _make_window()
    _navigate_to_mode_config(w, "beh-rg", folder=tmp)
    page = w._mode_config_page
    page._advanced_radio.setChecked(True)

    for key in ("nBaselinesStart", "nBaselinesEnd", "order"):
        assert not page._fields[key].isEnabled(), \
            f"{key} should be disabled for behavioral mode"

    print("  [OK] Grid-only params disabled for behavioral mode in Advanced form")


def test_existing_participant_list(tmp: Path) -> None:
    """After a session, the participant appears in list_participants."""
    from participants import list_participants

    w = _make_window()
    _navigate_to_mode_config(w, "beh-rg", sub_id="X01", group="Protan", folder=tmp)
    _confirm_default(w)
    w._behavioral_session_page._start()

    participants = list_participants(tmp)
    ids = [p[0] for p in participants]
    assert "X01" in ids, f"X01 not in participants: {participants}"

    print("  [OK] list_participants returns subject after session is recorded")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

TESTS = [
    test_all_modes_default,
    test_advanced_sends_batch,
    test_behavioral_csvs_and_file,
    test_press_accumulation,
    test_live_position_rg,
    test_live_position_bg,
    test_grid_csvs,
    test_grid_done,
    test_grid_progress_increments_on_trig_edge,
    test_back_reentry,
    test_session_number_increments,
    test_session_numbers_independent_per_exp_type,
    test_color_theming,
    test_grid_only_params_disabled_for_behavioral,
    test_existing_participant_list,
]


def main() -> int:
    passed = failed = 0
    print(f"Running {len(TESTS)} offscreen tests...\n")
    for test_fn in TESTS:
        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                test_fn(Path(tmp_dir))
                passed += 1
            except Exception as exc:
                print(f"  [FAIL] {test_fn.__name__}: {exc}")
                traceback.print_exc()
                failed += 1
    print(f"\n{'='*40}")
    print(f"  {passed} passed  |  {failed} failed")
    print(f"{'='*40}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
