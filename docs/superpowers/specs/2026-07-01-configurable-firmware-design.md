# Design: Configurable Firmware and GUI (Deliverables 3 & 4)

Date: 2026-07-01

## Overview

New firmware and GUI for rapid experimental prototyping. Four sub-modes (Solid, Linear, Grid, Behavioral), all configurable at runtime via serial without reflashing. Built fresh following the patterns of `prototype2/Firmware/subjectExperiment` and `prototype2/GUIsubjectExp`.

Output paths:
- Firmware: `prototype2/Firmware/configurableFirmware/`
- GUI: `prototype2/GUI/configurableFirmware/`

---

## Approaches Considered

Three approaches were evaluated during brainstorming.

### Approach A — Minimal extension (selected)

Follow the exact pattern of `subjectExperiment`: single `.ino` entry point, shared `globals`, `ledControl`, and `pinDefs` modules, one `.cpp/.h` file per sub-mode, and a central `serialParser`. Two `IntervalTimer`s: one for flickering (frequency-driven), one fixed at 100ms for data frame output.

GUI mirrors `GUIsubjectExp`: one `main_window.py` with a mode-selector panel that shows/hides parameter widgets per mode. Config save/load is a JSON dump of current widget values.

**Why selected:** Proven pattern, fast to build, no new abstractions. The serial parser grows as an if/else chain but stays readable at this scale.

### Approach B — Config-struct-centric

Same module split, but the center of gravity is a per-mode `Config` struct in `globals.h`. The serial parser fills the active struct; mode functions take `const Config&` and are stateless workers. The firmware's `GET` command serializes the struct back to the GUI, making config save/load trivial.

**Trade-off:** Cleaner separation of configuration from execution, but requires fully defining all struct fields upfront before any mode can be coded. Good option if the parameter set grows significantly or if firmware-side config serialization becomes important.

### Approach C — Command-table driven

All serial commands registered in a table (`{name, handler_fn, validator_fn}`). No if/else chain. The firmware responds to every command with ACK/NAK. GUI uses ACK/NAK to confirm state sync before starting.

**Trade-off:** Most robust and extensible. Overkill for a single-researcher tool where the serial link is reliable and the command set is fixed. Revisit if the tool grows into a shared platform.

---

## Firmware Architecture

### Module layout

```
configurableFirmware.ino   — setup(), loop(), mode dispatch
globals.h / globals.cpp    — all state: current mode, all params, LED assignments
pinDefs.h                  — pin constants (5 LEDs, ADCs, trigger, button)
ledControl.h / .cpp        — analogWrite wrappers, 12-bit PWM
serialParser.h / .cpp      — command parsing (MODE, SET, GET, START, STOP)
dataFrame.h / .cpp         — build and print the shared data frame
timerManager.h / .cpp      — two IntervalTimers: flicker + 100ms serial stream
hueSensor.h / .cpp         — TCS34725 I2C driver (optional; returns -99 if absent)
solidMode.h / .cpp
linearMode.h / .cpp
gridMode.h / .cpp
behavioralMode.h / .cpp
```

### State machine

```
IDLE
 │  MODE X
 ▼
CONFIGURED  ←──── SET param value ──┐
 │                GET / GET param   │
 │                MODE X (resets)   ┘
 │  START
 ▼
RUNNING
 │  STOP (or experiment ends naturally)
 ▼
IDLE
```

- `MODE X` accepted in `IDLE` and `CONFIGURED`. Sending a new `MODE` in `CONFIGURED` resets all parameters to defaults for the new mode.
- `SET` and `GET` accepted in `CONFIGURED` only.
- In `RUNNING`, only `STOP` is accepted — except Sub-mode A (Solid), where real-time LED value commands remain valid.
- `STOP` always returns to `IDLE` and clears the active mode.

### Hardware timers

Two `IntervalTimer` instances:
1. **Flicker timer** — period set by configured `freq`. Drives LED switching between stimulus and reference phases for modes B, C, D.
2. **Stream timer** — fixed 100ms. Builds and sends the data frame regardless of mode.

### Hue sensor

TCS34725 via I2C. Optional: if not connected, all HUE fields in the data frame are `-99`. If the user sends `START` with `hue=true` and the sensor is not detected, firmware returns an error and stays in `CONFIGURED`.

Note: "Amber" and "Yellow" are used interchangeably in the lab; the codebase uses "Yellow" throughout.

---

## Serial Protocol

### GUI → Teensy (newline-terminated)

