# Plan

## Prototype 2 Rapid Experiment Prototyping Tool

Design spec: `docs/superpowers/specs/2026-07-01-configurable-firmware-design.md`
Requirements: `docs/prototype2/requirementsREP.md`

Output paths:
- Firmware: `prototype2/Firmware/configurableFirmware/`
- GUI: `prototype2/GUI/configurableFirmware/`

### Testing convention
- Firmware: manual test instruction files (`tests/test_mN_instructions.md`) run via Arduino IDE serial monitor
- GUI: offscreen tests + mock serial link

---

## Milestones

### M1 — Firmware: shared infrastructure
Files: `globals.h/cpp`, `pinDefs.h`, `ledControl.h/cpp`, `serialParser.h/cpp`, `dataFrame.h/cpp`, `timerManager.h/cpp`, skeleton `configurableFirmware.ino`
Test: script verifies `MODE` command accepted, `GET` returns defaults, data frame arrives every ~100ms.
- [x] Implement shared modules
- [x] Write serial test script for M1 (`tests/test_m1.py`)

### M2 — Firmware: Sub-mode A (Solid)
Files: `solidMode.h/cpp`, full FSM, real-time LED commands in RUNNING state.
Test: `tests/test_m2_instructions.md` — manual via Arduino IDE serial monitor.
- [x] Implement solidMode
- [x] Write test instructions for M2

### M3 — Firmware: Hue sensor module
Files: `hueSensor.h/cpp`. Returns `-99` fields when absent; returns error on `START` with `hue=true` if not detected.
Test: `tests/test_m3_instructions.md` — manual via Arduino IDE serial monitor.
- [x] Implement hueSensor module
- [x] Write test instructions for M3

### M4 — Firmware: Sub-mode B (Linear)
Files: `linearMode.h/cpp`, baseline support, trigger signal.
Test: `tests/test_m4_instructions.md` — manual via Arduino IDE serial monitor.
- [x] Implement linearMode
- [x] Write test instructions for M4

### M4.1 Issues
- tried  SET LEDA BLUE ref1Led YELLOW, ref1Int 200, minA 500, maxA 3000, steps 5, freq 2, trialLength 2000, interTrialWait 300, nBaselinesStart 1, nBaselinesEnd 0 nothing happened.
    -counts are counting, but no LED was driven
- Notice that Reference LEDs and intensities are different than those for baseline. The baseline ones are only used during the baseline stage. The reference ones are to be used during the second part of the period. As it is now, they are mixed. 
- The LED parameter in the frame should be the name of the selected LED, then the intensity value should just go to the respective column of the frame.
- Trial counts work OK, Setting and getting works ok for all parameters.
- LEDA value grows during trials as expected.
- Hue sensor works succesfully. 
- Following work well as expected. 
    - SET LEDA CYAN, minA 500, maxA 3000, steps 3, freq 10, trialLength 1000, interTrialWait 300, hue 1 
    - SET LEDA YELLOW, minA 500, maxA 3000, steps 3, freq 10, trialLength 1000, interTrialWait 300, hue 1 
    - SET LEDA GREEN, minA 500, maxA 3000, steps 3, freq 10, trialLength 1000, interTrialWait 300, hue 1
    - SET LEDA BLUE, minA 500, maxA 3000, steps 3, freq 10, trialLength 1000, interTrialWait 300, hue 1
    - SET LEDA RED, minA 500, maxA 3000, steps 3, freq 10, trialLength 1000, interTrialWait 300, hue 1 

#### M4.1 Fix plan

Root causes identified by reading `linearMode.cpp`, `serialParser.cpp`, `dataFrame.cpp`, `globals.h/cpp`:

