# Plan

## Prototype 2 Milestones

### M1 — subjectExperiment Firmware
**Output:** `prototype2/Firmware/subjectExperiment/`
#### Other 
- [x] Walk jump increased to fixed range/3 magnitude (random sign). Previous: uniform random in ±range/5. Now: exactly ±range/3 each trial — guaranteed 33% move, more challenging.
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
**Output:** `prototype2/GUIsubjectExp/`
**Spec:** `docs/prototype2/prototype2-subjectExperiment-gui-requirements.md`

Controls the subjectExperiment firmware. Follows the same flow as `prototype/combined_gui` but with a revised serial protocol, two color modes (RG/BG), and updated data model. UI background is black throughout; accent colors change with color mode.

#### M2.1 — Project scaffold
- [ ] `uv` project in `prototype2/GUIsubjectExp/` with deps: `pyside6`, `pyqtgraph`, `pyserial`
- [ ] `main.py` entry point
- [ ] `serial_link.py` — QThread serial reader, `line_received(str)` signal, 38400 baud
- [ ] `protocol.py` — `parse_get_response`, `parse_stream_frame`, `parse_resp`, `build_batch_command`
- [ ] `participants.py` — 3-CSV scheme (`participants_master.csv`, `participants_behavioral.csv`, `participants_grid.csv`), `next_session_number`, `record_session`, `list_participants`

#### M2.2 — Pages
- [ ] `ConnectPage` — auto-detect PJRC vendor ID `0x16C0`, manual fallback dropdown, identity check via `get`/`mode=` response
- [ ] `ParticipantPage` — folder picker (QSettings-persisted), existing/new participant toggle, group combo (HC, PD, MD, Protan, Deutan, other)
- [ ] `ExperimentSelectPage` — four radios: `beh-rg`, `beh-bg`, `grid-rg`, `grid-bg`; no default preselected; color scheme updates on selection change
- [ ] `ModeConfig` — Default (no param changes) / Advanced (spin box form for all 12 params); sends batch command then start command; waits for `START ...` confirmation
- [ ] `BehavioralSessionPage` — scatter plot (primary vs green, black bg, mode palette); live position marker from stream frame uses reference color (yellow or cyan); press markers + median from `RESP` events; press table; auto-append session file on each press. axes use primary color in x axis, and secondary color in y axis.
- [ ] `GridSessionPage` — 10×10 dot grid (unvisited gray, visited reference color, current amber/cyan. Axes use primary color x axis, secondary in y axis); progress bar; TRIG indicator; completes on `DONE`

#### M2.3 — Color theming
- [ ] `set_color_mode(mode)` on MainWindow propagates palette to all pages
- [ ] RG: primary `#f70404`, secondary `#b1ff01`, reference `#fabd04`. use these color for corresponding av
- [ ] BG: primary `#0493ff`, secondary `#b1ff01`, reference `#50fefe`
- [ ] App-wide black background; accents (borders, plot colors, button highlights) from palette

#### M2.4 — Data model
- [ ] `participants_behavioral.csv`: `sub_id, group, session, file, datetime, mode, freq, refAmber, refCyan, maxA, minA, maxB, minB, trialLength, interTrialWait`
- [ ] `participants_grid.csv`: same minus `file`, plus `nBaselinesStart, nBaselinesEnd, order`
- [ ] `participants_master.csv`: `sub_id, group, experiment, session, datetime`
- [ ] Session data file `{sub_id}_R{n}.txt`: streaming append per `RESP` event, columns `Trial Primary Green`

#### M2.5 — Verification
- [ ] Offscreen pass (`QT_QPA_PLATFORM=offscreen`): all 4 mode paths, Default + Advanced, Back re-entry, all 3 CSVs, press accumulation, `DONE` completion
- [ ] Hardware pass on native Windows (COM port)

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
