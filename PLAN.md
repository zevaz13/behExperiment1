# Plan

## Prototype 2 Milestones

### M1 — subjectExperiment Firmware
**Output:** `prototype2/Firmware/subjectExperiment/`
#### Issues (fixed)
- [x] Baselines are solid LEDs: no flicker during baseline. Amber (RG) or Amber+Cyan (BG) set solid for trialLength, then turned off. Baselines numbered 101+ (start baselines 101,102; end baselines continue from 103,104).
- [x] Trial counts for the experiment part start at 1 (grid stimulus trials 1–100).
- [x] Multiple parameters settable at once via semicolon-separated commands: `freq=10;maxA=3200;minA=0`.
- [x] Behavioral intertrial strategy: knob anchoring (ADC-space offset so physical knob maps to target), walk from previous press position by ±range/5, first trial at interior margin.
- [x] Add new commands beh-rg-default, beh-bg-default, grid-rg-default, and grid-bg-default that should start the experiment with the default parameters. 
#### File scaffold
- [x] `pinDefs.h` — AMBER=0, RED=1, BLUE=2, GREEN=3, CYAN=4, TRIGGER=6, BUTTON=12, AI_RED=20, AI_GREEN=21; 12-bit PWM; baud 38400
- [x] `globals.h/.cpp` — all shared state: mode (RG/BG), colorPair, freq, refAmber, refCyan, minA, maxA, minB, maxB, nBaselinesStart, nBaselinesEnd, trialLength, interTrialWait, currentRed/Green/Blue/Amber/Cyan, trialCount, trigFlag
- [x] `ledControl.h/.cpp` — IntervalTimer flicker (half-period toggle: stimulus on, then reference on, no dark gap); second IntervalTimer for serial frame output; startFlicker/stopFlicker helpers; setAllLEDs helper
- [x] `behavioralExperiment.h/.cpp` — behavioral mode logic (TeensyThreads), knob anchoring, trial walk
- [x] `gridExperiment.h/.cpp` — grid mode logic (TeensyThreads), solid baselines, correct trial counts
- [x] `subjectExperiment.ino` — setup/loop, serial command dispatch, batch config support

#### Behavioral mode
- [x] Knob anchoring: ADC offset so current physical knob position maps to target value at trial start
- [x] Walk: each trial target = previous press ± walkJump(range/5), clamped to interior margin
- [x] First trial starts at interior margin (minA + range/5), not at an extreme

#### Grid mode
- [x] Red-Green pair: same pin/ref defaults as behavioral RG; trialLength=3000 ms, ISI=750 ms, nBaselinesStart=2, nBaselinesEnd=2
- [x] Blue-Green pair: same pin/ref defaults as behavioral BG; same timing defaults
- [x] Fixed 10×10 grid (NUM_STEPS=10, 100 stimulus combinations)
- [x] Diagonal traversal, 4 orders: (minA,minB)↗, (minA,maxB) B-flipped, (maxA,minB) A-flipped, (maxA,maxB) both flipped
- [x] Baseline trials at start (nBaselinesStart) and end (nBaselinesEnd) — solid reference, no flicker
- [x] EEG trigger fires on each trial

#### Serial configurability (no reprogramming)
- [x] Commands to set: `freq`, `refAmber`, `refCyan`, `maxA`, `minA`, `maxB`, `minB`, `nBaselinesStart`, `nBaselinesEnd`, `trialLength`, `interTrialWait`
- [x] Batch: semicolon-separated key=value pairs in a single line
- [x] Mode/pair selection command (RG vs BG, behavioral vs grid)

#### Serial output frame
- [x] Single unified frame for all modes:
  `&@STIM:{trCnt},Mode:{M},RED:{red},GREEN:{green},BLUE:{blue},AMBER:{amber},CYAN:{cyan},TRIG:{trigFlag}%!`
- [x] Unused channels sent as 0; Mode field = `RG` or `BG`

#### Testing commands
- [x] testingM1.md — 18 test scenarios covering all 4 modes, every config parameter, order variants, solid baselines, trial numbering, batch config, and behavioral anchoring

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