1. **Silent LED-name failures.** `parseLedId()` returns `LED_NONE` for any unrecognized string, and `applyParam()` always reports `OK SET` for LED-name params regardless of validity. A malformed command (e.g. a missing comma merging two params into one value) silently resets the target LED to `NONE` with no error — this is why "nothing happened" while trial counting kept working.
   - [x] Add a name-validation check before assigning any `LedId` param (`LEDA`, `LEDB`, `bgStim1Led`, `bgStim2Led`, `ref1Led`, `ref2Led`, `ref3Led`, new `baselineLed1/2/3`). Reject (return false → existing `ERR unknown param` path) unless the value is exactly one of `RED/YELLOW/GREEN/BLUE/CYAN/NONE`.

2. **Baseline LEDs mixed with reference LEDs.** `runBaselines()` currently reuses `ref1Led/ref2Led/ref3Led` (the flicker ref-phase LEDs) to drive the solid baseline display. Per decision: baseline gets its own independent 3-slot config.
   - [x] `globals.h/cpp`: add `LedId baselineLed1, baselineLed2, baselineLed3` (default `LED_NONE`) and `int baselineLed1Val, baselineLed2Val, baselineLed3Val` (default 0, range [0,4095]). Reset in `applyDefaults()`.
   - [x] `serialParser.cpp`: add SET keys `baselineLed1/2/3` (LED name) and `baselineLed1/2/3Val` (int), add to `printGet()`.
   - [x] `linearMode.cpp`: `runBaselines()` drives `baselineLed1/2/3` at their `Val` intensities instead of `ref1/2/3`. `ref1/2/3` remain exclusively used by `linearFlickerISR()`'s reference phase.
   - [x] Since Grid/Behavioral (M5/M6) will need the identical baseline behavior, keep `runBaselines()` easy to share (either leave as-is and copy when M5 lands, or lift into a shared helper now — decide at M5 time, not blocking this fix). **Done at M5 time**: extracted to `baselineRunner.h/cpp`, used by both `linearMode.cpp` and `gridMode.cpp`.

3. **Frame LEDA/LEDB field redundant with intensity columns.** Per requirements (`requirementsREP.md:133`) and your direction, the frame's `LEDA`/`LEDB` fields should report the *name* of the assigned LED, not its intensity (which is already visible in the matching Red/Yellow/Green/Blue/Cyan column).
   - [x] `dataFrame.cpp`: print `ledIdStr(ledA)` / `ledIdStr(ledB)` instead of `ledVal[ledA]`/`ledVal[ledB]`. Unset stays `"NONE"`.
   - [x] Update design spec (`docs/superpowers/specs/2026-07-01-configurable-firmware-design.md:113-117`) and `docs/prototype2/statusREP.md` frame description to match.

4. **Minor: flicker phase order.** `linearFlickerISR()` toggles `flickerPhase` before checking it, so the very first half-period after `startFlicker()` runs the *reference* phase instead of the *stim* phase (spec says stim runs first). Fix by seeding `flickerPhase = true` (instead of `false`) right before `startFlicker()` in `runLinear()`, so the first toggle lands on stim.
   - [x] Fix in `linearMode.cpp::runLinear()`.

4b. **Found during review: out-of-bounds write when LEDA unset.** `runLinear()` did `ledVal[ledA] = stimA[i]` with no guard — if `LEDA` is left at its default `LED_NONE` (enum value 5) and `START` is issued, this wrote past the end of the 5-element `ledVal[]` array. Directly adjacent to the reported issue since a rejected/absent `LEDA` value now correctly stays `LED_NONE` (see fix 1) rather than being silently misassigned.
   - [x] Guard with `if (ledA != LED_NONE)` in `linearMode.cpp::runLinear()`.

5. **Docs/tests**
   - [x] Update `tests/test_m4_instructions.md` to use `baselineLed1/baselineLed1Val` instead of `ref1Led/ref1Int` for baseline steps, and to reflect `LEDA`/`LEDB` frame fields now being LED names.
   - [x] Update `docs/prototype2/statusREP.md` SET-commands table and globals reference.

