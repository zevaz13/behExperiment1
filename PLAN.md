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
### M12.2 Issues behavioral test
- Upon push-button pressing, the marker is placed in the right location. However, the value appended to the table is 0,0. 
- The median cannot be tested as it is always 0,0. It is well placed in the plot.

**Root cause**: the marker's "right location" was misleading — it's updated continuously by *every* frame, so it quickly reflects the next trial's live knob position regardless of what the specific `Press=1` frame carried. The table/median read their value from that same `Press=1` frame's own LED columns, and on real hardware those still arrived zeroed despite the M12.1 firmware fix (the exact remaining race wasn't reproducible from here without hardware access). Fixed on the GUI side instead, since it can be made correct independent of the firmware's exact timing: `behavioral_view.py` now caches the last *live* (non-press) LEDA/LEDB reading, and on a `Press=1` frame only falls back to that cache if the frame's own values are both exactly 0 (the signature of `allLedsOff()` having already zeroed both LEDs) — a press frame carrying real, possibly fresher, values is still trusted directly.

- [x] `behavioral_view.py`: cache `_last_live_a`/`_last_live_b` from every non-press frame; use them for the marker/table/median only when the press frame's own values are both exactly 0.
- [x] Added offscreen tests for both cases: zeroed press frame falls back to the cached value; non-zero press frame is trusted directly (regression guard for the M9-era test).

**Status: implemented, all 49 `test_offscreen.py` tests pass. This fix is GUI-only (no reflash needed) — should resolve the issue immediately once you pull the updated `behavioral_view.py`.**
### M13.1 Refinement and details
- [x] Lets make it so for a given mode, we only can load configuration files for that one. Grid can only load files starting with gridParamConfig, linear only linearParamConfig, and behavioral only beh_configparams.
  Each config page's `_on_load` rejects any filename not starting with its mode's prefix (`linearParamConfig`/`gridParamConfig`/`beh_configparams`), warning via `QMessageBox` instead of loading. Tested by `test_config_load_rejects_wrong_mode_prefix`.
- [x] The window for the mode selection GUI, solid mode, solid-hue mode, linear mode (not configuration. the experiment itself) should be smaller.
  Added `COMPACT_WINDOW_SIZE` in `main_window.py`, applied to ModeSelect/Solid/Linear-session; everything else (config screens, Grid/Behavioral sessions) stays maximized. (Superseded by explicit pixel sizes in M13.2.)
- [x] The delay for the slidders now is too big, it could be a little smaller.
  `solid_view.py` `_SET_DEBOUNCE_MS` reduced from 100 to 50.
- [x] make the solid-hue, do something to show the button presses.
  Added a live press-count label + per-press R/G/B table (`_press_panel`) to `solid_view.py`, shown only while hue is enabled.
- [x] For the linear, grid and behavioral modes, please add a 2 second delay after pressing the start button and the experiment start.
  `main_window.py`: `START_DELAY_S = 2`; `_run_start_countdown` shows "Starting in Ns..." on the session page, then sends `START`.
- [x] When saving data please allow a space for the user to add an experiment name so resulting files would look like for example gridhue_exp_"ExpName"_timestamp.
  `linear_view.py`/`grid_view.py` `_on_start` prompt via `QInputDialog` for an optional experiment name, folded into the default hue-log filename (`linearhue_exp_<name>_<timestamp>.txt` / `gridhue_exp_<name>_<timestamp>.txt`).

**Status: implemented and committed (`ffd72ef`).**

### M13.2 Refinement and details
- Make the default size of experiment mode selection, solid experiment, solid hue, and linear experiment something like 1184x612 px would be great. Linear-hue should be 1800x700 px.
- When data acquisition stops, the figures displayed on the screen can be saved.
- In the solid-hue mode, when the person presses the button, I like what is shown in the column, but in the background keep also track of all the LED values at button press, and all the hue resulting parameters. Add a button to allow the person to save that table.

- [x] `main_window.py`: replaced `COMPACT_WINDOW_SIZE` with `DEFAULT_WINDOW_SIZE` (1184x612 — ModeSelect, Solid(-hue), Linear session without hue) and `LINEAR_HUE_WINDOW_SIZE` (1800x700 — Linear session only when that run's `hue=1`); `_switch_to` now takes an optional explicit size, computed per-run for Linear via `_window_size_for`. Grid/Behavioral are unaffected (stay maximized).
- [x] `figure_export.py` (new, shared): `save_plot_widgets(parent, plots, default_name)` prompts once for a filename and exports each named `PlotWidget` to PNG via `pyqtgraph.exporters.ImageExporter` (multiple plots get their name inserted before the extension). Wired into a "Save figure..." button on every session page: `solid_view` (hue plot, only when hue is on), `linear_view` (cumulative + mean hue plots, only when hue is on), `grid_view` (grid plot always, plus hue plots when on), `behavioral_view` (LEDA/LEDB scatter plot, always). The button is always enabled, not gated to after Stop, so it can be used anytime including once the run has stopped.
- [x] `solid_view.py`: the per-press `_press_log` already captured the full frame dict (all 5 LED intensities + HUE_R/G/B/CT/L, from the original M9 design) — this just needed exposing. Added a "Save press data..." button that writes it to `solidhue_presses_<timestamp>.txt`, the same space-separated `FRAME_FIELDS`-header format as the Linear/Grid hue logs.
- [x] Added offscreen tests: exact window sizes for the four light pages/states, Save-figure plot-set contents per mode (and hue-dependent visibility for Linear), Save-press-data file contents.

**Status: hardware-tested and tried by the user — confirmed working.**

### M13.3
- Make all the windows full screen. I dont like the way it looks now.
- In the grid hue experiment screen, lets do the following:
      - drop the markers in the mean per step plot, they make it hard to see the lines with many markers.
      - Change the layout of this screen. I want the grid with visited pixels to be on the left (and square). Next to it, on the right top the cummulative hue values, and under it the mean per step values. these 2 should be thiner, spanning the same space as the height of the matrix of visited pixels.
      - Under these, I would like you to include something similar to place 3 matrix plots (imshow in matplot lib that shows the value of each of the 3 hue channels in different plots across the experiment)
        use the folloving values for the color maps of these matrix plots : Red #DA2C43, green green #ACE1AF, blue #89CFF0. These could be small plots, the color limits should be 10000. 
- update projects readme. You may add figures if you can make them. To show the GUI.

- [x] `main_window.py`: removed the whole compact-window mechanism (`DEFAULT_WINDOW_SIZE`/`LINEAR_HUE_WINDOW_SIZE`/`_compact_pages`/`_window_size_for`) added in M13.1/M13.2 — `_switch_to` now just always calls `showMaximized()`. Every page is maximized again.
- [x] `grid_view.py` `GridSessionPage`: dropped `symbol="o"` from the mean-per-step curves (lines only). Reworked the layout: `_grid_plot` (aspect-locked, so it renders square) on the left; `_hue_col_widget` (cumulative + mean stacked, thin) on the right, same total height as the grid; `_heat_widget` (three small per-cell heatmaps, one per hue channel) below both, spanning the full width. `_hue_col_widget`/`_heat_widget` stay hidden together when hue is off, same as the old combined `_hue_widget`.
- [x] Per clarification: the three heatmaps are `steps x steps` grids indexed the same way as the visited-cell scatter (`(LEDA index, LEDB index)`), not a time-strip — each cell starts at 0 and is filled with that cell's mean-per-step hue value as its trial's mean is flushed (`_flush_trial_mean`, using `_current` — still holds the just-finished trial's cell at that point, since the grid-position update for the new trial's frame happens later in the same `_on_line` call). Colormaps are black-to-`#DA2C43`/`#ACE1AF`/`#89CFF0` (R/G/B) via `pyqtgraph.ColorMap`, fixed levels `(0, 10000)` regardless of data range.
- [x] `_on_save_figure` (Grid) now also exports the three heatmaps when hue is enabled.
- [x] `README.md`: added a Screenshots section (ModeSelect, Solid+hue, Grid+hue showing the new layout, Linear+hue) generated via a one-off offscreen script (not part of `test_offscreen.py`); images in `docs/prototype2/screenshots/`.
- [x] `test_offscreen.py`: replaced the now-obsolete compact-window-size tests with `test_all_pages_are_maximized`; no other test changes (per instruction to minimize use of this suite — a separate one-off script and `py_compile` were used to verify the new code instead of running the full suite).

**Status: implemented this session, not yet hardware-tested.**

### M14 — GUI: config screen redesign (stages, labels, visuals)

Design spec: `docs/superpowers/specs/2026-07-02-config-screen-redesign-design.md`
(brainstormed and approved before implementation).

Files: `param_form.py` (most of the work), `solid_view.py`, `linear_view.py`,
`grid_view.py`, `behavioral_view.py`, `docs/prototype2/statusREP.md`.

Reorganizes the Linear/Grid/Behavioral config screens from one flat list of
firmware-named fields into stage-grouped sections (Timing/Stimulus/Reference/
Baseline/Hue/Saving) with friendly labels, LED color swatches, a live stim-vs-
reference phase diagram, cross-field LED exclusion filtering, and a proper
"Saving" section replacing the Start-time popup dialogs. Firmware/protocol
unchanged — GUI-only. `main_window.py` needed zero changes (the `ParamForm`
round-trip contract — `values()`/`set_values()`/`changed_values()` — kept the
same signature throughout).

- [x] `param_form.py`: added `ParamMeta`, enriched `PARAM_SPEC` with `label`/
      `unit`/`stage`/`exclusion_group` for every key; moved `LED_COLORS` here
      from `solid_view.py` (single source of truth).
- [x] `param_form.py`: added `RANGE_PAIRS` (`minA`/`maxA`, `minB`/`maxB`) and
      reused the existing `_LED_PHASE_FIELDS` table for LED+intensity pairing;
      `ParamForm.__init__` builds one `QGroupBox` per stage (only for stages
      the mode's key list actually has fields in). `values()`/`set_values()`/
      `changed_values()` signatures and behavior unchanged — widgets stay
      registered per-key exactly as before.
- [x] `param_form.py`: color-swatch `QLabel` next to every LED dropdown; a
      `values_changed` signal (re-emitted from every child widget's change
      signal); cross-dropdown exclusion-group filtering (`stim`: LEDA/LEDB/
      bgStim1Led/bgStim2Led, `reference`: ref1/2/3Led, `baseline`:
      baselineLed1/2/3) via `QStandardItemModel` item-flag disabling (never
      removes items, never disables "NONE" or a combo's own current value) —
      runs once after `set_values()` and again on every `values_changed`.
- [x] `param_form.py`: `order` is now a 4-item named dropdown ("Standard",
      "Flip LEDB axis", "Flip LEDA axis", "Flip both axes") mapped to firmware
      values `{1,2,3,4}` — `0` dropped from the UI (confirmed identical to `1`
      in `gridMode.cpp`).
- [x] `param_form.py`: new `PhaseDiagram` widget — two labeled panels ("Stim"/
      "Reference") with colored role chips built from current form values,
      refreshed on `values_changed`. No Baseline diagram (its own group box
      with swatches is self-explanatory without one).
- [x] `param_form.py`: new `SavingSection` widget (Linear/Grid only) —
      experiment name field, existing "Save hue data to file" checkbox,
      destination path display + "Choose file..." button. No dialogs pop up
      at Start anymore; an unset destination silently falls back to the
      default `<mode>hue_exp_<name>_<timestamp>.txt` path.
- [x] `solid_view.py`: imports `LED_COLORS` from `param_form` instead of a
      local copy.
- [x] `linear_view.py` / `grid_view.py`: `PhaseDiagram` + `SavingSection` added
      to `LinearConfigPage`/`GridConfigPage`'s layout; the `QInputDialog`/
      `QFileDialog`-at-Start flow removed from `_on_start()` (`Start` button
      now connects straight to `start_requested`), destination read from
      `SavingSection` instead (`hue_log_path()` kept its exact signature).
- [x] `behavioral_view.py`: `PhaseDiagram` added to `BehavioralConfigPage` (no
      `SavingSection` — this mode doesn't save experiment data yet); the
      stage-grouped `ParamForm` renders correctly with Behavioral's smaller
      key set (no Baseline/Hue/Saving boxes).
- [x] Fixed a handful of *existing* `test_offscreen.py` tests that referenced
      now-renamed internals (`_save_hue_checkbox` → `_saving._save_checkbox`,
      direct `_hue_log_path` assignment → `_saving._explicit_path` +
      checkbox). No new tests added for the rest of M14 — verified instead via
      `py_compile`, small targeted standalone scripts (`PARAM_SPEC`/
      `_ROW_ORDER` coverage, round-trip, exclusion filtering, `order`
      mapping), and offscreen screenshots of all three config pages, per an
      explicit instruction partway through this work to stop extending/
      running the slow, crash-prone full `test_offscreen.py` suite.
- [x] `docs/prototype2/statusREP.md`: added "What M13 implements"/"What M14
      implements" sections describing all of the above and the M13.1-M13.3
      work that preceded it.

**Status: implemented, committed (`df06880`), hardware/manual-tested by the user — confirmed working.**

#### M14 follow-up: exact grid axis limits + column-based layout

Two more rounds of refinement requested after trying M14 on hardware:

1. **Grid plot axis limits.** First ask: force the visited-grid plot's x/y
   range to exactly `[minA,maxA]`/`[minB,maxB]` (was padded 5%). Turned out
   `_grid_plot.setAspectLocked(True)` (added in M13.3 for the "square" look)
   was fighting this — aspect lock forces 1:1 unit-per-pixel scaling, which
   stretches whichever axis doesn't match the widget's actual pixel
   proportions, so the "exact" range wasn't holding under a non-square
   widget. Fixed by dropping the aspect lock entirely (confirmed with the
   user: exact limits matter more than the forced-square look). Second ask,
   right after: re-add a *small* padding (`0.05`, not `0`) so marker circles
   at the min/max edge points don't get visually clipped once visited — done,
   and since the aspect lock is gone this now applies exactly and
   independently on each axis regardless of widget shape.
2. **Heatmap color-limit control.** Added a live "Heatmap color max"
   `QSpinBox` next to the three per-cell hue heatmaps in `GridSessionPage`
   (`_heat_clim`, defaults to the old fixed `(0, 10000)`); changing it
   re-applies `levels=` to all three `ImageItem`s immediately.
3. **Column-based stage layout.** Each stage `QGroupBox` was a vertical
   `QFormLayout` (one field per row); changed to a horizontal `QHBoxLayout`
   of labeled columns instead, applied to *every* stage (confirmed with the
   user, not just Timing/Stimulus as in the original examples) — e.g. Timing
   now shows Frequency/Duration/ITI/Order side by side, Reference shows
   Ref1/Ref2/Ref3 side by side. LEDA/LEDB's dropdown and their own min-max
   range now merge into one column (`_ROW_ORDER`'s new `led_range` tier)
   instead of two stacked rows; "Number of steps" stays on its own column
   (per the user's preference — it's shared by LEDA/LEDB, not specific to
   either).
   - Caught (via screenshots, not code review) and fixed two `PhaseDiagram`
     bugs surfaced by this refactor: a lone chip in a row stretched to fill
     the whole panel (`_fill()` had no trailing `addStretch()`); and swapping
     chips via `deleteLater()` alone left stale ones visibly overlapping the
     new ones, since `set_values()` fires several `values_changed` refreshes
     back-to-back during config load and `deleteLater()` only *schedules*
     removal — fixed by also calling `widget.setParent(None)` immediately.
   - No tests added for this follow-up round, per explicit instruction.

**Status: implemented, committed (`df06880`), tested by the user — confirmed working, "everything looks great."**'

### M15 - refining details per mode

Grouped by kind of change rather than by mode, so the mechanical tweaks can
land quickly and the open design question can be handled separately.

#### A. Default-value tweaks (trivial)
- [x] Solid-hue: default "Hue scale max" 1000 -> 5000 (`solid_view.py`
      `_DEFAULT_HUE_SCALE`).
- [x] Grid-hue: default "Heatmap color max" 10000 -> 3500 (`grid_view.py`
      `_HEATMAP_CLIM`) — 10000 made the colors too dim.

#### B. Saving-section gating (small UI)
- [x] Linear config: disable the Saving section until "Enable hue sensor" is
      checked.
- [x] Grid config: same — Saving section only enabled when hue is enabled.
      Done in `param_form.py` `SavingSection`: `set_hue_enabled()` now disables
      the whole section widget (not just the checkbox); starts disabled.

#### C. Mean-per-step plot: include baselines (logic fix)
- [x] Linear session (hue): the "Hue - mean per step" plot now adds a point for
      each baseline trial. Baselines get their own labeled x-slots outside the
      1..N step range: start baselines B1,B2,... at x=-n_start..-1 (left of step
      1), end baselines continue the numbering (B3,B4,...) at x=N+1..N+n_end
      (right of step N). Custom bottom-axis tick labels via `_apply_mean_axis()`;
      trial->x mapping via `_mean_x_for()`.
- [x] Grid session (hue): same fix as Linear (N = steps*steps). Heatmap cell
      fill stays stimulus-only (baselines map to no grid cell).

- [ ] The last baseline is not completely logged in the plots (linear and grid), until the user presses stop. It should be done automatically.

#### D. Metadata saving + linking (open design — brainstorm first)
- [ ] Find a way to save experiment metadata (the same info as the save-config
      JSON: frequency, trial length, LED assignments, etc.) and link it to the
      resulting saved experiment data so a saved dataset can be traced back to
      the config that produced it. Approach undecided — spans Linear/Grid/
      Behavioral.
- [ ] Behavioral: add an option to save the press table when it is non-empty.
      The saved table should include the whole frame received by the GUI (with
      LED configuration), and reuse whatever metadata-saving approach is
      decided above.