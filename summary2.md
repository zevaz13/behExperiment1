# Prototype 2 Development Summary

## M1 — subjectExperiment Firmware (hardware-verified, complete)

**Session:** 2026-06-29  
**Output:** `prototype2/Firmware/subjectExperiment/`  
**Status:** Built, flashed, and hardware-tested on Teensy 4.0. All 19 test scenarios in `testingM1.md` pass.

---

### Hardware context

New PCB supports five independent LED channels simultaneously. Key difference from prototype1: separate Blue and Cyan channels, Amber is always the primary reference LED.

| Signal | Pin | Role |
|--------|-----|------|
| AMBER | 0 | Primary reference (always reference LED) |
| RED | 1 | Primary stimulus (RG pair) |
| BLUE | 2 | Primary stimulus (BG pair) |
| GREEN | 3 | Secondary stimulus (both pairs) |
| CYAN | 4 | Secondary reference (BG pair only) |
| TRIGGER | 6 | EEG trigger output |
| BUTTON | 12 | Participant response button |
| AIred | 20 | Knob 1 — primary channel (Red or Blue) |
| AIgreen | 21 | Knob 2 — secondary channel (Green) |

PWM: 12-bit (0–4095). Baud: 38400.

---

### Files

| File | Description |
|------|-------------|
| `pinDefs.h` | All pin constants and `NUM_STEPS=10`, `NUM_STIMS=100` |
| `globals.h/.cpp` | All shared state and configurable parameters; `applyDefaultsRG/BG()`, `updateHalfPeriod()` |
| `ledControl.h/.cpp` | `flickerISR` (Phase A: stimulus on / Phase B: reference on); `timerSerial` fires `serialFrameOutput` every 100 ms |
| `behavioralExperiment.h/.cpp` | Knob-anchored trial loop, Bounce button debounce, walk-from-press intertrial strategy |
| `gridExperiment.h/.cpp` | Linspaced stimulus arrays, boustrophedon diagonal traversal (4 orders, see M2.9), solid baselines (101+), 1-based stimulus trial count |
| `subjectExperiment.ino` | `setup`/`loop`, `experimentThread` (TeensyThreads), `key=value` and batch config parser |
| `testingM1.md` | 19 test scenarios — all modes, parameters, trial numbering, batch config, anchoring, default-start commands |

---

### Architecture decisions

**Single flicker ISR** — one `IntervalTimer` toggles between Phase A (stimulus LEDs on, reference off) and Phase B (reference LEDs on, stimulus off) each half-period. No dark gap. The ISR reads `currentRed/Blue/Green/Amber/Cyan` globals written by the experiment thread.

**`timerSerial`** — second `IntervalTimer` fires `serialFrameOutput` every 100 ms unconditionally; returns immediately when `!started`. This means the serial frame reflects the true live state at all times.

**`experimentThread`** (TeensyThreads) — idles via `threads.yield()` when not running. On start, dispatches to `runBehavioralExperiment()` or `runGridExperiment()` based on `expMode`.

**Behavioral intertrial strategy** (matches prototype1 `knobs.cpp`):
- First trial anchors to interior margin: `minA + (maxA−minA)/5`, so the start is never at an extreme.
- ADC offset computed in raw ADC space (`rawFromMapped` inverse of `map()`), so the current physical knob position maps to the target value — the knob feels continuous, no snap.
- After button press: record press values, log response, stop flicker, wait `interTrialWait` ms.
- Next trial target = previous press ± `walkJump(range/5)`, clamped to interior margin, then re-anchor.

**Baseline trials (grid)** — solid reference LEDs via direct `analogWrite()` for `trialLength` ms, then off during ITI. No flicker timer running during baselines. Numbered 101+: start baselines are 101, 102, …; end baselines continue from `101 + nBaselinesStart`.

**Grid trial numbering** — stimulus trials are 1-based (1 through `NUM_STIMS`). Baseline trials are 101+. This makes it unambiguous in the serial stream whether a frame is a baseline or stimulus trial.

---

### Serial interface (complete command set)

**Start commands** (set mode, reset counters, start immediately):
```
beh-rg          beh-bg          grid-rg         grid-bg
```

**Default-start commands** (apply defaults for that color pair, then start):
```
beh-rg-default  beh-bg-default  grid-rg-default  grid-bg-default
```

