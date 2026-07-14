# Status: Rapid Experimental Prototyping Tool (REP)

Last updated: 2026-07-14

## What this is

Deliverables 3 and 4 of prototype2. A new configurable firmware and matching GUI that allow rapid prototyping of stimulus experiments without reflashing. Four sub-modes (Solid, Linear, Grid, Behavioral), all configured at runtime via serial.

Key documents:
- Requirements: `docs/prototype2/requirementsREP.md`
- Design spec: `docs/superpowers/specs/2026-07-01-configurable-firmware-design.md`
- Milestones: `PLAN.md`

---

## Architecture decisions (locked in)

- **Firmware approach**: Fresh code following `prototype2/Firmware/subjectExperiment` patterns. Same module structure, TeensyThreads, 38400 baud.
- **State machine**: `IDLE → CONFIGURED → RUNNING → IDLE`. `MODE X` enters CONFIGURED. `START` enters RUNNING. `STOP` always returns to IDLE and clears the active mode.
- **Serial protocol**: `MODE X`, `SET param value`, `GET [param]`, `START`, `STOP`. Multi-set via comma-separated pairs: `SET REDLED 300, GREENLED 200`.
- **Data frame** (every 100ms via hardware timer, only when RUNNING):
  `FRAME@TrialNumber@Red@Yellow@Green@Blue@Cyan@HUE_R@HUE_G@HUE_B@HUE_CT@HUE_L@LEDA@LEDB@Press@Trigger`
  Unused numeric fields sent as `-99`. `FRAME` is the line identifier (replaced the draft `TriggerCue` field). `LEDA`/`LEDB` are the *name* of the assigned LED (e.g. `RED`, or `NONE` if unset) — intensity is already in the matching Red/Yellow/Green/Blue/Cyan column.
- **LED naming**: `YELLOW` throughout (same as AMBER, same pin 0). No `AMBER` in new code.
- **LED assignment**: `LedId` enum (`LED_RED=0, LED_YELLOW, LED_GREEN, LED_BLUE, LED_CYAN, LED_NONE`). All LED state in `ledVal[5]` array indexed by `LedId`.
- **Hue sensor**: Optional TCS34725 via I2C (`Adafruit_TCS34725` library). `initHueSensor()` called on START if `hue=1`; returns error if not found. `readHue()` called from `loop()` when `hueEnabled`.
- **Testing**: Manual instructions in `tests/test_mN_instructions.md`, run via Arduino IDE serial monitor. No Python serial scripts (COM port not accessible from WSL).
- **No auto-commits**: User commits manually.
- **LED-uniqueness validation**: `serialParser.cpp::applyParam()` rejects a LED-role SET (`LEDA`/`LEDB`/`bgStim1Led`/`bgStim2Led`, `ref1/2/3Led`, `baselineLed1/2/3`) if it would duplicate a non-`NONE` LED already assigned to another role in the same phase group (stim / ref / baseline). Cross-phase reuse of the same LED is allowed. Shared code, so this applies to Linear and Grid alike.
- **Baseline logic is shared**: `baselineRunner.h/cpp` holds `runBaselines()`, used identically by `linearMode.cpp` and `gridMode.cpp`. Behavioral mode (M6) has no baselines per requirements, so it doesn't call it.
- **Behavioral PRESS**: physical button (`Bounce` on `PIN_BUTTON`) and the serial `PRESS` command have identical effect in Behavioral mode. Since `handleSerial()` (main thread) and `runBehavioral()` (experiment thread, via TeensyThreads) run on different threads, `PRESS` can't call the trial-advance logic directly — it sets `guiPressRequest`, which `runBehavioral()`'s polling loop consumes exactly like a button edge.
- **No hue in Behavioral**: `SET hue 1` is rejected (`applyParam()` returns false) while `MODE_BEHAVIORAL` is active — an explicit requirement, unlike other mode-irrelevant params which are silently accepted and unused.

---

## Firmware file map

`prototype2/Firmware/configurableFirmware/`