**Status: hardware verified — all `tests/test_m4_instructions.md` sections passed.** `printGetParam()` was left as-is for `baselineLed*` since it already omits the analogous `ref1/2/3Led`/`bgStim*Led` single-param lookups (pre-existing gap, out of scope here) — `GET` (full dump) covers them.

### M5 — Firmware: Sub-mode C (Grid)
Files: `gridMode.h/cpp`, `baselineRunner.h/cpp` (extracted shared baseline logic, now also used by `linearMode.cpp`).
Test: `tests/test_m5_instructions.md` — manual via Arduino IDE serial monitor.
- [x] Implement gridMode: two-LED flicker (LEDA+LEDB+bgStim1+bgStim2 stim phase vs. ref1/2/3 ref phase), diagonal boustrophedon `steps x steps` traversal with `gridOrder` transform (order 0 == order 1, matching `subjectExperiment/gridExperiment.cpp`), shared baselines via `baselineRunner`
- [x] Add LED-uniqueness validation to `serialParser.cpp::applyParam()` (rejects same LED assigned twice within a phase group: stim `LEDA/LEDB/bgStim1/bgStim2`, ref `ref1/2/3`, baseline `baselineLed1/2/3`); applies to both Linear and Grid since the parser is shared
- [x] Wire `gridMode.h` include + `MODE_GRID` case into `configurableFirmware.ino`
- [x] Write test instructions for M5

**Status: hardware verified — all `tests/test_m5_instructions.md` sections passed.**

