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


def _confirm_current(w: MainWindow) -> None:
    """Use firmware's current settings — no serial commands sent."""
    page = w._mode_config_page
    page._current_radio.setChecked(True)
    page._confirm()


def _confirm_factory(w: MainWindow) -> None:
    """Apply factory defaults (sends defaults-rg/bg, uses hardcoded defaults)."""
    page = w._mode_config_page
    page._factory_radio.setChecked(True)
    page._confirm()


def _confirm_configure(w: MainWindow, overrides: dict[str, int]) -> None:
    """Configure with specific param overrides, send batch command."""
    page = w._mode_config_page
    page._configure_radio.setChecked(True)
    for key, val in overrides.items():
        page._fields[key].setValue(val)
    page._confirm()


# Keep alias so tests that just want a neutral "proceed" are readable.
_confirm_default = _confirm_current


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


def test_configure_sends_batch(tmp: Path) -> None:
    """Configure mode sends exactly one batch command with only changed params."""
    w = _make_window()
    fake = _navigate_to_mode_config(w, "beh-rg", folder=tmp)
    _confirm_configure(w, {"freq": 20, "maxA": 3000})

    batch_cmds = [c for c in fake.sent if ";" in c and "=" in c]
    assert len(batch_cmds) == 1, f"Expected 1 batch command, got {batch_cmds}"
    parts = dict(tok.split("=") for tok in batch_cmds[0].split(";"))
    assert parts.get("freq") == "20", f"freq missing/wrong in batch: {parts}"
    assert parts.get("maxA") == "3000", f"maxA missing/wrong in batch: {parts}"
    assert "minA" not in parts, f"unchanged param minA in batch: {parts}"

    print("  [OK] Configure sends correct batch command (changed params only)")


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
    assert rows[-1]["mode"] == "beh-rg", f"master mode wrong: {rows[-1].get('mode')}"
    assert rows[-1]["session"] == "1"

    # Behavioral CSV
    beh_csv = tmp / "participants_behavioral.csv"
    assert beh_csv.exists(), "participants_behavioral.csv not created"
    rows = list(csv.DictReader(beh_csv.open()))
    assert rows[-1]["sub_id"] == "P01"
    assert rows[-1]["mode"] == "beh-rg"
    fname = rows[-1].get("file", "")
    assert fname.startswith("P01_beh-rg_R"), f"file field wrong: {fname}"

    # Session data file
    sess = tmp / "P01_beh-rg_R1.txt"
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

    sess = tmp / "P02_beh-rg_R1.txt"
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
    assert master_rows[-1]["mode"] == "grid-rg", f"master mode wrong: {master_rows[-1].get('mode')}"
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


def test_grid_progress_increments_on_stim_change(tmp: Path) -> None:
    """Progress increments when STIM changes (a trial finished), not on TRIG edge.

    STIM-change counting is robust to the 100 ms sampling rate: a short ITI that
    falls between two samples can hide a TRIG 1->0 edge, but the next trial's new
    STIM value is always observed.
    """
    w = _make_window()
    fake = _navigate_to_mode_config(w, "grid-rg", sub_id="G03", folder=tmp)
    _confirm_default(w)
    page = w._grid_session_page
    page._start()

    assert page._progress.value() == 0

    # First trial begins — no prior trial to count yet.
    fake.inject(_rg_frame(1, red=1600, green=1000, trig=1))
    assert page._progress.value() == 0, "Progress incremented before any trial finished"

    # Repeated frames for the same trial (including the ITI sample) do not count.
    fake.inject(_rg_frame(1, red=1600, green=1000, trig=0))
    assert page._progress.value() == 0, "Progress counted the same trial twice"

    # New STIM value => previous trial finished.
    fake.inject(_rg_frame(2, red=1800, green=900, trig=1))
    assert page._progress.value() == 1, \
        f"Progress should be 1 after STIM change, got {page._progress.value()}"

    # A trial whose entire ITI is missed (no trig=0 sample) still counts.
    fake.inject(_rg_frame(3, red=1400, green=1100, trig=1))
    assert page._progress.value() == 2, \
        f"Progress should be 2 even without a TRIG-low sample, got {page._progress.value()}"

    print("  [OK] Grid progress increments on STIM change (timing-robust)")


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


def test_behavioral_hides_irrelevant_params(tmp: Path) -> None:
    """nBaselinesStart/End, order, trialLength, interTrialWait hidden for behavioral."""
    from main_window import _BEHAVIORAL_HIDDEN
    w = _make_window()
    _navigate_to_mode_config(w, "beh-rg", folder=tmp)
    page = w._mode_config_page
    page._configure_radio.setChecked(True)

    for key in _BEHAVIORAL_HIDDEN:
        spin = page._fields[key]
        assert not page._form.isRowVisible(spin), \
            f"{key} row should be hidden for behavioral mode"

    # freq and LED params must remain visible
    for key in ("freq", "refAmber", "maxA", "minA", "maxB", "minB"):
        spin = page._fields[key]
        assert page._form.isRowVisible(spin), \
            f"{key} row should be visible for behavioral mode"

    print("  [OK] Irrelevant params hidden for behavioral; LED/freq params visible")