| File | Purpose | Status |
|------|---------|--------|
| `configurableFirmware.ino` | Entry point, setup(), loop(), experiment thread | Done (M1–M3) |
| `pinDefs.h` | Pin constants for all 5 LEDs, trigger, button, knobs | Done (M1) |
| `globals.h/cpp` | State machine, all params, ledVal[], timers, helpers | Done (M1) |
| `ledControl.h/cpp` | ledPinConfig(), setLed(), allLedsOff() | Done (M1) |
| `serialParser.h/cpp` | MODE/SET/GET/START/STOP/PRESS command handling | Done (M1–M3) |
| `dataFrame.h/cpp` | serialFrameOutput() ISR, 100ms stream | Done (M1) |
| `timerManager.h/cpp` | startFlicker(), stopFlicker(), startStream() | Done (M1) |
| `hueSensor.h/cpp` | TCS34725 init and readHue() | Done (M3) |
| `solidMode.h/cpp` | LED hold + button press loop | Done (M2) |
| `linearMode.h/cpp` | Linear flickering experiment | Done (M4) |
| `gridMode.h/cpp` | Grid flickering experiment | Done (M5) |
| `baselineRunner.h/cpp` | Shared solid baseline display (Linear + Grid) | Done (M5) |
| `behavioralMode.h/cpp` | ADC knob behavioral experiment | Done (M6) |

---

## Globals reference (key params)

| Variable | Type | Notes |
|----------|------|-------|
| `fwState` | `FwState` | IDLE / CONFIGURED / RUNNING |
| `activeMode` | `Mode` | NONE / SOLID / LINEAR / GRID / BEHAVIORAL |
| `freq` | int | Flicker frequency in Hz, default 10 |
| `trialLength` | uint | Trial duration ms, default 3000 |
| `interTrialWait` | uint | ITI ms, default 750 |
| `steps` | int | Steps per axis [2,50], default 10 |
| `gridOrder` | int | Sequence order [0,4], default 1 |
| `nBaselinesStart/End` | int | Baseline trial count, default 0 |
| `ledA / ledB` | `LedId` | Primary/secondary flickering LED |
| `maxA/minA, maxB/minB` | int | Intensity range [0,4095] |
| `bgStim1/2Led, Int` | LedId/int | Background LEDs during stim phase |
| `ref1/2/3Led, Int` | LedId/int | Reference phase LEDs (flicker cycle only) |
| `baselineLed1/2/3, Val` | LedId/int | Solid LEDs shown during baseline trials (independent of ref1/2/3) |
| `hueEnabled` | bool | Enables hue sensor reading |
| `ledVal[5]` | volatile int[] | Current output per LED (indexed by LedId) |
| `trCnt` | volatile int | Trial counter (1+ stim, 1001+ baseline) |
| `trigFlag` | volatile int | Hardware trigger pin state |
| `pressFlag` | volatile bool | Set on button/PRESS, cleared after next frame |
| `guiPressRequest` | volatile bool | Serial `PRESS` in Behavioral mode; consumed by `runBehavioral()` |
| `halfPeriod` | volatile ulong | µs, derived from freq by updateHalfPeriod() |

---

## SET commands reference

| Command | Example | Constraint |
|---------|---------|-----------|
| `SET freq N` | `SET freq 20` | [1, 500] |
| `SET trialLength N` | `SET trialLength 2000` | ms |
| `SET interTrialWait N` | `SET interTrialWait 500` | ms |
| `SET steps N` | `SET steps 5` | [2, 50] |
| `SET order N` | `SET order 2` | [0, 4] |
| `SET nBaselinesStart N` | `SET nBaselinesStart 2` | |
| `SET nBaselinesEnd N` | `SET nBaselinesEnd 2` | |
| `SET maxA/minA N` | `SET maxA 3200` | [0, 4095] |
| `SET maxB/minB N` | `SET maxB 2000` | [0, 4095] |
| `SET LEDA X` | `SET LEDA RED` | RED/YELLOW/GREEN/BLUE/CYAN/NONE |
| `SET LEDB X` | `SET LEDB GREEN` | same |
| `SET bgStim1Led X` | `SET bgStim1Led CYAN` | same |
| `SET bgStim1Int N` | `SET bgStim1Int 1000` | [0, 4095] |
| `SET bgStim2Led X` | — | same |
| `SET bgStim2Int N` | — | [0, 4095] |
| `SET ref1/2/3Led X` | `SET ref1Led YELLOW` | same |
| `SET ref1/2/3Int N` | `SET ref1Int 2400` | [0, 4095] |
| `SET baselineLed1/2/3 X` | `SET baselineLed1 YELLOW` | same; used for baseline trials only |
| `SET baselineLed1/2/3Val N` | `SET baselineLed1Val 2000` | [0, 4095] |
| `SET hue 0/1` | `SET hue 1` | enables hue sensor |
| `SET REDLED N` | `SET REDLED 2000` | Solid mode only, live while running |
| `SET YELLOWLED N` | — | same |
| `SET GREENLED N` | — | same |
| `SET BLUELED N` | — | same |
| `SET CYANLED N` | — | same |
| Multi-set | `SET REDLED 300, CYANLED 800` | comma-space separated |

