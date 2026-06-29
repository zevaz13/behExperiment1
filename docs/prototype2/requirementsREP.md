# Requirements for Rapid Experimental Prototyping
## Deliverable 3 — Configurable Firmware (rapid experimental prototyping)

**Output path:** `prototype2/Firmware/configurableFirmware/`

Highly flexible firmware for rapid prototyping of new stimulus designs. Four sub-modes, all
configurable via serial without reprogramming.

### Sub-mode A — Configurable Grid

- Selectable LEDs for each half of the flicker period (multiple LEDs can be active per half).
  Example: first half = Red + Green combined; second half = Yellow + Cyan.
- Configurable number of steps (intensity levels). All selected LEDs share the same step count.
- Values can also be constant (single-step = solid).
- Output mode: Hue sensor frame OR EEG trigger frame (selectable).

### Sub-mode B — Configurable Steps

- Single color or combination that steps through intensity levels.
- Selectable LEDs, number of steps, frequency, min/max values.
- Supports Hue and EEG output frames.

### Sub-mode C — Configurable Solid

- All five LED channels (Amber, Red, Blue, Green, Cyan) controllable to fixed values in real time.
- Serial commands update LED amplitudes on the fly.
- Hue sensor output only (for now).

### Sub-mode D — Configurable Behavioral

- Like the subjectExperiment behavioral mode but all LED selections are configurable.
- Operator specifies which LEDs flicker and which LED(s) serve as reference.
- Supports Hue and EEG output frames.

### Serial configurability

All sub-modes accept runtime configuration commands for:
- LED selection (which channels are active in each phase)
- Number of steps
- Frequency
- Min/max intensity values
- Trial length and inter-trial interval
- Output frame type (hue vs EEG)

### Architecture

Same modular pattern. A new version of the firmware that removes all references to specific
named experiments (no "Blue experiment", no "Grid experiment" by name) — generic primitives only.

---

## Deliverable 4 — Configurable Firmware GUI

**Output path:** `prototype2/GUI/configurableFirmware/`

Same stack and baseline features as the subjectExperiment GUI, plus:

- Save and load experiment configurations (JSON or similar).
  - Saving captures all current parameter settings.
  - Loading restores them and re-sends all configuration commands to the Teensy.
  - On participant change, the GUI re-sends the loaded configuration to re-initialize the board.
- Sub-mode selector (Grid / Steps / Solid / Behavioral).
- LED assignment controls for each phase (which channels are active).
- All other configurable parameters exposed in the UI.

---

## What the starting points reveal

### `BlueTestPrototype_07MAY26`

Earliest clean modular behavioral firmware for prototype2 hardware. Blue-only experiment using
TeensyThreads + IntervalTimer pattern. No hue sensor. Establishes the modular split:
globals, ledControl, experiment logic. Reference for behavioral mode structure.

### `BlueTestHUESENSOR_03JUN26`

Extends the above with TCS34725 hue sensor. Demonstrates how to integrate hue readings
into the serial output frame alongside LED values. Uses a separate `IntervalTimer` for
serial frame output (150 ms period). Shows how multiple experiment types (Blue only,
Blue vs Yellow, Blue vs Red, Blue vs FixedBlue, Blue vs ShiftedBlue) share a single firmware.

Serial frame format established here:
```
&@STIM:{trCnt},HUE_LUX:{lux},BLUE:{val},YELLOW:{val},RED:{val},BLUE2:{val},TRIG:{flag}%!
```

### `GRIDHUESENSOR_10JUN26`

Grid experiment on prototype2 hardware with hue sensor. Two modes: `flash` (flickering) and
`solid`. Demonstrates the diagonal grid sequence generation, baseline trials, and the
startFlicker/stopFlicker pattern. Serial frame timer runs at 110 ms.

### `debugging_Stim_11Dec25`

FSM-based flexible debugging firmware. Supports constant LED mode and blinking mode
(BG = Blue/Cyan/Green, RG = Amber/Red/Green). Closest analog to Deliverable 3. Shows
runtime parameter parsing (`parseAssignments`, `parseBlinkConfig`). Good reference for the
configurable firmware architecture.

### `MET_EEG_knobs_BLgr_RDgr_22_09_25` and `MET_EEG_GridBl_Cy_Gr_22_09_25`

Older monolithic firmwares on the new pin layout. Use different pin assignments than the
modular files (do not use these pin assignments). Include behavioral knob experiment and
grid experiment with EEG triggers. Show the data frame format for the older protocol.
Useful for understanding the history but not to be copied directly.

---

## Reference console loggers (`startingPoint/prototype2/GUI/`)

Two C# (.NET 8) console applications that have been used in practice to record hue sensor
data. They are not GUIs — they run in a terminal, send one command to the Teensy, then
stream and save incoming serial frames until they receive "DONE". Both use `RJCP.IO.Ports`
(SerialPortStream) for serial access.

### `hueLogger` — behavioral experiment logger

Usage: `HueLogger.exe <COM> <expType> <outFileSuffix>`

- Sends `expType` (e.g. `blue`, `blue-yellow`, `blue-red`, `blue-fixed`, `blue-shifted`)
  as the start command.
- Parses behavioral hue frames and writes tab-separated data.
- Output columns: `Stim R G B C Temp HueLux Yellow Red Blue Blue2 Trig`
- Saved files named `{expType}_{suffix}.txt` inside a `data/` directory; auto-increments
  counter to avoid overwriting.

Full frame parsed:
```
&@STIM:{n},R:{r},G:{g},B:{b},C:{c},TEMP:{t},HUE_LUX:{lux},BLUE:{blue},YELLOW:{yellow},RED:{red},BLUE2:{blue2},TRIG:{trig}%!
```

Collected data files in `bin/Debug/net8.0/data/` reflect experiments across multiple
conditions (with filter / no filter / offset variants: `_B`, `_C`, `_NF`, `_O`, `_R`, `_Y`).

### `HueGridLogger` — grid experiment logger

Usage: `HueGridLogger.exe <COM> <expType> <outFileSuffix>`

- Sends `expType` (e.g. `flash`, `solid`) as the start command.
- Parses grid hue frames and writes tab-separated data.
- Output columns: `Stim HueR HueG HueB HueC HueCT HueLux Yellow Red Green Trig`
- Same file-naming convention as hueLogger.

Full frame parsed:
```
&@STIM:{n},HUE_R:{r},HUE_G:{g},HUE_B:{b},HUE_C:{c},HUE_CT:{ct},HUE_LUX:{lux},YELLOW:{yellow},RED:{red},GREEN:{green},TRIG:{trig}%!
```

Collected data covers combinations like `flash_R`, `flash_RG`, `flash_RGY`, `solid_F`, etc.,
reflecting different LED combinations tested during hardware bring-up.

### Implication for new GUIs

The Python GUIs for prototype2 must parse the same frame formats and produce equivalent
tab-separated output. The column layout from these loggers defines the canonical data
schema for both the subjectExperiment and configurable firmware GUIs when hue sensor output
is active.

---

## Constraints and conventions

- Firmware: Teensy 4.0, Arduino IDE, manual flash + test cycle.
- Python: `uv` only for all package management.
- Modular firmware: no experiment-specific names in shared modules.
- Lux is included in hue-mode serial frames (from TCS34725); no standalone lux sensor.
- No over-engineering: match the simplicity level of prototype1 code.
- Documentation in `docs/prototype2/`.
- PLAN.md tracks milestones and checklists.
