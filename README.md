# behExperiment1

Behavioral neuroscience experiment ("knobs test" / metamers project). A
participant turns red and green knobs to match a fixed amber/yellow
reference, searching for a "metamer" — a red+green mix that, flickered
against the fixed amber, looks like a solid color instead of flickering.

Two components: Teensy 4.0 firmware that drives the LEDs and reads the
knobs, and a GUI that controls the firmware over serial and logs data.

## Repo layout

```
prototype/firmware/knobsBehavioral/   behavioral (knobs) firmware (Teensy 4.0)
prototype/firmware/gridEEG/           grid (EEG) firmware (Teensy 4.0)
prototype/gui/                        behavioral GUI (Python, uv-managed)
prototype/grid_gui/                   grid GUI (Python, uv-managed)
startingPoint/                        original firmware and GUI (reference, untouched)
docs/configure.md                     behavioral: serial commands and procedure
docs/firmware-architecture.md         behavioral: firmware module design
docs/gui-usage.md                     behavioral: GUI screens and controls
docs/grid-configure.md                grid: serial commands and procedure
docs/grid-gui-usage.md                grid: GUI screens and controls
PLAN.md                               milestones and status
CLAUDE.md                             project goals and coding standards
```

## Firmware

Build with the Arduino IDE + Teensyduino, targeting Teensy 4.0. Requires the
`TeensyThreads` library (`IntervalTimer` is part of the Teensy core).

For serial commands, the experimental procedure, and the data format, see
[docs/configure.md](docs/configure.md). For the internal module design, see
[docs/firmware-architecture.md](docs/firmware-architecture.md).

## GUI

Python, managed with `uv`. Run on native Windows (the Teensy connects as a
COM port WSL2 can't see without extra setup):

```
cd prototype/gui
uv run main.py
```

The `.venv` here is OS-specific (compiled PySide6/numpy binaries don't work
across OSes). If you also run this from WSL/Linux against the same
checkout, set `UV_PROJECT_ENVIRONMENT=.venv-linux` there so it doesn't
collide with the Windows `.venv` — otherwise `uv` will try to delete and
rebuild the other OS's venv and fail.

For what each screen and control does, see
[docs/gui-usage.md](docs/gui-usage.md).

## Status

See [PLAN.md](PLAN.md) for current milestones. The firmware rewrite
(milestone 1) is hardware-verified. The GUI (milestone 2) has a working
draft (connect, mode/settings, live plot with results table and save) but
hasn't been run against real hardware yet. Firmware/GUI integration hasn't
started.
