# Project Summary: behExperiment1

## What this is

A behavioral neuroscience experiment ("knobs test" / metamers project) with two
components: Teensy 4.0 firmware that drives the stimulus and reads inputs, and a
C# WinForms GUI that talks to the Teensy over serial, logs data, and acts as the
experiment runner. The repo is currently at the **starting point / legacy version**
of both — the actual goal (per CLAUDE.md) is to redesign and modernize both pieces
and integrate them, with new work landing under `prototype/`.

## Repo layout

```
CLAUDE.md                          project goals, role, coding standards
startingPoint/
  experiment.md                    spec for the existing experiment
  knobsExperimentTeensy/
    knobsExperimentTeensy.ino      legacy Arduino/Teensy firmware
  GUImetamers/                     legacy C# (.NET 8, WinForms) GUI + build output
.agents/skills/agent-browser/      agent-browser skill (web search) installed
skills-lock.json                   skill lock file
```

No `prototype/` directory or `PLAN.md` exists yet — both are called for in
CLAUDE.md but not yet created.

## The experimental task (startingPoint/experiment.md)

Participant turns two knobs (red, green ADC inputs) to match a fixed amber/yellow
reference, trying to find a "metamer" — a red+green mix that, when flickered
against the fixed yellow at 10 Hz, looks like a smooth solid color rather than a
flicker. Pressing a button logs the trial (TriggerCue, TrialNumber, Amber, red,
green, Press) and starts a new run from a random (red, green) start point.

Key parameters called out in the spec (some not yet reflected in firmware):
- Flicker frequency: 10 Hz, 50% duty cycle red+green vs. 50% duty cycle fixed amber.
- Amber/yellow reference fixed at 2400.
- Desired ranges: minRed 0 (currently 300 in firmware), minGreen 0, maxRed 3000,
  "minGreen 2000" (likely meant maxGreen — current firmware has maxGreen=2400,
  minGreen=300).
- 12-bit PWM and 12-bit ADC.
- 50 ms smoothing window on red/green readings.
- A variability mechanism exists to randomize knob-to-output mapping so participants
  can't "learn" the dial position (currently a random offset applied to raw ADC
  reads, see below).

## Firmware (knobsExperimentTeensy.ino)

- Uses `Bounce2` for the button, `TeensyThreads` for cooperative threads, and
  `IntervalTimer` for the three LED channels (amber/red/green), each toggled at the
  10 Hz half-period via hardware timers.
- Pins: button on 20 (interrupt, FALLING edge), AMBER=0, RED=3, GREEN=1, trigger=13
  (purpose noted as unclear in a comment), analog ins on 19 (red) / 22 (green).
- `analogWriteResolution(12)` / `analogReadResolution(12)`.
- State machine driven by `mode` (0 = idle/off, 1 = "random walk" — stubbed,
  prints "boing", 2 = "variable resistor" knobs experiment — the only mode fully
  implemented, 3–6 = linear walk EEG/behavioral variants for red→green and
  green→red — all stubbed with "boing" placeholders).
- Serial commands recognized in `loop()`: `"1789"` starts mode 2 (the only working
  experiment), `"2789"`–`"7789"` print start messages but don't actually implement
  their modes yet, `"6969"` stops/resets.
- Mode 2 (`var_nob_exp`): samples AIred/AIgreen every 5 ms, averages over 10
  samples (~50 ms window matching the spec's smoothing requirement), adds a
  per-run random offset (`initialOffsetRed` in [0,1500), `initialOffsetGreen` in
  [0,500)) to the raw ADC value before mapping to PWM — this is the existing
  "variability" mechanism that makes the dial-to-output mapping unpredictable per
  run. Output mapped from 0–4095 to `[0,maxRed]` / `[0,maxGreen]`.
- Current limits: `maxRed=3000, minRed=300, maxGreen=2400, minGreen=300` — these are
  hardcoded `#define`/global constants, not serial-configurable yet (CLAUDE.md
  asks for serial-configurable flicker frequency, yellow reference, max
  red/green, minGreen/minRed).
- Button press in mode 2 sends the trial's final dataframe
  (`0@0@amberVal@outputValueRed@outputValueGreen@0`) over serial, deliberately
  repeated 9 times "for redundancy" per a known bug, followed by an `endOfFrame`
  sentinel `"~~~"`, then resets to mode 0.
- Dead/stubbed code: modes 1, 3–6 in both `handleButtonPress()` and
  `amber_red_green()` are placeholders only.
- `sendSerialData()` (continuous 50 Hz serial stream of trigger/trial/amber/red/
  green/press) is gated to only run for `mode == 3 || mode == 4`, i.e. it's wired
  up for the EEG linear-walk modes that aren't implemented yet — currently inert
  in practice since mode 2 is the only working mode and doesn't use this path.

## GUI (startingPoint/GUImetamers)

- .NET 8 WinForms app (net8.0-windows), C#.
- `SerialCommunication.cs`: thin wrapper over `System.IO.Ports.SerialPort`,
  hardcoded baud rate 38400, open/close/send-command only — no read-side logic
  visible in this file.
- `Form1`, `Form3_Constant`, `screen2`, `screen3LinBeh`, `screen3RandBeh`: separate
  WinForms screens, naming suggests one per experiment mode (constant values,
  linear behavioral, random behavioral) mirroring the firmware's `mode` states.
- Build artifacts (`bin/`, `obj/`) are committed to the repo — worth gitignoring
  if untracked-by-design isn't already the case.

## Stated goals (CLAUDE.md) not yet started

- Firmware: faster sessions, less predictable variability routine, serial-configurable
  flicker frequency / yellow reference / max red/green / min red/green, smoothness
  evaluation, integration with a new GUI.
- GUI: re-evaluate implementation language, serial control of firmware, real-time
  plotting, participant/data logging, overall UX pass.
- New work should live under `prototype/` (not yet created).
- `PLAN.md` should track milestones/checklists (not yet created).
- Python, if used, must use `uv` as the package manager exclusively.

## Working-tree state at time of this summary

- `CLAUDE.md` modified (uncommitted) — added the "Coding standards" and "Other"
  sections (no-emoji rule, agent-browser skill, feature-dev guidelines).
- Untracked: `.agents/` (agent-browser skill) and `skills-lock.json`.
- Two commits on `main`: initial commit, then `CLAUDE.md` added.
