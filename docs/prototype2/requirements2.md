# Prototype 2 Requirements

## Context

Prototype 2 targets a revised PCB. The key difference from prototype 1 is that the new board
supports five independent LED channels simultaneously: Red, Green, Yellow (Amber), Blue, and Cyan.
A hue sensor (TCS34725 via I2C) is also wired in for some experimental modalities. All new
deliverables live under `prototype2/`.

Reference code in `startingPoint/prototype2/` is read-only. The finished prototype1 code in
`prototype/` is also read-only and serves as the style reference.

---

## Hardware

### Pin assignments (from `startingPoint/prototype2/Firmware/*/pinDefs.h`)

| Signal    | Pin | Notes                   |
|-----------|-----|-------------------------|
| AMBER     | 0   | DR1 — yellow/reference  |
| RED       | 1   | DR2                     |
| BLUE      | 2   | DR5                     |
| GREEN     | 3   | DR4                     |
| CYAN      | 4   | DR6                     |
| TRIGGER   | 6   | DO1 — EEG trigger line  |
| BUTTON    | 12  | DI1                     |
| AI red    | 20  | knob / ADC 1            |
| AI green  | 21  | knob / ADC 2            |

PWM resolution: 12-bit (0–4095).  
Baud rate: 38400.

### Hue sensor (TCS34725)

Connected via I2C (`Wire`). Provides: R, G, B, clear, color temperature, and lux — all fields
are included in serial frames when the hue sensor is active. No dedicated standalone LUX sensor
is implemented; lux comes exclusively from this chip.

---

## Deliverable 1 — subjectExperiment Firmware

**Output path:** `prototype2/Firmware/subjectExperiment/`

Unified firmware for both the behavioral and grid experiments, adapted for the new hardware.
Modelled after the prototype1 combined firmware. No hue sensor. EEG trigger line required.

### Modes

**Behavioral mode** — similar to prototype1 behavioral experiment. The stimulus flickers at a
given frequency. Each period is split exactly in half: first half = stimulus LEDs on, second
half = reference LEDs on. No dark gap between the two halves — direct toggle.
- Configurable color pair: Red-Green OR Blue-Green.
  - Red-Green: Red (knob 1, AIred=20) and Green (knob 2, AIgreen=21) flicker, reflecting
    the live knob readings. Yellow (Amber) is reference (default refAmber = 2400, refCyan = 0). Defaults: freq=10 Hz, minRed=0, maxRed=3200, minGreen=0, maxGreen=2000
  - Blue-Green: Blue (knob 1, AIred=20) and Green (knob 2, AIgreen=21) flicker, reflecting
    the live knob readings. Cyan and Amber are simultaneously lit as reference
    (default refCyan = 1400, refAmber = 500).   Defaults: freq=10 Hz, minBlue=0, maxBlue=2800, minGreen=0, maxGreen=2000
- Uses one hardware timer that toggles between stimulus state and reference state each
  half-period.
- A second hardware timer fires the serial output frame at a fixed interval.
- Knob mapping is the same for both modes: knob 1 always controls the primary (Red or Blue)
  channel, knob 2 always controls Green.
- Starting position for each trial is randomized around a value to avoid extreme
  starts. Offset range: ±(maxLED − minLED) / 5 applied to each channel independently.
- At button press: `currentRed` and `currentGreen` (or `currentBlue` and `currentGreen`) — the
  already-mapped LED output values, not raw ADC readings — are logged as the trial response.
  After the inter-trial wait, the next trial begins from a new randomized starting position.
- Trial-to-trial variability is the same mechanism as prototype1: a fixed wait followed by
  a small random offset at trial start.

**Grid mode** — similar to prototype1 grid experiment. Same half-period toggle structure as
behavioral mode (no dark gap). Stimulus LEDs on for first half-period, reference LEDs on for
second half-period.
- Configurable color pair: Red-Green OR Blue-Green.
  - Red-Green: Red and Green flicker at the grid trial intensities. Yellow (Amber) is
    reference (default refAmber = 2400, refCyan = 0).
    Defaults: freq=10 Hz, minRed=0, maxRed=3200, minGreen=0, maxGreen=2000,
    trialLength=3000 ms, ISI=750 ms, 2 baselines at start, 2 at end.
  - Blue-Green: Blue and Green flicker at the grid trial intensities. Cyan and Amber are
    simultaneously lit as reference (default refCyan = 1400, refAmber = 500).
    Defaults: freq=10 Hz, minBlue=0, maxBlue=2800, minGreen=0, maxGreen=2000,
    trialLength=3000 ms, ISI=750 ms, 2 baselines at start, 2 at end.