def test_grid_shows_all_params(tmp: Path) -> None:
    """All 12 params are visible for grid mode."""
    from main_window import _BEHAVIORAL_HIDDEN
    w = _make_window()
    _navigate_to_mode_config(w, "grid-rg", folder=tmp)
    page = w._mode_config_page
    page._configure_radio.setChecked(True)

    for key in _BEHAVIORAL_HIDDEN:
        spin = page._fields[key]
        assert page._form.isRowVisible(spin), \
            f"{key} row should be visible for grid mode"

    print("  [OK] All params visible for grid mode")


def test_factory_defaults_sends_batch(tmp: Path) -> None:
    """Factory Default sends a full explicit batch (not defaults-rg/bg) to avoid order bug."""
    from main_window import _DEFAULTS
    for mode_str, pair in (("beh-rg", "rg"), ("grid-bg", "bg")):
        w = _make_window()
        fake = _navigate_to_mode_config(w, mode_str, folder=tmp)
        _confirm_factory(w)

        # Should send a batch command containing order=1 explicitly.
        batch_cmds = [c for c in fake.sent if ";" in c and "=" in c]
        assert batch_cmds, f"No batch command sent for {mode_str}: {fake.sent}"
        parts = dict(tok.split("=") for tok in batch_cmds[0].split(";"))
        assert parts.get("order") == "1", \
            f"order not set to 1 in factory batch for {mode_str}: {parts}"
        assert parts.get("freq") == _DEFAULTS[pair]["freq"], \
            f"freq mismatch in factory batch: {parts}"

        # Should NOT send the old defaults-rg/bg command.
        assert f"defaults-{pair}" not in fake.sent, \
            f"defaults-{pair} should not be sent (use explicit batch instead)"

        # Settings stamped with mode_str.
        sess_settings = (w._behavioral_session_page if mode_str.startswith("beh")
                         else w._grid_session_page)._settings
        assert sess_settings.get("mode") == mode_str, \
            f"mode in session settings wrong: {sess_settings.get('mode')}"

    print("  [OK] Factory Default sends explicit batch with order=1 (not defaults-rg/bg)")


def test_stop_then_start_creates_new_session(tmp: Path) -> None:
    """Stop then Start creates a new session file and CSV row each time."""
    w = _make_window()
    fake = _navigate_to_mode_config(w, "beh-rg", sub_id="R01", folder=tmp)
    _confirm_default(w)
    page = w._behavioral_session_page

    page._start()   # session 1
    fake.inject("RESP,Trial:1,A:1600,B:1000")
    page._stop()

    page._start()   # session 2 — must create a NEW file
    fake.inject("RESP,Trial:1,A:1700,B:900")

    beh_rows = list(csv.DictReader((tmp / "participants_behavioral.csv").open()))
    sessions = [int(r["session"]) for r in beh_rows if r["sub_id"] == "R01"]
    assert sessions == [1, 2], f"Expected [1, 2] sessions, got {sessions}"

    assert (tmp / "R01_beh-rg_R1.txt").exists(), "Session 1 file missing"
    assert (tmp / "R01_beh-rg_R2.txt").exists(), "Session 2 file missing"

    # Each file should have only its own press.
    s1 = (tmp / "R01_beh-rg_R1.txt").read_text().splitlines()
    s2 = (tmp / "R01_beh-rg_R2.txt").read_text().splitlines()
    assert len(s1) == 2, f"Session 1 file should have header + 1 press, got {s1}"
    assert len(s2) == 2, f"Session 2 file should have header + 1 press, got {s2}"

    print("  [OK] Stop then Start creates a new session file and CSV row each time")


def test_session_numbers_independent_per_mode(tmp: Path) -> None:
    """beh-rg and beh-bg have independent session counters for the same subject."""
    for mode in ("beh-rg", "beh-bg"):
        w = _make_window()
        _navigate_to_mode_config(w, mode, sub_id="M01", folder=tmp)
        _confirm_default(w)
        w._behavioral_session_page._start()

    beh_rows = list(csv.DictReader((tmp / "participants_behavioral.csv").open()))
    rg_sessions = [int(r["session"]) for r in beh_rows if r["sub_id"] == "M01" and r["mode"] == "beh-rg"]
    bg_sessions = [int(r["session"]) for r in beh_rows if r["sub_id"] == "M01" and r["mode"] == "beh-bg"]
    assert rg_sessions == [1], f"beh-rg session should be [1], got {rg_sessions}"
    assert bg_sessions == [1], f"beh-bg session should be [1], got {bg_sessions}"

    # File names should include mode
    assert (tmp / "M01_beh-rg_R1.txt").exists()
    assert (tmp / "M01_beh-bg_R1.txt").exists()

    print("  [OK] beh-rg and beh-bg have independent session counters and file names")


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


