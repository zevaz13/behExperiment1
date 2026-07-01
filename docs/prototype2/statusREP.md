# Status: Rapid Experimental Prototyping Tool (REP)

Last updated: 2026-07-01

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
| M6 | Firmware Sub-mode D (Behavioral) | **Done, ready to flash** |
| M7 | GUI project setup + serial infrastructure | TODO |
| M8 | GUI main window + mode selector | TODO |
| M9 | GUI Sub-mode A view (Solid) | TODO |
| M10 | GUI Sub-mode B view + config I/O | TODO |
| M11 | GUI Sub-mode C view (Grid) | TODO |
| M12 | GUI Sub-mode D view (Behavioral) | TODO |

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

---

## GUI stack (M7–M12)

- **Output**: `prototype2/GUI/configurableFirmware/`
- **Stack**: PySide6 + pyqtgraph + pyserial, managed by `uv`
- **Must run on Windows** (COM port). When developing from WSL: `UV_PROJECT_ENVIRONMENT=.venv-linux`
- Follows `prototype2/GUIsubjectExp/` structure: `serial_link.py`, `protocol.py`, per-mode view files
- Frame parser: looks for lines starting with `FRAME@`, splits on `@`, 16 tokens
