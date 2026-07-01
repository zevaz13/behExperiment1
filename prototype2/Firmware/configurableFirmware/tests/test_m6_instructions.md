# M6 Manual Test — Sub-mode D (Behavioral)

Open the Arduino IDE Serial Monitor at **38400 baud**, line ending **Newline**.
Flash and reset. Requires a potentiometer/knob wired to `PIN_KNOB_A` (pin 20) and
`PIN_KNOB_B` (pin 21), and a button on `PIN_BUTTON` (pin 12).

---

## 1. Knob-driven intensity + physical button

```
MODE BEHAVIORAL
SET LEDA RED, minA 500, maxA 3000, LEDB GREEN, minB 500, maxB 2000, ref1Led YELLOW, ref1Int 2400, freq 10, interTrialWait 300
START
```

- Trial 1 anchors so the knobs' current physical position already reads near the interior margin (`minA + (maxA-minA)/5`), not an extreme — you don't need to move the knobs to a specific spot first.[ok]
- Turn knob A / knob B: RED / GREEN brightness should track the turn in real time (flickering at 10 Hz against YELLOW reference). [ok]
- FRAME@: `trCnt=1`, `LEDA=RED`, `LEDB=GREEN`, `Red`/`Green` columns show live intensity.[ok]
- Press the physical button: trial ends, LEDs off for `interTrialWait` (300 ms), `trCnt` increments to 2, a new randomized target is picked (knob position needed to reach it will have shifted — you'll need to turn the knob again to match).[ok]
- Verify this repeats indefinitely (no fixed trial count, no baselines — `trCnt` never jumps to 1001+). [ok]

---

## 2. Serial PRESS (GUI-simulated) [OK]

With the experiment running (same SET as above), instead of the physical button, send:
```
PRESS
```
**Expected**: `OK PRESS`, same effect as the physical button — trial ends, ITI, `trCnt` increments, new target picked. [OK]

---

## 3. Hue rejected

```
MODE BEHAVIORAL
SET hue 1
```
**Expected**: `ERR unknown param: hue 1` (hue sensor is not supported in Behavioral mode). `GET hue` should still show `0`. [ok]

---

## 4. LED-uniqueness rejected

```
MODE BEHAVIORAL
SET LEDA RED
SET LEDB RED
```
**Expected**: second command returns `ERR unknown param: LEDB RED` (rejected); `GET LEDB` still shows `NONE`. [OK]

---

## 5. Background LEDs during stim phase [OK]

```
MODE BEHAVIORAL
SET LEDA RED, LEDB GREEN, bgStim1Led CYAN, bgStim1Int 1000, ref1Led YELLOW, ref1Int 2000, minA 500, maxA 3000, minB 500, maxB 3000, freq 10, interTrialWait 300
START
```
- Stim phase: RED + GREEN (knob-driven) flicker + CYAN on at 1000.
- Ref phase: YELLOW at 2000 only.

ALSO TESTED [OK]

MODE BEHAVIORAL
SET LEDA RED, LEDB GREEN, bgStim1Led CYAN, bgStim1Int 1000, ref1Led YELLOW, ref1Int 2000, ref2Led BLUE, ref2Int 2000, minA 500, maxA 3000, minB 500, maxB 3000, freq 10, interTrialWait 300
START

---

## 6. STOP mid-trial [OK]

```
MODE BEHAVIORAL
SET LEDA RED, minA 500, maxA 3000, LEDB GREEN, minB 500, maxB 3000, freq 10, interTrialWait 300
START
```
Mid-trial, send `STOP`. **Expected**: `OK STOP`, LEDs off immediately, no more frames.

---

## 7. Press-event frame reports live LED values (M12.1 fix)

```
MODE BEHAVIORAL
SET LEDA RED, minA 500, maxA 3000, LEDB GREEN, minB 500, maxB 2000, freq 10, interTrialWait 500
START
```
- Turn the knobs so RED/GREEN settle at some visibly non-zero, non-equal intensity (e.g. RED ~1800, GREEN ~1200).
- Press the button (or send `PRESS`). **Expected**: the very next `FRAME@` line has `Press=1` and its `Red`/`Green` columns show the intensity at the moment of the press (matching what you saw just before pressing) — **not** `0`/`0`. Subsequent frames during the ITI correctly show `Red`/`Green` at 0 (LEDs off) with `Press=0`.
- This was a bug: `allLedsOff()` used to zero the LED values before the next periodic 100ms frame could report them, so the press was always logged as (0, 0). Fixed by forcing out the press-event frame (`serialFrameOutput()`) immediately, before `allLedsOff()`.

---

## Pass criteria

- LEDA/LEDB intensity tracks the corresponding knob live during a trial
- First trial anchors to the interior margin; subsequent trials walk to a new randomized target after each press, clamped to the interior margins
- Physical button press and serial `PRESS` have identical effect (end trial, log response via `Press=1` on the next frame, ITI, new target)
- `trCnt` increments once per trial, starting at 1, with no fixed upper bound and no 1001+ baseline numbering
- `SET hue 1` is rejected while in Behavioral mode
- LEDA/LEDB cannot be set to the same LED (rejected)
- Trigger HIGH during each trial, LOW during ITI
- STOP halts immediately with LEDs off
- The `Press=1` frame reports the actual LED intensities at the moment of the press, not 0/0