| Command | Example | Notes |
|---|---|---|
| `MODE X` | `MODE LINEAR` | Sets mode, loads defaults, enters CONFIGURED |
| `SET param value` | `SET LEDA RED` | Sets one parameter |
| `SET p1 v1, p2 v2` | `SET REDLED 300, GREENLED 200` | Multi-set (Solid mode) |
| `GET` | `GET` | Returns full current config |
| `GET param` | `GET LEDA` | Returns one value |
| `START` | `START` | Begins experiment, enters RUNNING |
| `STOP` | `STOP` | Halts, returns to IDLE |

### Teensy → GUI (every 100ms, `@`-delimited)

```
TriggerCue@TrialNumber@Red@Yellow@Green@Blue@Cyan@HUE_R@HUE_G@HUE_B@HUE_CT@HUE_L@LEDA@LEDB@Press@Trigger
```

- Fields not relevant to the current mode sent as `-99`
- `LEDA` / `LEDB` carry the *name* of the assigned LED (e.g. `RED`, or `NONE` if unset) — the intensity is already available in the matching Red/Yellow/Green/Blue/Cyan column
- `Press` is `1` on the frame where a button press occurs, else `0`
- `Trigger` reflects the hardware trigger pin state
- `TrialNumber` starts at `1001` for baseline periods, `1` for stimulus trials

---

## GUI Architecture

### File layout

```
main.py              — entry point
main_window.py       — top-level window, mode selector, screen switching
serial_link.py       — serial read/write thread, frame parsing
protocol.py          — command builders (SET, GET, MODE, START, STOP)
config_io.py         — JSON save/load of experiment parameters
solid_view.py        — Sub-mode A UI
linear_view.py       — Sub-mode B UI
grid_view.py         — Sub-mode C UI
behavioral_view.py   — Sub-mode D UI
```

### Flow

Main window opens on a mode-selector screen. Choosing a mode sends `MODE X` to the Teensy and switches to that mode's view. Sub-modes B, C, and D present a config screen (with load/save) before the experiment screen. Sub-mode A goes directly to the experiment screen.

### Sub-mode A — Solid view

- 5 vertical sliders side by side, one per LED, with a color swatch and editable value box
- LED colors: Red `#f70404`, Yellow `#fabd04`, Green `#b1ff01`, Blue `#0493ff`, Cyan `#50fefe`
- Right panel shows hue sensor R/G/B bar plots (only if hue sensor active)
- Button press (physical or GUI) triggers a full data frame with `Press=1`
- No config save/load

### Sub-mode B — Linear view

- Config screen: all Linear parameters, hue toggle, load/save (filename prefix `linearParamConfig_`)
- Experiment screen: progress bar, current/total repetition label, key config summary at bottom
- Hue plots (optional, shown only if hue active): cumulative R/G/B channels on one plot; mean R/G/B per step on a second plot
- Data saved as `linearhue_exp_<timestamp>.txt` when hue is active (all frames logged)
- LED referred to as `LEDA (<selected LED name>)` in labels

### Sub-mode C — Grid view

- Config screen: all Grid parameters, hue toggle, load/save (filename prefix `gridParamConfig_`)
- Experiment screen: progress bar, current/total repetition label, key config summary at bottom
- Grid plot showing visited and current points (x = LEDA, y = LEDB), axes labeled `LEDA (<name>)` / `LEDB (<name>)`
- Hue plots (optional, shown only if hue active): same layout as Linear
- Data saved as `gridhue_exp_<timestamp>.txt` when hue is active

### Sub-mode D — Behavioral view

- Config screen: all Behavioral parameters (no hue)
- Experiment screen: real-time scatter plot of LEDA vs. LEDB intensity, axes labeled with LED names
- Button press appends a row to a table on the right; rolling median shown on screen
- Data save deferred to a later milestone

### Shared UI behavior

- LED assignment dropdowns (LEDA, LEDB, Background slots, Reference slots) remove already-selected LEDs from remaining options within the same phase, preventing duplicate assignment
- Back button on every experiment screen returns to mode selector (sends `STOP` if running)
- Color palette: background black, LED colors as above, `#ff7256` for non-LED UI accents

---

## Constraints

- Teensy 4.0, Arduino IDE, manual flash + test cycle
- 12-bit ADC and PWM resolution
- Python: `uv` only for package management
- No over-engineering: match the simplicity of `subjectExperiment`
- GUI must run on native Windows (COM port access)
- When developing from WSL/Linux: `UV_PROJECT_ENVIRONMENT=.venv-linux`
