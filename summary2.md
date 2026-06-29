# Prototype 2 Development Summary

## Session: 2026-06-29

### M1 — subjectExperiment Firmware (complete)

**Output:** `prototype2/Firmware/subjectExperiment/`

Created unified firmware for behavioral and grid experiments targeting the new 5-LED PCB (Teensy 4.0). Modelled on the prototype1 combined firmware pattern.

#### Files created

| File | Description |
|---|---|
| `pinDefs.h` | Pin constants (AMBER=0, RED=1, BLUE=2, GREEN=3, CYAN=4, TRIGGER=6, BUTTON=12, AIred=20, AIgreen=21), NUM_STEPS=10 |
| `globals.h/.cpp` | All shared state, configurable parameters, `applyDefaultsRG/BG()`, `updateHalfPeriod()` |
| `ledControl.h/.cpp` | Single `flickerISR` (Phase A: stimulus on / Phase B: reference on), `timerSerial` fires `serialFrameOutput` every 100 ms |
| `behavioralExperiment.h/.cpp` | Knob-driven trial loop, Bounce button debounce, randomized start offset, button-press response logging |
| `gridExperiment.h/.cpp` | Linspaced stimulus arrays, 4-order diagonal traversal, start/end baselines (solid reference), EEG trigger per trial |
| `subjectExperiment.ino` | `setup`/`loop`, `experimentThread` (TeensyThreads), `key=value` serial config parser |
| `testingM1.md` | 13 test scenarios covering all 4 modes, every config parameter, order variants, and edge cases |

#### Architecture decisions

- **Single flicker ISR** — one `IntervalTimer` toggles directly between Phase A (stimulus LEDs) and Phase B (reference LEDs) each half-period. No dark gap between phases. This is cleaner than the two-independent-timer approach in earlier reference firmwares.
- **`timerSerial`** starts in `setup()` and fires `serialFrameOutput` every 100 ms; returns immediately when `!started`.
- **`experimentThread`** (TeensyThreads) idles via `threads.yield()` when not running, then dispatches to `runBehavioralExperiment()` or `runGridExperiment()` based on `expMode`.
- **Config commands** (`key=value`) accepted at any time; mode/start commands (`beh-rg`, `beh-bg`, `grid-rg`, `grid-bg`) apply defaults for the selected pair, then start. User config overrides must be sent after the mode command if defaults need changing.
- **Randomized start** in behavioral mode: ADC mapping offset of ±(max−min)/5 per channel so trials never begin at an extreme value.
- **Diagonal grid traversal**: 4 orders implemented by flipping A and/or B index axes on the base (0,0)→diagonal sequence.

#### Serial interface

Start commands: `beh-rg`, `beh-bg`, `grid-rg`, `grid-bg`
Stop command: `stop`

Config commands (examples):
```
freq=10          refAmber=2400    refCyan=0
maxA=3200        minA=0           maxB=2000        minB=0
nBaselinesStart=2  nBaselinesEnd=2  trialLength=3000  interTrialWait=750
order=1
```

Serial output frame (all modes):
```
&@STIM:{trCnt},Mode:{RG|BG},RED:{v},GREEN:{v},BLUE:{v},AMBER:{v},CYAN:{v},TRIG:{0|1}%!
```

#### Plan update

PLAN.md M1 checklist fully marked complete. M2 (subjectExperiment GUI) is the next milestone.