Special commands: `PRESS` (Solid or Behavioral + RUNNING only — simulates button press from GUI).

---

## Milestone status

| Milestone | Description | Status |
|-----------|-------------|--------|
| M1 | Firmware shared infrastructure | **Done, hardware verified** |
| M2 | Firmware Sub-mode A (Solid) | **Done, hardware verified** |
| M3 | Firmware Hue sensor module | **Done, hardware verified** |
| M4 | Firmware Sub-mode B (Linear) | **Done, hardware verified** |
| M5 | Firmware Sub-mode C (Grid) | **Done, hardware verified** |
| M6 | Firmware Sub-mode D (Behavioral) | **Done, hardware verified** |
| M7 | GUI project setup + serial infrastructure | **Done** |
| M8 | GUI main window + mode selector | **Done** |
| M9 | GUI Sub-mode A view (Solid) | **Done, hardware verified** |
| M10 | GUI Sub-mode B view + config I/O | **Done, needs hardware run (Windows)** |
| M11 | GUI Sub-mode C view (Grid) | **Done, needs hardware run (Windows)** |
| M12 | GUI Sub-mode D view (Behavioral) | **Done, needs hardware run (Windows)** |

---

## What M4 (Linear) needs to implement

From requirements:
- Flicker: LEDA alternates with reference LEDs at `freq`. stim phase = LEDA + bgStim1 + bgStim2; ref phase = ref1 + ref2 + ref3.
- Steps: LEDA sweeps from `minA` to `maxA` in `steps` linear increments. One trial per step value.
- Baselines: `nBaselinesStart` + `nBaselinesEnd` solid trials using `baselineLed1/2/3` (independent of ref1/2/3); trCnt starts at 1001.
- Stimulus trials: trCnt starts at 1 (after baselines).
- Trigger: HIGH at start of each stimulus period, LOW at end.
- Hue: if `hueEnabled`, HUE fields populated in frame; otherwise -99.
- flickerISR is defined inside linearMode.cpp and passed to `startFlicker()`.

Key difference from subjectExperiment: LED assignments are fully configurable via LedId globals (ledA, bgStim1Led, ref1Led, etc.) rather than hardcoded color pairs.

---

## What M5 (Grid) implements

Same as Linear but with two flickering LEDs (LEDA + LEDB), forming a `steps x steps` grid. Uses the same diagonal boustrophedon traversal as `subjectExperiment/gridExperiment.cpp`, with the `gridOrder` transform (order 2/4 flip the B axis, order 3/4 flip the A axis; order 0 and 1 are both the identity — no distinct meaning defined for 0). `gridFlickerISR` drives both LEDA and LEDB simultaneously in the stim phase, against ref1/2/3 in the reference phase. Sequence is generated in one pass into `seqA[]`/`seqB[]` (max 50x50=2500 entries) rather than precomputing a separate coordinate array. Baselines reuse `baselineRunner::runBaselines()`.

---

## What M6 (Behavioral) implements

Same two-phase flicker structure as Grid (stim = LEDA + LEDB + bgStim1 + bgStim2, ref = ref1/2/3), but LEDA/LEDB intensity is driven live by `PIN_KNOB_A`/`PIN_KNOB_B` ADC reads instead of a precomputed step sequence. Anchor-offset knob strategy (`rawFromMapped`/`wrapAdc`/`walkJump`) mirrors `subjectExperiment/behavioralExperiment.cpp`: each trial anchors the knobs' current physical position to a target value, so the participant doesn't need to physically return the knob to an origin between trials. A button press — physical (`Bounce` on `PIN_BUTTON`) or serial `PRESS` (via `guiPressRequest`) — ends the trial, logs the response (`Press=1` on the next FRAME), waits `interTrialWait`, then walks to a new randomized target clamped to the interior margins. No hue support (`SET hue 1` rejected in this mode). No baselines, no fixed trial count or `trialLength` — runs until `STOP`.

