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

### 1.2 Configuration and serial printing
- [x] Added `settings.{h,cpp}`: flicker frequency, amber reference, max/min
      red/green are now runtime values (defaults from `config.h`),
      configurable via `SET <name> <value>` (e.g. `SET maxRed 2800`) —
      plain text, one setting per line, chosen so a desktop app can build
      commands with simple string formatting (no JSON parser needed on
      the Teensy).
- [x] Default mode (`MODE DEFAULT`, the boot default): settings are pinned
      to the `config.h` constants; `SET` is rejected. Advanced mode
      (`MODE ADVANCED`): `SET` takes effect immediately, applied live
      (mid-trial changes to max/min red/green take effect on the next
      knob sample; frequency changes take effect on the next trial start).
- [x] Added `telemetry.{h,cpp}`: a second `IntervalTimer` ticks every
      100 ms; while a trial is active it streams the same dataframe format
      used for the final result (Press=0), so a GUI can plot red/green
      live. The one-shot send on button press is unchanged (Press=1) and
      still marks the authoritative trial result in the log.
- [x] Extracted `dataframe.{h,cpp}` (`sendDataFrame`) so the periodic
      stream and the final button-press result share one implementation
      instead of duplicating the `Serial.print` sequence.
- [x] Default `minRed`/`minGreen` changed from the legacy 300/300 to 0/0,
      matching the `startingPoint/experiment.md` spec.
- [x] Documented mode/SET usage and the experimental procedure in
      `docs/configure.md`.

### 1.3 
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
- Fixed as part of 1.2: `minRed`/`minGreen` are now actually applied as the
  floor of the knob-to-PWM mapping (`map(raw, 0, 4095, minX, maxX)` in
  `knobs.cpp`), instead of being unused constants like in the legacy code.
  Defaults are now 0/0, matching `startingPoint/experiment.md`.
- Re-flash and verify on hardware: `SET`/`MODE` commands, the 100 ms
  telemetry stream, and the min/max red-green clamping have not yet been
  tested on real hardware.