def test_grid_visited_cells_stay_marked(tmp: Path) -> None:
    """ITI frames (TRIG=0, LEDs zeroed) must not move the marker to (0,0);
    presented stimulus cells stay marked as new trials arrive (M2.8)."""
    from main_window import _nearest_index

    w = _make_window()
    fake = _navigate_to_mode_config(w, "grid-rg", sub_id="V01", folder=tmp)
    _confirm_default(w)
    page = w._grid_session_page
    page._start()

    a_levels, b_levels = page._a_levels, page._b_levels
    cell1 = (_nearest_index(a_levels, 1600), _nearest_index(b_levels, 1000))
    cell2 = (_nearest_index(a_levels, 3200), _nearest_index(b_levels, 2000))
    assert cell1 != (0, 0), "test premise: cell1 must be a non-origin cell"

    # Stimulus presented (TRIG=1).
    fake.inject(_rg_frame(1, red=1600, green=1000, trig=1))
    assert page._current == cell1, f"current cell wrong: {page._current}"
    assert cell1 in page._visited

    # Inter-trial wait: same STIM, LEDs zeroed, TRIG=0. Marker must hold.
    fake.inject(_rg_frame(1, red=0, green=0, trig=0))
    assert page._current == cell1, f"marker jumped during ITI to {page._current}"
    assert (0, 0) not in page._visited, "ITI origin frame was wrongly marked visited"
    assert cell1 in page._visited, "stimulus cell lost its mark during ITI"

    # Next stimulus: previous cell stays marked, new one becomes current.
    fake.inject(_rg_frame(2, red=3200, green=2000, trig=1))
    assert page._current == cell2
    assert cell1 in page._visited, "previously visited cell lost its mark"
    assert cell2 in page._visited

    print("  [OK] Grid visited cells stay marked; ITI does not jump to (0,0)")


def test_inactive_session_page_is_detached(tmp: Path) -> None:
    """Leaving a session detaches its handler so it stops consuming the stream."""
    w = _make_window()
    fake = _navigate_to_mode_config(w, "beh-rg", sub_id="D01", folder=tmp)
    _confirm_default(w)
    beh = w._behavioral_session_page
    assert beh._link is fake, "Behavioral page not attached on session start"

    w._on_back_requested()
    assert beh._link is None, "Behavioral page still attached after Back"

    # Switch to a grid session; the behavioral page must stay detached and inert.
    w._on_mode_selected("grid-bg")
    fake.inject_get("grid-bg")
    _confirm_default(w)
    grid = w._grid_session_page
    grid._start()
    assert beh._link is None, "Behavioral page re-attached during grid session"

    rows_before = beh._table.rowCount()
    fake.inject("RESP,Trial:1,A:1600,B:1000")
    assert beh._table.rowCount() == rows_before, \
        "Detached behavioral page still processed a RESP line"

    print("  [OK] Inactive session page is detached and inert")


def test_connection_lost_returns_to_connect(tmp: Path) -> None:
    """connection_lost tears down the session and returns to the Connect page."""
    w = _make_window()
    fake = _navigate_to_mode_config(w, "grid-rg", sub_id="C01", folder=tmp)
    _confirm_default(w)
    w._grid_session_page._start()

    fake.connection_lost.emit("device unplugged")

    assert w._stack.currentWidget() is w._connect_page, \
        "Did not return to Connect page after connection loss"
    assert w._link is None, "Link reference not cleared after connection loss"
    assert w._active_session_page is None, "Active session not torn down"
    assert w._grid_session_page._link is None, "Grid page still attached after disconnect"

    print("  [OK] Connection loss returns to Connect page and tears down session")


def test_subject_id_rejects_invalid_chars(tmp: Path) -> None:
    """ParticipantPage rejects filesystem-unsafe subject IDs."""
    w = _make_window()
    w._on_connected(FakeSerialLink())
    page = w._participant_page
    page._folder_edit.setText(str(tmp))
    page._new_radio.setChecked(True)

    confirmed: list = []
    page.participant_confirmed.connect(lambda *a: confirmed.append(a))

    page._sub_id_edit.setText("bad/id")
    page._confirm()
    assert not confirmed, "Invalid subject ID was accepted"
    assert "letters" in page._error_label.text().lower(), \
        f"No validation error shown, got: {page._error_label.text()!r}"

    page._sub_id_edit.setText("good_ID-01")
    page._confirm()
    assert confirmed and confirmed[-1][0] == "good_ID-01", \
        "Valid subject ID was not accepted"

    print("  [OK] Subject ID validation rejects unsafe characters")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

TESTS = [
    test_all_modes_default,
    test_configure_sends_batch,
    test_behavioral_csvs_and_file,
    test_press_accumulation,
    test_live_position_rg,
    test_live_position_bg,
    test_grid_csvs,
    test_grid_done,
    test_grid_progress_increments_on_stim_change,
    test_grid_visited_cells_stay_marked,
    test_inactive_session_page_is_detached,
    test_connection_lost_returns_to_connect,
    test_subject_id_rejects_invalid_chars,
    test_back_reentry,
    test_session_number_increments,
    test_session_numbers_independent_per_exp_type,
    test_color_theming,
    test_behavioral_hides_irrelevant_params,
    test_grid_shows_all_params,
    test_factory_defaults_sends_batch,
    test_stop_then_start_creates_new_session,
    test_session_numbers_independent_per_mode,
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
