# Prototype 2 Development Summary

## M1 — subjectExperiment Firmware (hardware-verified, complete)

**Session:** 2026-06-29  
**Output:** `prototype2/Firmware/subjectExperiment/`  
**Status:** Built, flashed, and hardware-tested on Teensy 4.0. All 19 test scenarios in `testingM1.md` pass.

---

### Hardware context

New PCB supports five independent LED channels simultaneously. Key difference from prototype1: separate Blue and Cyan channels, Amber is always the primary reference LED.

| Signal | Pin | Role |
|--------|-----|------|
| AMBER | 0 | Primary reference (always reference LED) |
| RED | 1 | Primary stimulus (RG pair) |
| BLUE | 2 | Primary stimulus (BG pair) |
| GREEN | 3 | Secondary stimulus (both pairs) |
| CYAN | 4 | Secondary reference (BG pair only) |
| TRIGGER | 6 | EEG trigger output |
| BUTTON | 12 | Participant response button |
| AIred | 20 | Knob 1 — primary channel (Red or Blue) |
| AIgreen | 21 | Knob 2 — secondary channel (Green) |

PWM: 12-bit (0–4095). Baud: 38400.

---

### Files

| File | Description |
|------|-------------|
| `pinDefs.h` | All pin constants and `NUM_STEPS=10`, `NUM_STIMS=100` |
| `globals.h/.cpp` | All shared state and configurable parameters; `applyDefaultsRG/BG()`, `updateHalfPeriod()` |
| `ledControl.h/.cpp` | `flickerISR` (Phase A: stimulus on / Phase B: reference on); `timerSerial` fires `serialFrameOutput` every 100 ms |
| `behavioralExperiment.h/.cpp` | Knob-anchored trial loop, Bounce button debounce, walk-from-press intertrial strategy |
| `gridExperiment.h/.cpp` | Linspaced stimulus arrays, diagonal traversal (4 orders), solid baselines (101+), 1-based stimulus trial count |
| `subjectExperiment.ino` | `setup`/`loop`, `experimentThread` (TeensyThreads), `key=value` and batch config parser |
| `testingM1.md` | 19 test scenarios — all modes, parameters, trial numbering, batch config, anchoring, default-start commands |

---

### Architecture decisions

**Single flicker ISR** — one `IntervalTimer` toggles between Phase A (stimulus LEDs on, reference off) and Phase B (reference LEDs on, stimulus off) each half-period. No dark gap. The ISR reads `currentRed/Blue/Green/Amber/Cyan` globals written by the experiment thread.

**`timerSerial`** — second `IntervalTimer` fires `serialFrameOutput` every 100 ms unconditionally; returns immediately when `!started`. This means the serial frame reflects the true live state at all times.

**`experimentThread`** (TeensyThreads) — idles via `threads.yield()` when not running. On start, dispatches to `runBehavioralExperiment()` or `runGridExperiment()` based on `expMode`.

**Behavioral intertrial strategy** (matches prototype1 `knobs.cpp`):
- First trial anchors to interior margin: `minA + (maxA−minA)/5`, so the start is never at an extreme.
- ADC offset computed in raw ADC space (`rawFromMapped` inverse of `map()`), so the current physical knob position maps to the target value — the knob feels continuous, no snap.
- After button press: record press values, log response, stop flicker, wait `interTrialWait` ms.
- Next trial target = previous press ± `walkJump(range/5)`, clamped to interior margin, then re-anchor.

**Baseline trials (grid)** — solid reference LEDs via direct `analogWrite()` for `trialLength` ms, then off during ITI. No flicker timer running during baselines. Numbered 101+: start baselines are 101, 102, …; end baselines continue from `101 + nBaselinesStart`.

**Grid trial numbering** — stimulus trials are 1-based (1 through `NUM_STIMS`). Baseline trials are 101+. This makes it unambiguous in the serial stream whether a frame is a baseline or stimulus trial.

---

### Serial interface (complete command set)

**Start commands** (set mode, reset counters, start immediately):
```
beh-rg          beh-bg          grid-rg         grid-bg
```

**Default-start commands** (apply defaults for that color pair, then start):
```
beh-rg-default  beh-bg-default  grid-rg-default  grid-bg-default
```

**Utility:**
```
stop            get             defaults-rg     defaults-bg
```

**Config** (accepted any time, including while running):
```
freq=10          refAmber=2400    refCyan=0
maxA=3200        minA=0           maxB=2000        minB=0
nBaselinesStart=2  nBaselinesEnd=2  trialLength=3000  interTrialWait=750
order=1
```

**Batch config** (semicolon-separated, all applied atomically):
```
freq=10;maxA=3200;minA=0;refAmber=2400
```

---

### Serial output frame (all modes, 100 ms interval)

```
&@STIM:{trCnt},Mode:{RG|BG},RED:{v},GREEN:{v},BLUE:{v},AMBER:{v},CYAN:{v},TRIG:{0|1}%!
```

Unused channels output as 0. `trCnt` is 101+ for baselines, 1-based for grid stimulus trials, 1-based increments for behavioral.

**Behavioral response line** (logged on each button press):
```
RESP,Trial:{n},A:{primary_LED_value},B:{green_LED_value}
```

---

### Defaults

| Parameter | RG default | BG default |
|-----------|-----------|-----------|
| freq | 10 Hz | 10 Hz |
| refAmber | 2400 | 500 |
| refCyan | 0 | 1400 |
| maxA (Red/Blue) | 3200 | 2800 |
| minA | 0 | 0 |
| maxB (Green) | 2000 | 2000 |
| minB | 0 | 0 |
| nBaselinesStart | 2 | 2 |
| nBaselinesEnd | 2 | 2 |
| trialLength | 3000 ms | 3000 ms |
| interTrialWait | 750 ms | 750 ms |

---

### Next milestone

**M2 — subjectExperiment GUI** (`prototype2/GUI/subjectExperiment/`)

PySide6 + pyqtgraph + pyserial, uv-managed. Targets native Windows (Teensy COM port). Mirrors the prototype1 combined GUI pattern with:
- Port selection and serial connect/disconnect
- Participant management (create/select, session number)
- Mode selector (Behavioral vs Grid, RG vs BG) with matching color theme
- Configuration panel for all firmware parameters (with send-to-device and read-from-device)
- Real-time plot of LED values + trigger events
- Data logging to CSV
- Start/Stop controls

Reference implementation: `prototype/combined_gui/` (read-only).