### M6 — Firmware: Sub-mode D (Behavioral)
Files: `behavioralMode.h/cpp`, ADC knob control, button press frame.
Test: `tests/test_m6_instructions.md` — manual via Arduino IDE serial monitor; button press and ADC behavior verified manually.
- [x] Implement behavioralMode: two-phase flicker (stim `LEDA/LEDB` live knob values + `bgStim1/2` vs. ref `ref1/2/3`), anchor-offset knob strategy mirroring `subjectExperiment/behavioralExperiment.cpp` (`rawFromMapped`/`wrapAdc`/`walkJump`, interior-margin start and walk clamp), no baselines, no fixed trial count, runs until STOP
- [x] Physical button (`Bounce` on `PIN_BUTTON`) and serial `PRESS` both end the trial identically, via a new `guiPressRequest` flag consumed by `runBehavioral()` (serial parsing and the experiment loop run on different TeensyThreads threads, so `PRESS` can't call the trial-advance logic directly)
- [x] `SET hue 1` rejected while `MODE_BEHAVIORAL` is active (explicit requirement — hue not supported in this mode), reusing the same `applyParam()` false-return path as the other validations
- [x] Wire `behavioralMode.h` include + `MODE_BEHAVIORAL` case into `configurableFirmware.ino`
- [x] Write test instructions for M6

**Status: hardware verified — all `tests/test_m6_instructions.md` sections passed. All 4 firmware sub-modes (M1-M6) are now done and hardware-verified.**

### M7 — GUI: project setup + serial infrastructure
Files: `pyproject.toml` (uv), `main.py`, `serial_link.py`, `protocol.py`
Test: unit tests for protocol command builders; mock serial test for frame parsing.
- [x] Set up uv project (`prototype2/GUI/configurableFirmware/`, deps: pyside6, pyqtgraph, pyserial)
- [x] Implement serial_link (unchanged from `GUIsubjectExp` — transport layer is protocol-agnostic) and protocol modules (new `MODE`/`SET`/`GET`/`START`/`STOP` protocol, `FRAME@` 15-field parser with `LEDA`/`LEDB` as LED-name strings)
- [x] Write unit and mock serial tests (in `test_offscreen.py`, run via `UV_PROJECT_ENVIRONMENT=.venv-linux uv run python test_offscreen.py`)

### M8 — GUI: main window + mode selector
Files: `main_window.py` with mode-selector screen and screen switching.
Test: offscreen test verifies mode buttons present and trigger correct screen transitions.
- [x] Implement main_window: `ConnectPage` (adapted from `GUIsubjectExp`), `ModeSelectPage` (SOLID/LINEAR/GRID/BEHAVIORAL buttons + a hue checkbox next to Solid, since Solid has no config screen of its own to ask there), shared `PlaceholderPage` for Linear/Grid/Behavioral until M10-M12 land
- [x] Write offscreen test for M8 (navigation, placeholder routing, Back/STOP, connection-loss teardown)

### M9 — GUI: Sub-mode A view
Files: `solid_view.py` — 5 sliders, color swatches, optional hue panel.
Test: offscreen test verifies sliders emit correct SET commands; hue panel shown/hidden correctly.
- [x] Implement solid_view: 5 vertical sliders (synced to spinboxes) with color swatches, each sending `SET <COLOR>LED <value>`; incoming `FRAME@` lines update the displayed values without re-sending (no feedback loop); hue bar plot (R/G/B) shown only when hue was enabled at mode-select time; press rows accumulate in memory (`_press_log`) only while hue is active, per requirements — no visible table yet, saving is a later milestone
- [x] Write offscreen test for M9 (slider->SET, sync, hue visibility, frame-driven updates, press-log gating)

**Status: implemented and visually smoke-tested via offscreen screenshot rendering (`QT_QPA_PLATFORM=offscreen`). All 17 `test_offscreen.py` tests pass. Needs a real hardware run (Windows + Teensy) to confirm serial round-trip, since this can't be tested from WSL.**

#### M9.1 Solid view issues. 
- When selecting the solid view with hue sensor, there is a slight delay in how the bars are plotted. They keep moving for a long time. after changes have been done.
- The auto scale is making things not look good. Maybe lets start with a default scale value (say 1000), but add a text box to change it, instead of it being dynamical. 
- When auto scaling, the sliders also scale for some reason. They should always map from 0 to 4095

**Root cause**: all three symptoms trace back to pyqtgraph's default Y-axis auto-range on the hue plot. It re-tweens the view range toward a new target on every incoming frame (the "keeps moving" lag), and the resulting axis-label-width churn was dragging the slider column's rendered size around too (the sliders' own range was always hardcoded `0-4095` — it was the *layout*, not the range, that was visibly shifting).

- [x] `solid_view.py`: lock the hue plot's X and Y range (`setXRange`/`setYRange`, which disables pyqtgraph auto-range for those axes) instead of leaving it to auto-scale
- [x] Add a "Hue scale max" `QSpinBox` (default 1000) above the plot; changing it updates the fixed Y-range via `setYRange`
- [x] Add offscreen tests: fixed range unaffected by large frame values, spinbox updates range, controls visibility matches the hue plot's
- [x] Verified with an offscreen-rendered screenshot

#### M9.2. hue view issues
- Lag issues remain when setting up values, both the setting sliders and the hue sensor are slow. My best guess is that we are saturating the serial port. We are writting and answering too often. 
- The GUI can wait until the slidder stops moving to set a value. The plotter for hue data can take some time to plot. 

**Status: implemented, all 20 `test_offscreen.py` tests pass. Needs a real hardware run to confirm the lag is gone.**

### M10 — GUI: Sub-mode B view + config I/O
Files: `linear_view.py`, `config_io.py` — config screen, progress bar, conditional hue plots, save/load.
Test: offscreen test; round-trip test for JSON save/load.
- [ ] Implement linear_view and config_io
- [ ] Write offscreen and round-trip tests for M10

### M11 — GUI: Sub-mode C view
Files: `grid_view.py` — grid plot, config screen, conditional hue plots, save/load.
Test: offscreen test verifies grid updates on incoming frames.
- [ ] Implement grid_view
- [ ] Write offscreen test for M11

### M12 — GUI: Sub-mode D view
Files: `behavioral_view.py` — scatter plot, press table, rolling median.
Test: offscreen test verifies plot and table update on simulated frames.
- [ ] Implement behavioral_view
- [ ] Write offscreen test for M12