**M12.1 fix**: the press handler used to call `allLedsOff()` immediately after capturing the pressed values, zeroing `ledVal[]` before the *asynchronous* 100ms `FRAME` timer could report them — so `Press=1` frames essentially always showed 0/0 instead of the actual pressed intensities. Fixed by calling `serialFrameOutput()` synchronously right after `pressFlag = true` and before `allLedsOff()`, forcing out the press-event frame deterministically instead of relying on the periodic timer's timing.

---

## GUI file map

`prototype2/GUI/configurableFirmware/`

| File | Purpose | Status |
|------|---------|--------|
| `pyproject.toml` | uv project, deps: pyside6, pyqtgraph, pyserial | Done (M7) |
| `main.py` | Entry point | Done (M7) |
| `serial_link.py` | `SerialLink` (QThread), Teensy port auto-detect — unchanged from `GUIsubjectExp`, transport is protocol-agnostic | Done (M7) |
| `protocol.py` | `parse_frame`, `parse_get_response`, `build_mode_command`, `build_set_command` for the `MODE`/`SET`/`GET`/`START`/`STOP` protocol | Done (M7) |
| `main_window.py` | `ConnectPage`, `ModeSelectPage`, `MainWindow` navigation | Done (M8, extended M10-M12) |
| `solid_view.py` | Sub-mode A (Solid) view | Done (M9) |
| `param_form.py` | Shared config form widget (Linear/Grid/Behavioral) + `PhaseDiagram`/`SavingSection` | Done (M10, extended M11.1/M12, redesigned M14) |
| `config_io.py` | JSON save/load for experiment configs | Done (M10) |
| `figure_export.py` | `save_plot_widgets()` — exports a session page's pyqtgraph plots to PNG | Done (M13.2) |
| `run_export.py` | `build_metadata()`, `save_run()` (combined metadata+data JSON), `save_metadata()` (sidecar) | Done (M15) |
| `linear_view.py` | Sub-mode B (Linear) config + session views | Done (M10, extended M11.1/M13/M14/M15) |
| `grid_view.py` | Sub-mode C (Grid) config + session views | Done (M11, extended M11.1/M13/M14/M15) |
| `behavioral_view.py` | Sub-mode D (Behavioral) config + session views | Done (M12, extended M13.2/M14/M15) |
| `test_offscreen.py` | Offscreen test suite (protocol, navigation, all views), `QT_QPA_PLATFORM=offscreen` | Done (M7-M13), extended each milestone (M14 layout/visual work verified via one-off scripts instead, see M14 notes) |

## What M8/M9 implement

