# behExperiment1

Behavioral neuroscience experiment platform (metamers / "knobs test"). A participant turns knobs to match a flickering stimulus to a fixed reference, searching for the metamer — a color mix that looks solid instead of flickering.

Two generations of hardware are in this repo. Prototype 1 is complete and was used in production. Prototype 2 targets a revised PCB with five independent LED channels (Red, Green, Amber, Blue, Cyan).

---

## Repo layout

```
prototype2/
  Firmware/subjectExperiment/      subjectExperiment firmware (Teensy 4.0) — COMPLETE, hardware-verified
  GUIsubjectExp/                   subjectExperiment GUI (Python, uv) — COMPLETE, hardware-verified
  Firmware/configurableFirmware/   Rapid Experiment Prototyping Tool firmware — COMPLETE, hardware-verified
  GUI/configurableFirmware/        Rapid Experiment Prototyping Tool GUI (Python, uv) — COMPLETE, hardware-tested

prototype/
  firmware/knobsBehavioral/     behavioral firmware, prototype1 (reference)
  firmware/gridEEG/             grid firmware, prototype1 (reference)
  firmware/experimentStimControl/ combined firmware, prototype1 (reference)
  combined_gui/                 combined GUI, prototype1 (reference)
  gui/                          behavioral GUI, prototype1 (reference)
  grid_gui/                     grid GUI, prototype1 (reference)

startingPoint/                  original hardware reference files (read-only)
docs/prototype1/                prototype1 architecture and usage docs
docs/prototype2/                prototype2 requirements and design docs
summary2.md                     detailed session log for prototype2 work
PLAN.md                         milestones and status
CLAUDE.md                       project goals and coding standards
```

---

## Prototype 2

### Firmware — subjectExperiment

Unified firmware for both behavioral and grid experiments on the new 5-LED PCB.

**Build:** Arduino IDE + Teensyduino, target Teensy 4.0.

**Required libraries:** `TeensyThreads`, `Bounce` (both installable via Arduino Library Manager). `IntervalTimer` is part of the Teensy core.

**Sketch:** `prototype2/Firmware/subjectExperiment/subjectExperiment.ino`

**Modes:**

- `beh-rg` / `beh-bg` — behavioral (knob-driven, button response), Red-Green or Blue-Green pair
- `grid-rg` / `grid-bg` — grid (10×10 automated sweep), Red-Green or Blue-Green pair
- Append `-default` to any start command to restore defaults before starting (e.g. `beh-rg-default`)

**Serial interface** (38400 baud):

```
beh-rg-default          start behavioral, RG pair, defaults restored
beh-bg-default          start behavioral, BG pair, defaults restored
grid-rg-default         start grid, RG pair, defaults restored
grid-bg-default         start grid, BG pair, defaults restored
beh-rg / beh-bg         start behavioral with current params
grid-rg / grid-bg       start grid with current params
stop                    stop experiment
get                     print all current parameter values
defaults-rg             restore RG defaults without starting
defaults-bg             restore BG defaults without starting
freq=10                 set flicker frequency (Hz)
refAmber=2400           set Amber reference value (0–4095)
refCyan=1400            set Cyan reference value (0–4095)
maxA=3200               set max primary channel (Red or Blue)
minA=0                  set min primary channel
maxB=2000               set max Green channel
minB=0                  set min Green channel
nBaselinesStart=2       set baseline trials at experiment start
nBaselinesEnd=2         set baseline trials at experiment end
trialLength=3000        set trial duration (ms, grid mode)
interTrialWait=750      set inter-trial interval (ms)
order=1                 set grid traversal order (1–4)
```

Batch config (semicolon-separated, accepted any time):
```
freq=10;maxA=3200;refAmber=2400
```

**Serial output frame** (100 ms interval while running):
```
&@STIM:{trCnt},Mode:{RG|BG},RED:{v},GREEN:{v},BLUE:{v},AMBER:{v},CYAN:{v},TRIG:{0|1}%!
```

Grid baseline trials are numbered 101+; stimulus trials are 1-based. Behavioral trial count is 1-based per session.

For complete test procedures see `prototype2/Firmware/subjectExperiment/testingM1.md`.

### GUI — subjectExperiment

Complete, hardware-verified. `prototype2/GUIsubjectExp/`

Stack: Python, PySide6 + pyqtgraph + pyserial, managed with `uv`. Must run on native Windows (Teensy enumerates as a COM port that WSL2 cannot see without passthrough).

```
cd prototype2/GUIsubjectExp
uv run python main.py          # Windows
```

If developing/testing from WSL/Linux, set `UV_PROJECT_ENVIRONMENT=.venv-linux` to avoid colliding with the Windows venv. Offscreen tests: `UV_PROJECT_ENVIRONMENT=.venv-linux uv run python test_offscreen.py`.

---

### Firmware + GUI — configurableFirmware (Rapid Experiment Prototyping Tool)

A second-generation deliverable that replaces fixed experiment modes with a firmware you configure at runtime over serial — four sub-modes (Solid, Linear, Grid, Behavioral), any of the 5 LEDs assignable to any role (primary/secondary sweep, background, reference, baseline), optional hue sensor. Built to let a researcher prototype new stimulus designs without reflashing.

**Firmware** — `prototype2/Firmware/configurableFirmware/`. Same build setup as subjectExperiment (Arduino IDE + Teensyduino, Teensy 4.0, `TeensyThreads`/`Bounce`/`IntervalTimer`). Sketch: `configurableFirmware.ino`. Serial protocol: `MODE`, `SET`, `GET`, `START`, `STOP`, `PRESS` (38400 baud) — full command reference, globals, and per-mode behavior in [`docs/prototype2/statusREP.md`](docs/prototype2/statusREP.md). Manual test procedures per milestone: `prototype2/Firmware/configurableFirmware/tests/test_mN_instructions.md`.

**GUI** — `prototype2/GUI/configurableFirmware/`. Same stack as GUIsubjectExp (PySide6 + pyqtgraph + pyserial via `uv`), one view per sub-mode plus JSON config save/load.

```
cd prototype2/GUI/configurableFirmware
uv run python main.py          # Windows
```

If developing/testing from WSL/Linux, set `UV_PROJECT_ENVIRONMENT=.venv-linux`. Offscreen tests: `UV_PROJECT_ENVIRONMENT=.venv-linux uv run python test_offscreen.py`.

---

## Prototype 1 (reference, complete)

Prototype 1 hardware-verified firmware and GUI live in `prototype/`. These are read-only references — do not modify.

```
cd prototype/combined_gui
uv run main.py          # Windows
```

For docs: `docs/prototype1/`

---

## Status

| Deliverable | Status |
|-----------|--------|
| subjectExperiment Firmware | Hardware-verified, complete |
| subjectExperiment GUI | Hardware-verified, complete |
| configurableFirmware (Rapid Experiment Prototyping Tool) — Firmware | Hardware-verified, complete (all 4 sub-modes: Solid, Linear, Grid, Behavioral) |
| configurableFirmware — GUI | Complete, hardware-tested (all 4 sub-mode views + config save/load) |

See [PLAN.md](PLAN.md) for detailed milestone checklists, [docs/prototype2/statusREP.md](docs/prototype2/statusREP.md) for the current architecture/protocol reference, and [summary2.md](summary2.md) for session notes and history.
