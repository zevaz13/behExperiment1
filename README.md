# behExperiment1

Behavioral neuroscience experiment ("knobs test" / metamers project). A
participant turns red and green knobs to match a fixed amber/yellow
reference, searching for a "metamer" — a red+green mix that, flickered
against the fixed amber, looks like a solid color instead of flickering.

Two components: Teensy 4.0 firmware that drives the LEDs and reads the
knobs, and a GUI that controls the firmware over serial and logs data.

## Repo layout

```
prototype/firmware/knobsBehavioral/   current firmware (Teensy 4.0, Arduino IDE)
startingPoint/                        original firmware and GUI (reference, untouched)
docs/configure.md                     serial commands and experimental procedure
docs/firmware-architecture.md         firmware module design
PLAN.md                               milestones and status
CLAUDE.md                             project goals and coding standards
```

## Firmware

Build with the Arduino IDE + Teensyduino, targeting Teensy 4.0. Requires the
`TeensyThreads` library (`IntervalTimer` is part of the Teensy core).

For serial commands, the experimental procedure, and the data format, see
[docs/configure.md](docs/configure.md). For the internal module design, see
[docs/firmware-architecture.md](docs/firmware-architecture.md).

## Status

See [PLAN.md](PLAN.md) for current milestones. The firmware rewrite
(milestone 1) is hardware-verified; the GUI rewrite and firmware/GUI
integration haven't started.