- **ModeSelectPage**: one button per mode (`SOLID`/`LINEAR`/`GRID`/`BEHAVIORAL`) plus a "Enable hue sensor" checkbox next to the Solid button. Solid has no config screen of its own (per design spec — it "goes directly to the experiment screen"), so its hue choice has to be made before entering it; Linear/Grid each expose their own hue toggle on their config screens instead, since they do have a config step. Behavioral doesn't support hue at all.
- **Solid auto-start**: choosing Solid sends `MODE SOLID`, then `SET hue 1` if the checkbox was checked, then `START` — all before the view is shown, so the sliders are live immediately. The `SolidView`'s Back button sends `STOP` and returns to `ModeSelectPage`.
- **SolidView**: 5 vertical sliders (Red/Yellow/Green/Blue/Cyan, in that order) each paired with a synced `QSpinBox` and a color swatch; moving either sends `SET <COLOR>LED <value>`. Incoming `FRAME@` lines update the displayed slider/spinbox values without re-emitting `SET` (signals blocked during the frame-driven update, so there's no feedback loop). A hue bar plot (pyqtgraph `BarGraphItem`, R/G/B) is shown only when hue was enabled at mode-select time, and press rows (`Press=1` frames) accumulate in memory (`_press_log`) only while hue is active — matches requirements ("used for saving data later"); no visible table or file output yet.
- **Testing**: `UV_PROJECT_ENVIRONMENT=.venv-linux uv run python test_offscreen.py` from `prototype2/GUI/configurableFirmware/`. Can't test real serial I/O from WSL (no COM port passthrough) — verified via `FakeSerialLink` plus offscreen-rendered screenshots (`QT_QPA_PLATFORM=offscreen`, `QWidget.grab().save(...)`).

## What M10/M11 (+ M11.1) implement

- **`param_form.py`** (shared by Linear/Grid/Behavioral): `ParamForm(keys)` builds a `QFormLayout` from `PARAM_SPEC` — `QSpinBox` for int params, `QComboBox` (`NONE`/`RED`/`YELLOW`/`GREEN`/`BLUE`/`CYAN`) for LED-assignment params, `QCheckBox` for `hue`. `set_values()` populates from a GET-response-style string dict; `values()` reads back natively typed; `changed_values(baseline)` diffs against a baseline for a minimal `SET` batch. `format_led_assignments(settings)` (M11.1) summarizes every non-NONE `bgStim1/2`/`ref1/2/3`/`baselineLed1/2/3` as `"<phase>: <LED>=<value>"`, appended to each session page's summary line (LEDA/LEDB are shown separately as the headline params). `LED_FRAME_KEY` maps an LED name to its `FRAME@` column, shared by Grid's and Behavioral's live-position tracking.
- **Navigation**: choosing Linear/Grid/Behavioral sends `MODE X`, then `GET`, buffering lines (same pattern as `ConnectPage`) until the `mode=` line completes the response; the corresponding config page is then shown pre-filled. `MainWindow` looks up the right config page via a `mode -> config page` dict rather than per-mode branches. The config page's Start button computes `changed_values()` against the GET baseline; `start_requested` tells `MainWindow` to send the `SET` batch + `START` and show the session page.
- **Load/Save**: `LinearConfigPage`/`GridConfigPage` have Load/Save buttons using plain `QFileDialog`s (`linearParamConfig_<timestamp>.json` / `gridParamConfig_<timestamp>.json` suggested names); editing the form directly is the "configure" path, Load is the "load experimental setup" path — both work off the same form rather than a hard either/or branch. Behavioral has neither, per the design spec (it doesn't ask for config load/save there, unlike Linear/Grid).
- **Hue data saving is opt-in (M11.1)**: a "Save hue data to file" checkbox (GUI-only, not sent to the firmware) sits below the form, disabled unless `hue` is checked, and defaults unchecked. The hue-log `QFileDialog` (`linearhue_exp_<timestamp>.txt` / `gridhue_exp_<timestamp>.txt`) only appears on Start if both are checked — hue can be enabled purely to watch the live plots without a file being written every session.
- **Progress counting**: tracks a *set of distinct `TrialNumber`s seen* rather than detecting changes between frames. The firmware has no completion sentinel (unlike the old subjectExperiment protocol's `DONE` line), so change-detection would never count the final trial; a seen-set counts it as soon as its first frame arrives, while staying just as robust to repeated/skipped 100ms samples.
- **Hue plots** (shown only if hue enabled): a "cumulative" plot is a growing per-frame R/G/B time series (auto-ranging Y, per your call — different failure mode than the M9.1 bar-chart bug since it's a smoothly growing line, not a live-redrawn bar), and a "mean per step" plot appends one R/G/B point per completed *stimulus* trial (baseline trials excluded) once its `TrialNumber` changes. All frames are logged to the chosen `.txt` file while hue is active and the save checkbox was checked.
- **GridSessionPage** additionally shows a visited/current-point scatter (x = LEDA, y = LEDB, axes labeled with the assigned LED names), updated only on `Trigger=1` frames of non-baseline trials — mirrors `GUIsubjectExp`'s `GridSessionPage` logic so the ITI's zeroed LEDs never drag the marker to (0, 0).

## What M12 implements

- **BehavioralConfigPage**: `ParamForm` with Behavioral's fields (`freq`, `interTrialWait`, `LEDA`/`maxA`/`minA`, `LEDB`/`maxB`/`minB`, `bgStim1/2`, `ref1/2/3` — no `hue`, no `steps`/`order`/baselines/`trialLength`, matching what the firmware actually reads in this mode). Load/Save JSON buttons added in M12.1 (`beh_configparams_<timestamp>.json`), mirroring Linear/Grid.
- **BehavioralSessionPage**: mirrors `GUIsubjectExp`'s `BehavioralSessionPage` — a live LEDA/LEDB position marker updated from every frame (via `LED_FRAME_KEY`), press marks (`Press=1` frames) accumulating a scatter + a rolling-median star marker and label, and a press table with dynamic `[LEDA name, LEDB name]` column headers. No progress bar (the firmware has no fixed trial count in this mode, runs until `STOP`). No data saving yet (explicitly deferred by requirements — "we will save data with the stimulator status at button presses" later).
- **Press button**: sends `PRESS` directly from the session page (same "page owns its own in-place commands" pattern as `LinearSessionPage`/`GridSessionPage`'s Stop button) — identical effect to the physical button, per the M6 firmware decision that made `PRESS` valid in Behavioral mode.
- **M12.2 fix — press table/median still showed 0,0 on hardware even after the M12.1 firmware fix**: the live marker updates from every frame, so it looked correct (it was just reflecting the next trial's knob position by the time you noticed), while the `Press=1` frame's own LED columns were still arriving zeroed on real hardware. Fixed on the GUI side, independent of the exact firmware timing: `BehavioralSessionPage` caches the last *live* (non-press) LEDA/LEDB reading (`_last_live_a`/`_last_live_b`) and falls back to it for the marker/table/median only when the press frame's own values are both exactly 0 (the signature of `allLedsOff()` having already zeroed both LEDs) — a press frame with real, possibly fresher, values is still trusted directly.
- **`PlaceholderPage` removed**: with all 4 modes now having real views, the placeholder was dead code.
- **M12.1**: `main.py` launches with `window.showMaximized()` — with this many parameters on the config screens, a small default window made it hard to see the whole picture.

## What M13 implements

- **M13.1**: per-mode config-file prefix enforcement (`_on_load` rejects a filename not starting with the mode's prefix), a smaller slider debounce (`_SET_DEBOUNCE_MS` 100→50), a solid-hue press-count/table panel, a 2s "Starting in Ns..." countdown before `START` (`main_window.py` `START_DELAY_S`), and an experiment-name prompt folded into the hue-log filename.
- **M13.2**: `figure_export.py`'s `save_plot_widgets(parent, plots, default_name)` — one `QFileDialog` prompt, then each named `PlotWidget` exported via `pyqtgraph.exporters.ImageExporter` (multiple plots get their name inserted before the file extension). A "Save figure..." button wired into every session page, always enabled (not gated to after Stop). Solid-hue's `_press_log` (already capturing the full frame per press since M9) got a "Save press data..." button writing it to a space-separated `FRAME_FIELDS`-header `.txt`, matching the Linear/Grid hue-log format.
- **M13.3**: reverted window compact-sizing back to always-maximized (`_switch_to` just calls `showMaximized()`) — the M13.1/M13.2 compact-window experiment didn't look good in practice. `GridSessionPage` layout reworked: square-ish grid plot left, thin cumulative+mean-per-step stack right, three small per-cell hue heatmaps below (steps×steps, indexed like the visited-cell scatter, filled with each cell's mean-per-step value as `_flush_trial_mean` runs — using `_current`, which still holds the *just-finished* trial's cell at that point since the new trial's grid-position update happens later in the same `_on_line` call). Heatmap colormaps: black→`#DA2C43`/`#ACE1AF`/`#89CFF0` (R/G/B) via `pyqtgraph.ColorMap`. Mean-per-step curves lost their point markers (lines only, less clutter with many points). README got a Screenshots section (`docs/prototype2/screenshots/`), generated via a one-off offscreen script — not part of `test_offscreen.py`.
- **Grid axis/heatmap refinements (same session as M14)**: the grid plot's `setAspectLocked(True)` (added for M13.3's "square" look) was found to conflict with wanting *exact* `[minA,maxA]`×`[minB,maxB]` axis limits — aspect lock forces 1:1 unit-per-pixel scaling, which stretches whichever axis doesn't match the widget's actual pixel proportions. Resolved by dropping the aspect lock entirely (exact limits matter more than the square look) and using `padding=0.05` (not `0`) on `setXRange`/`setYRange` so marker circles at the min/max edge points don't get clipped. The three heatmaps gained a live "Heatmap color max" `QSpinBox` (`_heat_clim`, default matches `_HEATMAP_CLIM`) instead of a fixed `(0, 10000)` — changing it re-applies `levels=` to all three `ImageItem`s immediately.

## What M14 implements

Full redesign of the Linear/Grid/Behavioral config screens — see
`docs/superpowers/specs/2026-07-02-config-screen-redesign-design.md` for the
original design rationale (brainstormed with the user before implementation).

- **Stage-grouped, column layout**: `param_form.py`'s `PARAM_SPEC` (a plain
  dict, unchanged as the source of truth for widget kind/range) gained a
  `ParamMeta` dataclass with `label` (friendly name, not the firmware key),
  `unit`, `stage` (`Timing`/`Stimulus`/`Reference`/`Baseline`/`Hue`), and
  `exclusion_group`. `ParamForm` builds one `QGroupBox` per stage present in
  the mode's key list (Behavioral has no Baseline/Hue boxes), and *within*
  each box every field is a labeled column in a single horizontal row (not a
  vertical list) — e.g. Timing shows Frequency/Duration/ITI/Order side by
  side. `_ROW_ORDER` is a fixed, hand-ordered list of "row specs" tried
  most- to least-specific per field: `("led_range", led_key, lo_key, hi_key)`
  (LEDA/LEDB + their own min-max range, merged into one column) → `("range",
  label, lo_key, hi_key)` (a bare min/max pair without its LED) → `("led_pair",
  led_key)` (an LED + single intensity, for backgrounds/reference/baseline,
  looked up via the pre-existing `_LED_PAIR_BY_LED_KEY`) → the bare key alone.
  Each tier only fires if *all* its keys are present and not already consumed
  by an earlier tier, so a `ParamForm` built with a partial key subset (e.g.
  just `maxA` without `minA`, as some unit tests do) still renders that field
  standalone instead of silently dropping it. The widget registry
  (`self._widgets`, keyed by firmware param name) and the `values()`/
  `set_values()`/`changed_values()` contract are **unchanged** — only how
  widgets are grouped/labeled changed, so `main_window.py` needed zero edits.
- **LED color swatches + exclusion filtering**: every LED `QComboBox` gets a
  small color swatch (`LED_COLORS`, moved here from `solid_view.py` as the
  one source of truth) that updates live. LED widgets in the same
  `exclusion_group` (`stim`: LEDA/LEDB/bgStim1Led/bgStim2Led; `reference`:
  ref1/2/3Led; `baseline`: baselineLed1/2/3) grey out (via
  `QStandardItemModel` item-flag disabling, not removal) whichever LED is
  already picked in a sibling of the same group — "NONE" and a combo's own
  current value are never disabled. This is a GUI convenience only; the
  firmware's own duplicate-LED rejection (`serialParser.cpp`) is unchanged
  and remains the real source of truth.
- **`order` becomes a named dropdown**: "Standard"/"Flip LEDB axis"/"Flip
  LEDA axis"/"Flip both axes", mapped to firmware values `{1,2,3,4}` — `0` is
  dropped from the UI since `gridMode.cpp` confirms it's identical to `1`.
- **`PhaseDiagram`** (new, shared by all 3 modes): a small live "what's on in
  each phase" summary — colored chips for LEDA/LEDB/backgrounds (Stim panel)
  and ref1/2/3 (Reference panel), rebuilt from `ParamForm.values()` on a new
  `values_changed` signal (re-emitted from every child widget's own change
  signal). Two bugs found via visual (screenshot) inspection, not code
  review, and fixed: (1) a chip row with only one chip stretched to fill the
  whole panel because `_fill()` had no trailing `addStretch()`; (2) `_fill()`
  used `deleteLater()` alone to remove old chips, which only *schedules*
  deletion — since `set_values()` fires several `values_changed` refreshes
  back-to-back while populating the form, stale chip widgets stayed visible
  (still parented, just not laid out) until the event loop next ran,
  overlapping the new ones. Fixed by calling `widget.setParent(None)`
  immediately in addition to `deleteLater()`.
- **`SavingSection`** (new, Linear/Grid only): experiment name field, the
  existing "Save hue data to file" checkbox, and a destination path
  display + "Choose file..." button — all decided ahead of time on the
  config screen. `_on_start()` no longer opens any dialog: an unset
  destination silently falls back to the same default filename pattern
  (`<mode>hue_exp_<name>_<timestamp>.txt`) computed at Start. `hue_log_path()`
  keeps its exact old signature/meaning.
- **Verification approach**: per explicit instruction partway through this
  work, `test_offscreen.py` was *not* extended for the column-layout and
  grid-axis follow-up changes, and the full suite was not run repeatedly
  during development (it's slow and has a pre-existing, unrelated
  offscreen/Qt teardown segfault). Instead: `py_compile` on every touched
  file, small targeted standalone scripts exercising the new APIs directly
  (`PARAM_SPEC`/`_ROW_ORDER` coverage, round-trip, exclusion filtering,
  `order` mapping), re-running the handful of *existing* tests that
  referenced now-renamed internals (`_save_hue_checkbox` → `_saving`,
  `_hue_log_path` → `SavingSection`), and offscreen screenshots of all three
  config pages to visually confirm the layout (this is how both `PhaseDiagram`
  bugs above were actually caught).

---

## What M15 implements

Per-mode refinements (see `PLAN.md` M15 for the milestone checklist). All
GUI-only; firmware/protocol unchanged. A–C hardware-tested; D hardware-tested.

- **A. Default-value tweaks**: Solid-hue "Hue scale max" default 1000 -> 5000
  (`solid_view._DEFAULT_HUE_SCALE`); Grid-hue "Heatmap color max" default
  10000 -> 3500 (`grid_view._HEATMAP_CLIM`) since 10000 washed the colors out.
- **B. Saving-section gating**: the Linear/Grid config "Saving" section is now
  disabled until the hue sensor is enabled (`SavingSection.set_hue_enabled()`
  disables the whole section widget, not just the "Save hue data" checkbox).
- **C. Baseline points on the mean-per-step plot** (Linear + Grid hue view):
  the "Hue - mean per step" plot now includes baseline trials, each on its own
  labeled x-slot outside the 1..N step range — start baselines `B1,B2,...` at
  `x = -n_start..-1` (left of step 1), end baselines continuing the numbering
  (`B3,B4,...`) at `x = N+1..N+n_end` (right of step N); custom bottom-axis
  tick labels (`_apply_mean_axis`), trial->x mapping (`_mean_x_for`). Grid uses
  `N = steps*steps`; its per-cell heatmap fill stays stimulus-only. The mean
  point is also now drawn **live** and updated in place as each trial's frames
  arrive (`_update_mean_point`), so the last trial (including an end baseline)
  is plotted without waiting for a next trial or Stop — the old flush-on-trial-
  change never plotted the final trial until Stop.
- **D. Metadata saving + linking**: new shared `run_export.py` —
  `build_metadata(mode, settings, name)` (flat: every config param plus
  provenance `mode`/`experiment_name`/`saved_at`, written last so provenance
  wins over a GET response's own `mode`), `save_run(path, metadata, columns,
  rows)` (single combined JSON `{metadata, columns, data}`), and
  `save_metadata(path, metadata)` (sidecar). Per-mode split, by user
  preference:
  - **Solid + Behavioral** (small runs): one self-contained combined JSON via
    `save_run` — read back with `d = json.load(f); meta = d["metadata"];
    df = pandas.DataFrame(d["data"], columns=d["columns"])`.
  - **Linear + Grid** (long frame streams): the streaming `.txt` data log is
    kept unchanged (crash-safe), plus a sidecar `.json` (same filename stem)
    holding the metadata via `save_metadata`, written when the log opens.
  - **Behavioral press-data save**: a "Save press data..." button on the
    session page writes the combined JSON. The on-screen table stays minimal
    (trial count, LEDA value, LEDB value), but each saved row is the full
    frame (all 5 LED intensities incl. background, hue channels, LEDA/LEDB
    assignment). Because the firmware zeroes all LEDs at press time
    (`allLedsOff()`, the M12.2 timing), the literal `Press=1` frame arrives
    all-zero; the GUI caches the whole last-live (pre-press) frame
    (`_last_live_frame`) and saves that (marked `Press=1`) whenever the press
    frame's LED columns are zeroed, preserving the real intensities. A press
    frame carrying real values is saved as-is.
  - `SavingSection.experiment_name()` added; Linear/Grid config pages expose it
    and `main_window` passes it into `start_session`.

New GUI file: `run_export.py`.

---

## GUI stack (M7–M15)

- **Output**: `prototype2/GUI/configurableFirmware/`
- **Stack**: PySide6 + pyqtgraph + pyserial, managed by `uv`
- **Must run on Windows** (COM port). When developing from WSL: `UV_PROJECT_ENVIRONMENT=.venv-linux`
- Follows `prototype2/GUIsubjectExp/` structure: `serial_link.py`, `protocol.py`, per-mode view files
- Frame parser: looks for lines starting with `FRAME@`, splits the remainder on `@` into 15 fields (`protocol.FRAME_FIELDS`)
