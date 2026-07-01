# Plan

## Prototype 2 Rapid Experiment Prototyping Tool

Design spec: `docs/superpowers/specs/2026-07-01-configurable-firmware-design.md`
Requirements: `docs/prototype2/requirementsREP.md`

Output paths:
- Firmware: `prototype2/Firmware/configurableFirmware/`
- GUI: `prototype2/GUI/configurableFirmware/`

### Testing convention
- Firmware: manual test instruction files (`tests/test_mN_instructions.md`) run via Arduino IDE serial monitor
- GUI: offscreen tests + mock serial link

---

## Milestones

### M1 — Firmware: shared infrastructure
Files: `globals.h/cpp`, `pinDefs.h`, `ledControl.h/cpp`, `serialParser.h/cpp`, `dataFrame.h/cpp`, `timerManager.h/cpp`, skeleton `configurableFirmware.ino`
Test: script verifies `MODE` command accepted, `GET` returns defaults, data frame arrives every ~100ms.
- [x] Implement shared modules
- [x] Write serial test script for M1 (`tests/test_m1.py`)

### M2 — Firmware: Sub-mode A (Solid)
Files: `solidMode.h/cpp`, full FSM, real-time LED commands in RUNNING state.
Test: `tests/test_m2_instructions.md` — manual via Arduino IDE serial monitor.
- [x] Implement solidMode
- [x] Write test instructions for M2

### M3 — Firmware: Hue sensor module
Files: `hueSensor.h/cpp`. Returns `-99` fields when absent; returns error on `START` with `hue=true` if not detected.
Test: script verifies error response when sensor absent; sensor-present path tested manually.
- [ ] Implement hueSensor module
- [ ] Write serial test script for M3

### M4 — Firmware: Sub-mode B (Linear)
Files: `linearMode.h/cpp`, baseline support, trigger signal.
Test: script configures short run (2 steps, 2 baselines), asserts trial numbering and frame fields.
- [ ] Implement linearMode
- [ ] Write serial test script for M4

### M5 — Firmware: Sub-mode C (Grid)
Files: `gridMode.h/cpp`, sequence order support.
Test: script runs 2×2 grid, asserts sequence visits all combinations, verifies baseline numbering.
- [ ] Implement gridMode
- [ ] Write serial test script for M5

### M6 — Firmware: Sub-mode D (Behavioral)
Files: `behavioralMode.h/cpp`, ADC knob control, button press frame.
Test: script verifies frame output; button press and ADC behavior verified manually.
- [ ] Implement behavioralMode
- [ ] Write serial test script for M6

### M7 — GUI: project setup + serial infrastructure
Files: `pyproject.toml` (uv), `main.py`, `serial_link.py`, `protocol.py`
Test: unit tests for protocol command builders; mock serial test for frame parsing.
- [ ] Set up uv project
- [ ] Implement serial_link and protocol modules
- [ ] Write unit and mock serial tests

### M8 — GUI: main window + mode selector
Files: `main_window.py` with mode-selector screen and screen switching.
Test: offscreen test verifies mode buttons present and trigger correct screen transitions.
- [ ] Implement main_window
- [ ] Write offscreen test for M8

### M9 — GUI: Sub-mode A view
Files: `solid_view.py` — 5 sliders, color swatches, optional hue panel.
Test: offscreen test verifies sliders emit correct SET commands; hue panel shown/hidden correctly.
- [ ] Implement solid_view
- [ ] Write offscreen test for M9

### M10 — GUI: Sub-mode B view + config I/O
Files: `linear_view.py`, `config_io.py` — config screen, progress bar, conditional hue plots, save/load.
Test: offscreen test; round-trip test for JSON save/load.
- [ ] Implement linear_view and config_io
- [ ] Write offscreen and round-trip tests for M10

### M11 — GUI: Sub-mode C view
Files: `grid_view.py` — grid plot, config screen, conditional hue plots, save/load.
Test: offscreen test verifies grid updates on incoming frames.
- [ ] Implement grid_view
- [ ] Write offscreen test for M11

### M12 — GUI: Sub-mode D view
Files: `behavioral_view.py` — scatter plot, press table, rolling median.
Test: offscreen test verifies plot and table update on simulated frames.
- [ ] Implement behavioral_view
- [ ] Write offscreen test for M12