**Utility:**
```
stop            get             defaults-rg     defaults-bg
```

**Config** (accepted any time, including while running):
```
freq=10          refAmber=2400    refCyan=0
maxA=3200        minA=0           maxB=2000        minB=0
nBaselinesStart=2  nBaselinesEnd=2  trialLength=3000  interTrialWait=750
order=1
```

**Batch config** (semicolon-separated, all applied atomically):
```
freq=10;maxA=3200;minA=0;refAmber=2400
```

---

### Serial output frame (all modes, 100 ms interval)

```
&@STIM:{trCnt},Mode:{RG|BG},RED:{v},GREEN:{v},BLUE:{v},AMBER:{v},CYAN:{v},TRIG:{0|1}%!
```

Unused channels output as 0. `trCnt` is 101+ for baselines, 1-based for grid stimulus trials, 1-based increments for behavioral.

**Behavioral response line** (logged on each button press):
```
RESP,Trial:{n},A:{primary_LED_value},B:{green_LED_value}
```

---

### Defaults

| Parameter | RG default | BG default |
|-----------|-----------|-----------|
| freq | 10 Hz | 10 Hz |
| refAmber | 2400 | 500 |
| refCyan | 0 | 1400 |
| maxA (Red/Blue) | 3200 | 2800 |
| minA | 0 | 0 |
| maxB (Green) | 2000 | 2000 |
| minB | 0 | 0 |
| nBaselinesStart | 2 | 2 |
| nBaselinesEnd | 2 | 2 |
| trialLength | 3000 ms | 3000 ms |
| interTrialWait | 750 ms | 750 ms |

---

## M2 — subjectExperiment GUI (hardware-verified, complete)

**Sessions:** 2026-06-30
**Output:** `prototype2/GUIsubjectExp/`
**Spec:** `docs/prototype2/prototype2-subjectExperiment-gui-requirements.md`
**Status:** M2.1–M2.5 complete; M2.6, M2.7, M2.8 bug-fix rounds applied; GUI robustness hardening from `GUIrevision.md` applied. 23/23 offscreen tests pass.

---

### Files

| File | Description |
|------|-------------|
| `pyproject.toml` | uv project; deps: pyside6 ≥6.11.1, pyqtgraph ≥0.14.0, pyserial ≥3.5 |
| `main.py` | Entry point — creates `QApplication` and `MainWindow` |
| `serial_link.py` | `SerialLink(QThread)` — background line reader, `line_received(str)` signal, 38400 baud; `find_teensy_port()` by PJRC vendor ID |
| `protocol.py` | `parse_get_response`, `parse_stream_frame`, `parse_resp`, `build_batch_command` |
| `participants.py` | 3-CSV model, `list_participants`, `next_session_number`, `record_behavioral_session`, `record_grid_session` |
| `main_window.py` | All pages + `MainWindow` coordinator |
| `test_offscreen.py` | 23 offscreen tests (`QT_QPA_PLATFORM=offscreen`), all passing |
| `docs/prototype2/subjectExperiment-gui-guide.md` | User guide: startup, flow, parameters, data files, troubleshooting |

---

### Application flow

```
ConnectPage → ParticipantPage → ExperimentSelectPage → ModeConfigPage → Session
                                        ↑                                   |
                                        └─────────── Back (re-queries get) ─┘
```

---

### Page descriptions

**ConnectPage** — auto-detects Teensy by PJRC vendor ID `0x16C0`, retries every 500 ms up to 6 times, then falls back to manual port dropdown. Confirms firmware identity by sending `get` and accumulating lines until a `mode=` key appears in the response.

**ParticipantPage** — folder picker (persisted via `QSettings`), toggle between existing participant (from `participants_master.csv`) and new participant (Subject ID + Group). Re-reads master CSV on every `showEvent`.

**ExperimentSelectPage** — four radio buttons: `beh-rg`, `beh-bg`, `grid-rg`, `grid-bg`. No default preselected. On radio toggle, emits `color_mode_changed` so the app stylesheet updates immediately. On Continue, sends `get` to the firmware and waits for the full response before showing ModeConfigPage.

