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

- [x] `solid_view.py` `_LedColumn`: debounce the outbound `SET` — a 100ms single-shot `QTimer` restarts on every slider/spinbox change, so a fast continuous drag collapses into one `SET` sent ~100ms after motion pauses, instead of one per tick. The slider<->spinbox visual sync stays instant (no serial round trip involved).
- [x] `solid_view.py` `SolidView`: throttle the hue bar plot to a fixed ~300ms redraw cadence — every incoming frame updates a cached `_latest_hue` tuple, but `_hue_bars.setOpts()` is only actually called by a repeating timer, started/stopped alongside the session. Press-row logging is untouched (stays immediate — presses are rare and shouldn't be delayed).
- [x] Added offscreen tests (`QTest.qWait`) proving rapid slider changes collapse to a single `SET` with the final value, and that the hue plot only reflects new data once the throttle timer fires, not on every frame.

**Status: implemented, all 22 `test_offscreen.py` tests pass. Needs a real hardware run to confirm the lag is gone.**

### M10 — GUI: Sub-mode B view + config I/O
Files: `linear_view.py`, `config_io.py` — config screen, progress bar, conditional hue plots, save/load.
Test: offscreen test; round-trip test for JSON save/load.
- [x] `param_form.py` (shared, also used by M11): `ParamForm` builds a `QFormLayout` from an ordered key list — `QSpinBox` for int params, `QComboBox` (LED name/NONE) for LED-assignment params, `QCheckBox` for `hue`. `set_values()`/`values()`/`changed_values()` round-trip against the firmware's string-based GET/SET protocol.
- [x] `config_io.py`: plain `save_config`/`load_config`, JSON, no versioning.
- [x] `linear_view.py`: `LinearConfigPage` (form pre-filled from `GET`, Load/Save-as-JSON buttons, Start prompts for a hue-log file path if hue is checked) and `LinearSessionPage` (progress bar + trial/total label, config summary, and — only if hue is enabled — a growing cumulative R/G/B time-series plot plus a mean-per-step plot, with every frame logged to the chosen `.txt` file while hue is active)
- [x] Trial-completion counting uses a *set of distinct TrialNumbers seen* rather than change-detection: the firmware has no `DONE` sentinel line (unlike the old subjectExperiment protocol), so change-detection would never count the very last trial. A seen-set naturally handles that, and stays robust to repeated/skipped 100ms samples the same way `GUIsubjectExp`'s STIM-change counting was.
- [x] Write offscreen and round-trip tests for M10 (`ParamForm`, `config_io`, navigation, progress counting robustness, hue plots, hue log file)

### M11 — GUI: Sub-mode C view
Files: `grid_view.py` — grid plot, config screen, conditional hue plots, save/load.
Test: offscreen test verifies grid updates on incoming frames.
- [x] `grid_view.py`: `GridConfigPage` (Linear's fields + `LEDB`/`maxB`/`minB`/`order`) and `GridSessionPage` — same progress/hue-plot/logging approach as Linear, plus a visited/current-point scatter plot (x = LEDA, y = LEDB, axes labeled with the assigned LED names) mirroring `GUIsubjectExp`'s `GridSessionPage`: position only updates on `Trigger=1` frames of non-baseline trials, so the ITI's zeroed LEDs never drag the marker to (0,0).
- [x] Write offscreen test for M11 (navigation, total-trials/axis computation, visited-cells-stay-marked-through-ITI, baseline trials excluded from the grid but still counted toward progress)

**Status (M10/M11): implemented, all 37 `test_offscreen.py` tests pass; visually smoke-tested via offscreen screenshots. Needs a real hardware run (Windows + Teensy) — can't test serial I/O from WSL.**
#### M11.1 Issues.
- [x] the user can decide to save or not their data for both linear and grid. The way it is is forcing the data saving, but might not be the case. We will tackle this more formally when we are dealing with saving. For now, just make it so we enable data saving or not.
  `LinearConfigPage`/`GridConfigPage` now have a "Save hue data to file" checkbox (GUI-only, not a firmware param), unchecked by default and only enabled once `hue` is checked. The hue-log `QFileDialog` only appears on Start if both are checked — hue can be enabled purely to watch the live plots without a file being written.
- [x] In the linear experiment mode, I want to see in the GET params line the current values of the LEDs that are set. So it should tell me for the LEDs that are not none, what Phase are they attached to, and what is their value.
  Added `param_form.format_led_assignments(settings)` — lists every non-NONE `bgStim1/2`, `ref1/2/3`, `baselineLed1/2/3` as `"<phase>: <LED>=<value>"`, appended to the Linear session summary line (LEDA is already shown separately as the headline param).
- [x] Same as above but for the grid test.
  Same `format_led_assignments()` call appended to the Grid session summary (LEDA/LEDB already shown separately).

### M12 — GUI: Sub-mode D view
Files: `behavioral_view.py` — scatter plot, press table, rolling median.
Test: offscreen test verifies plot and table update on simulated frames.
- [x] `behavioral_view.py`: `BehavioralConfigPage` (no hue, no config load/save — design spec doesn't ask for either here, unlike Linear/Grid) and `BehavioralSessionPage` — live LEDA/LEDB scatter marker + press marks + rolling-median star marker/label, press table with dynamic `[LEDA name, LEDB name]` headers, mirroring `GUIsubjectExp`'s `BehavioralSessionPage`. No fixed trial count, no progress bar (firmware runs until STOP), no data saving (deferred, per requirements).
- [x] GUI Press button sends `PRESS` directly (same page-owns-in-place-commands pattern as `LinearSessionPage`/`GridSessionPage`'s Stop button) — identical effect to the physical button, per the M6 firmware decision.
- [x] Removed `PlaceholderPage` (dead code now that all 4 modes have real views); `MainWindow`'s Linear/Grid/Behavioral navigation is unified into one `_config_pages` dict + shared `MODE`-then-`GET` flow.
- [x] Write offscreen test for M12 (navigation, live marker, press table/median, Press button, Back/STOP)

**Status (M11.1/M12): implemented, all 46 `test_offscreen.py` tests pass; visually smoke-tested via offscreen screenshots. All 4 GUI sub-mode views (M9-M12) are now built. Needs a real hardware run (Windows + Teensy) — can't test serial I/O from WSL.**

### M12.1 Issues
- The GUI should launch full screen for configuration and experiment screens. With too many parameters is hard to tell where we are.
- When pressing the button or the press. It always records 0,0. These values should be the currentLEDA value and currentLEDB value at pressing.
- This experiment should also support loading and saving experiment configuration json files. call them beh_configparams...

- [x] `main.py`: `window.showMaximized()` instead of `window.show()` — applies to the whole app (including config/experiment screens) from launch.
- [x] **Root cause of the 0,0 press bug (firmware)**: `behavioralMode.cpp`'s press handler calls `allLedsOff()` right after capturing `pressA`/`pressB`, zeroing `ledVal[]` before the *asynchronous* 100ms `FRAME` timer gets a chance to report them — so the `Press=1` frame's LED columns were essentially always already 0 by the time it fired. Fixed by calling `serialFrameOutput()` synchronously right after `pressFlag = true` and before `allLedsOff()`, forcing out the press-event frame with the still-live values deterministically (no more relying on timing luck against the periodic timer). Added a verification section to `tests/test_m6_instructions.md`.
- [x] `behavioral_view.py`: added Load/Save JSON buttons to `BehavioralConfigPage`, mirroring Linear/Grid, using `beh_configparams_<timestamp>.json` naming as requested.
- [x] Added offscreen test for the Behavioral config save/load round-trip.

**Status: implemented, all 47 `test_offscreen.py` tests pass. The 0,0 press fix is in firmware — needs reflash + hardware retest (see M6 test file section 7) to confirm.**
