# Plan

## Prototype 2 Milestones

### M1 — subjectExperiment Firmware
- [ ] Pin definitions and globals for new 5-LED hardware
- [ ] Modular ledControl (IntervalTimer flicker, TeensyThreads)
- [ ] Behavioral mode: Red-Green and Blue-Green, mid-range staircase start
- [ ] Grid mode: Red-Green and Blue-Green, diagonal sequence, baselines
- [ ] EEG trigger line
- [ ] Runtime serial configurability (freq, refVal, min/max, baselines, timing)
- [ ] Serial output frame

### M2 — subjectExperiment GUI
- [ ] uv project setup, PySide6 + pyqtgraph + pyserial
- [ ] Port selection and serial connection
- [ ] Participant management (create/select, session number)
- [ ] Real-time data plot
- [ ] Mode selector (Behavioral vs Grid, RG vs BG) with color theme
- [ ] Configuration panel (all firmware parameters)
- [ ] Data logging (CSV)
- [ ] Start/Stop controls

### M3 — Configurable Firmware
- [ ] Sub-mode A: Configurable Grid (per-half LED selection, steps)
- [ ] Sub-mode B: Configurable Steps (single or combined LEDs, steps)
- [ ] Sub-mode C: Configurable Solid (all 5 LEDs in real-time, hue output)
- [ ] Sub-mode D: Configurable Behavioral (LED-selectable behavioral)
- [ ] Hue vs EEG output frame selection
- [ ] Full runtime configurability via serial

### M4 — Configurable Firmware GUI
- [ ] All M2 baseline features
- [ ] Sub-mode selector
- [ ] LED assignment controls per phase
- [ ] Save/load configuration (JSON)
- [ ] Re-send config on participant change

---

## Prototype 1 Milestones (completed)

### 1. Firmware cleanup (1.1-1.5 hardware-verified)