**ModeConfigPage** — three radio options:
- *Default* — sends a full explicit batch of factory defaults (`freq=10;refAmber=...;order=1;...`) so all params including order are reliably reset
- *Current* — navigates with firmware's current GET response settings, no commands sent
- *Configure* — spin box form; for behavioral mode the 5 grid-irrelevant params (nBaselinesStart, nBaselinesEnd, order, trialLength, interTrialWait) are hidden; sends batch for only changed fields

**BehavioralSessionPage** — params label (mode, freq, ranges, Ref Amber, Ref Cyan) above the controls. Scatter plot (primary LED vs Green, black background). Live position marker (reference color, circle) updated from every `&@...%!` stream frame. Press markers (gray X) and running median marker (primary color, star) updated on each `RESP,Trial:n,A:v,B:v` event. Press table (Trial / Primary / Green) right of the plot. Every Start creates a new session file and CSV row.

**GridSessionPage** — params label (mode, freq, ranges, Ref Amber, Ref Cyan, Order). 10×10 dot scatter plot (unvisited: dark gray, visited: primary color, current: reference color larger). Progress bar over nBaselinesStart + 100 + nBaselinesEnd total trials, incremented on each STIM (trial-number) change rather than a TRIG edge, so it is robust to the 100 ms sample rate (a short ITI can hide a TRIG edge between samples; the next trial's STIM is always observed). Position and visited-marking are gated on TRIG=1 so the inter-trial wait (LEDs zeroed, STIM unchanged) does not drag the marker to (0,0); each presented stimulus cell is marked visited at presentation and stays marked. TRIG indicator label lights up in reference color when trigger is HIGH. Status label shows "Baseline trial", "Stimulus N / 100", or "Done". Completes on `DONE` line. Every Start creates a new CSV row.

---

### Serial protocol differences from prototype1

| Aspect | Prototype 1 | Prototype 2 |
|--------|-------------|-------------|
| Start commands | `BEHAVIORALSTART`, `GRIDSTART` | `beh-rg`, `beh-bg`, `grid-rg`, `grid-bg` |
| Stop | `BEHAVIORALSTOP`, `GRIDSTOP` | `stop` |
| Query | `BEHAVIORALGET`, `GRIDGET` | `get` (multi-line response) |
| Set | `BEHAVIORALSET key val, ...` | `key=value;key2=val2` |
| GET response | single space-separated line | multi-line key=value, complete on `mode=` |
| Stream frame | `0@3@2400@1420@980@0` | `&@STIM:3,Mode:RG,RED:0,...%!` |
| Press events | embedded in stream (Press field = 1) | separate `RESP,Trial:n,A:v,B:v` line |
| Completion | `GRID DONE` | `DONE` |

---

### Color theming

A stylesheet template with `{primary}` is applied via `QApplication.setStyleSheet()` whenever the color mode changes. Radio button indicators use a fixed `#ff7256` (visible on black). QSpinBox up/down buttons defined explicitly to fix Windows up-arrow click area.

| Mode | Primary | Secondary | Reference |
|------|---------|-----------|-----------|
| RG | `#f70404` (Red) | `#b1ff01` (Green) | `#fabd04` (Amber) |
| BG | `#0493ff` (Blue) | `#b1ff01` (Green) | `#50fefe` (Cyan) |

Plot brushes (live position, median, grid dot colors) are updated programmatically when `start_session()` is called on a session page. The TRIG indicator uses the reference color when active.

---

### Data model

**`participants_master.csv`** — `sub_id, group, experiment, mode, session, datetime`

**`participants_behavioral.csv`** — `sub_id, group, session, file, datetime, mode, freq, refAmber, refCyan, maxA, minA, maxB, minB, trialLength, interTrialWait`

**`participants_grid.csv`** — same minus `file`, plus `nBaselinesStart, nBaselinesEnd, order`

**Session data file** (`{sub_id}_{mode}_R{n}.txt`, behavioral only) — header `Trial Primary Green`, one row per `RESP` event appended in real time. Created fresh on every Start press.

Session numbers are scoped per `(sub_id, mode_str)` pair (e.g. beh-rg and beh-bg are independent). `next_session_number` scans both the CSV and existing `.txt` files in the folder to find the next safe number.

---

### Key design decisions

**`settings["mode"]` stamped in `_on_mode_confirmed`** — before passing settings to the session page, MainWindow overwrites `settings["mode"]` with the user's ExperimentSelect choice. This prevents a stale firmware GET response (which might report the previous mode) from corrupting the CSV mode column.

**Factory Default sends explicit batch, not `defaults-rg/bg`** — hardware testing showed the firmware's `defaults-rg` command did not reliably reset `order`. The Default path now sends `freq=10;refAmber=...;order=1;...` explicitly, guaranteeing all parameters including order are set.

**Every Start is a new session** — both behavioral and grid pages call `_open_run_file()` / `_record_session()` unconditionally on every Start, so Stop → Start always increments the run counter and creates a new file.

---

### M2.8 — Grid visited-cell fix

Reported: the grid marker jumped back to (0,0) during the inter-trial wait and only that cell stayed marked; visited stimulus cells were not kept marked.

Root cause: during the ITI the firmware zeroes the LED outputs but keeps the same STIM and TRIG=0. `GridSessionPage._on_line` updated the current cell from every frame, so ITI frames mapped RED=0/GREEN=0 to cell (0,0), and the subsequent visited-marking recorded (0,0) instead of the real stimulus cell.

Fix: position and marking are now gated on TRIG=1; each presented stimulus cell is added to `_visited` at presentation time and stays marked; the current cell is highlighted on top. Regression test `test_grid_visited_cells_stay_marked` added.

---

### GUI robustness hardening (code review — `GUIrevision.md`)

A review of the working GUI (`GUIrevision.md`) identified latent issues around the shared `SerialLink` lifecycle; the High/Medium items were fixed:

- **Stale signal connections (High)** — session pages previously connected `_on_line` once and never disconnected, so after visiting both behavioral and grid pages, both consumed the serial stream. Now session pages use balanced `_attach`/`detach`; `MainWindow` tracks the active session page and detaches it on Back, so only the visible page processes frames.
- **Connection loss (High)** — `connection_lost` is now owned by `MainWindow`. On a drop it tears down the session/link and auto-returns to the Connect page, which restarts auto-detection. `ConnectPage` cleanly transfers link ownership on handoff and gained `restart()` / `close_link()`.
- **Exit cleanup (Medium)** — `MainWindow.closeEvent` now closes the link so the reader `QThread` and serial port are released.
- **Subject-ID sanitization (Medium)** — `ParticipantPage` rejects subject IDs that are not `[A-Za-z0-9_-]+`, since the ID becomes a filename stem.
- **Grid progress robustness (Medium)** — progress counting moved from TRIG-edge detection to STIM-change detection (see GridSessionPage above).
- **Grid data logging (Medium, by decision)** — grid sessions intentionally log only the config CSV row; per-trial data is captured by the EEG acquisition system, time-locked via the hardware TRIG line. Documented in the `GridSessionPage` docstring and the GUI guide.

Three new tests cover these: `test_inactive_session_page_is_detached`, `test_connection_lost_returns_to_connect`, `test_subject_id_rejects_invalid_chars`.

---

## M2.9 — Firmware grid-sequence fix (boustrophedon traversal)

**Output:** `prototype2/Firmware/subjectExperiment/gridExperiment.cpp`
**Status:** Fixed, logic-verified, and flashed + hardware-tested on Teensy 4.0. Complete.

Comparison of the grid stimulus ordering between prototype1 (`prototype/firmware/gridEEG/sequence.cpp`) and prototype2 (`subjectExperiment/gridExperiment.cpp`) found they walked the grid's anti-diagonals differently:

- **Prototype1** — boustrophedon (serpentine): alternates direction on each successive diagonal, so the path is continuous and consecutive stimuli stay adjacent.
- **Prototype2 (before fix)** — unidirectional: every diagonal walked the same way, jumping back across the grid at each diagonal boundary.

The order-flip convention (order 2 flips Y, 3 flips X, 4 flips both) already matched; only the diagonal direction differed. `buildDiagonalCoords` was rewritten to the boustrophedon traversal (even diagonal sum: index descending; odd: ascending — parity matched to prototype1's `d = (x-1)+(y-1)+2`). Verified in Python that prototype2 now reproduces prototype1's full 100-stimulus sequence exactly for all four orders. The GUI is unaffected — it infers grid positions from the streamed LED values, not from traversal order.