- Fixed 10×10 grid (NUM_STEPS=10, 100 stimulus combinations total).
- One hardware timer toggles between stimulus and reference each half-period.
- A second hardware timer fires the serial output frame at a fixed interval.
- Baselines at start and end (configurable count each, defaults above).
- Trials walk a diagonal grid of (stimulus A × stimulus B) intensity combinations.
  4 traversal orders supported, same definition as prototype1:
  - Order 1: start at (minA, minB), diagonal up-right
  - Order 2: start at (minA, maxB), flip B axis
  - Order 3: start at (maxA, minB), flip A axis
  - Order 4: start at (maxA, maxB), flip both axes
- EEG trigger fires during each trial.

### Serial configurability (no reprogramming required)

All parameters below must be settable via serial commands at runtime:

| Parameter          | Description                                                  |
|--------------------|--------------------------------------------------------------|
| `freq`             | Flickering frequency (Hz)                                    |
| `refAmber`         | Amber (Yellow) reference LED value                           |
| `refCyan`          | Cyan reference LED value (0 for Red-Green mode)              |
| `maxA` / `minA`    | Max/min for primary stimulus LED (Red or Blue)               |
| `maxB` / `minB`    | Max/min for secondary stimulus LED (Green)                   |
| `nBaselinesStart`  | Number of baseline trials at start (grid mode)               |
| `nBaselinesEnd`    | Number of baseline trials at end (grid mode)                 |
| `trialLength`      | Trial duration (ms)                                          |
| `interTrialWait`   | Inter-trial interval (ms)                                    |

### Serial output frame

Single unified frame for all modes (behavioral and grid, RG and BG). All five LED channel
values are always streamed; unused channels are sent as 0.

```
&@STIM:{trCnt},Mode:{M},RED:{red},GREEN:{green},BLUE:{blue},AMBER:{amber},CYAN:{cyan},TRIG:{trigFlag}%!
```

| Field    | RG behavioral / grid        | BG behavioral / grid        |
|----------|-----------------------------|-----------------------------|
| `Mode`   | `RG`                        | `BG`                        |
| `RED`    | currentRed (stimulus)       | 0                           |
| `GREEN`  | currentGreen (stimulus)     | currentGreen (stimulus)     |
| `BLUE`   | 0                           | currentBlue (stimulus)      |
| `AMBER`  | refAmber                    | refAmber                    |
| `CYAN`   | 0                           | refCyan                     |

The GUI identifies the active channels from the `Mode` field rather than inferring from
which values are non-zero.

### Architecture

Modular, same pattern as prototype1 combined firmware:
- `pinDefs.h` — pin constants
- `globals.h / .cpp` — all shared state
- `ledControl.h / .cpp` — timer-driven flicker, LED helpers
- `behavioralExperiment.h / .cpp` — behavioral mode logic
- `gridExperiment.h / .cpp` — grid mode logic
- `subjectExperiment.ino` — setup/loop, serial command dispatch

Uses `IntervalTimer` for flicker and `TeensyThreads` for the experiment thread.

---
## Deliverable 2 — subjectExperiment GUI

**Output path:** `prototype2/GUI/subjectExperiment/`

Python GUI that controls the subjectExperiment Firmware via serial. Style reference:
`prototype/combined_gui/`.

Stack: PySide6 + pyqtgraph + pyserial, managed by `uv`.
Must run on native Windows (COM port enumeration). Linux/WSL development uses
`UV_PROJECT_ENVIRONMENT=.venv-linux`.

### Features

- Port selection and connection management.
- Participant management: create new participant, select existing, record session number.
- Data logging: save experimental data to file (CSV or similar), keyed by participant/session.
- Real-time plot of serial data (LED values, trigger).
- Mode selector: Behavioral vs Grid, Red-Green vs Blue-Green.
- Color scheme adapts to selected modality (Red-Green theme vs Blue-Green theme).
- Serial configuration panel: expose all configurable firmware parameters (freq, ref values,
  baselines, trial timing) and send them to the board.
- Start/Stop experiment controls.

---
