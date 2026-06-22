# Plan

## Milestones

### 1. Firmware cleanup (in progress)
- [x] Split monolithic `knobsExperimentTeensy.ino` into modules under
      `prototype/firmware/knobsBehavioral/`: `pins.h`, `config.h`,
      `flicker.*`, `knobs.*`, `trial.*`, `serial_commands.*`.
- [x] Drop unused experiment modes (random walk, linear EEG/behavioral
      walks) — only the knobs/variable-resistor behavioral experiment is
      kept.
- [x] Drop unused `Bounce2` dependency (configured but never queried in the
      legacy code) and the unused `~~~` end-of-frame sentinel (the GUI's
      parser ignores lines without `@`, so it had no effect).
- [x] Renamed serial protocol to `START`/`STOP` (legacy GUI used
      `1789`/`6969` — GUI will need updating to match, see milestone 3).
- [x] Trial result is now sent once per button press instead of 9x
      (legacy code repeated it as a workaround for an already-fixed bug).
- [X] Build/flash-test on actual Teensy 4.0 + PCB hardware.
      - Code Builds and runs.
      - Issues were detected with the flickering. Both the yellow and red+green Combination are been used at the same time. These must be out of fase. First part of the period for RED+Green (No Yellow), second part for Yellow (No Red+green)
### 1.1 Solve Flickering issues
- [x] `flicker.cpp` now uses a single `IntervalTimer` whose ISR alternates
      between two strictly exclusive phases: RED+GREEN on/AMBER off, then
      AMBER on/RED+GREEN off. Public API (`flickerInit/Start/SetRedGreen/
      Stop`) unchanged, so `trial.cpp`/`knobs.cpp` needed no changes.
- [x] Re-flash and verify on hardware that RED+GREEN and AMBER no longer
      overlap.

### 1.2 Configure 
- [ ] Make flicker frequency, amber/yellow reference, max red/green, and
      min red/green configurable via serial commands (currently constants
      in `config.h`).
- [ ] Decide on and implement an improved (less learnable) variability
      routine — current one keeps the legacy per-trial random ADC offset.

### 2. GUI refactor (not started)
- [ ] Evaluate replacement language/framework for the experiment logger.
- [ ] Update serial protocol usage to match firmware (`START`/`STOP`).
- [ ] Real-time plotting of red/green trial data.
- [ ] Participant/session management and data export.

### 3. Firmware + GUI integration (not started)
- [ ] End-to-end test of new firmware against new/updated GUI.

## Known gaps surfaced during cleanup
- `minRed`/`minGreen` existed as constants in the legacy firmware but were
  never actually applied as a floor in the ADC-to-PWM mapping — the spec
  in `startingPoint/experiment.md` calls for minRed=0, minGreen=0, but the
  current behavior is effectively minRed=minGreen=0 regardless of the
  configured values. Not reintroduced in the cleanup; needs a decision
  when serial-configurability is implemented.
