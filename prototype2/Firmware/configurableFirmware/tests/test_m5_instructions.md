# M5 Manual Test — Sub-mode C (Grid)

Open the Arduino IDE Serial Monitor at **38400 baud**, line ending **Newline**.
Flash and reset.

---

## 1. 2x2 grid, order 1 (default) [OK]

```
MODE GRID
SET LEDA RED, minA 500, maxA 3000, LEDB GREEN, minB 1000, maxB 2000, ref1Led YELLOW, ref1Int 2000, steps 2, freq 10, trialLength 1000, interTrialWait 300, order 1
START
```

Diagonal traversal for a 2x2 grid visits (minA,minB) -> (minA,maxB) -> (maxA,minB) -> (maxA,maxB). Expect trials 1-4:

| trCnt | LEDA (RED) | LEDB (GREEN) |
|---|---|---|
| 1 | 500  | 1000 |
| 2 | 500  | 2000 |
| 3 | 3000 | 1000 |
| 4 | 3000 | 2000 |

- FRAME@: `LEDA=RED`, `LEDB=GREEN` (name fields), `Red`/`Green` columns carry the intensities above.
- Stim phase: RED+GREEN flicker together against YELLOW (2000) reference.
- Trigger HIGH during each trial, LOW during ITI.

---

## 2. Order transform (2, 3, 4) [Ok] - For now works, be its easier to test completely with the GUI.

Repeat with `SET order 2` (flips B axis: minA,maxB start), `order 3` (flips A axis: maxA,minB start), `order 4` (flips both: maxA,maxB start). Verify the first trial's LEDA/LEDB values match the expected starting corner in each case.

---

## 3. Background LEDs during stim phase [OK]

```
MODE GRID
SET LEDA RED, LEDB GREEN, bgStim1Led CYAN, bgStim1Int 1000, ref1Led YELLOW, ref1Int 2000, minA 500, maxA 3000, minB 1000, maxB 2000, steps 2, freq 10, trialLength 1000, interTrialWait 300
START
```
- Stim phase: RED + GREEN flicker + CYAN on at 1000.
- Ref phase: YELLOW at 2000 only.

---

## 4. Baselines (shared with Linear) [OK]

```
MODE GRID
SET LEDA RED, LEDB GREEN, minA 500, maxA 3000, minB 1000, maxB 2000, baselineLed1 YELLOW, baselineLed1Val 2000, steps 2, freq 10, trialLength 1000, interTrialWait 300, nBaselinesStart 1, nBaselinesEnd 1
START
```
- Baseline trials (trCnt 1001, then 1002 after stimulus trials): YELLOW solid at 2000, independent of any `ref1/2/3Led` setting.
- Stimulus trials: trCnt 1-4 as in test 1.

---

## 5. LED-uniqueness rejected [OK]

```
MODE GRID
SET LEDA RED
SET LEDB RED
```
**Expected**: second command returns `ERR unknown param: LEDB RED` (rejected — LEDB cannot equal LEDA in the stim phase) [OK]; `GET LEDB` still shows `NONE`. [OK]

Also verify cross-phase reuse is allowed: `SET ref1Led RED` after `SET LEDA RED` should succeed (`OK SET ref1Led`) [ok] since baseline/ref phases don't conflict with the stim phase.

---

## 6. STOP mid-experiment [ok]

```
MODE GRID
SET LEDA RED, LEDB GREEN, minA 500, maxA 3000, minB 1000, maxB 2000, steps 5, freq 10, trialLength 1000, interTrialWait 300
START
```
During a stimulus trial, send `STOP`. **Expected**: `OK STOP`, LEDs off immediately, no more frames.

---

## 7. Hue mode (if sensor connected) [ok]

```
MODE GRID
SET LEDA RED, LEDB GREEN, minA 500, maxA 3000, minB 1000, maxB 2000, steps 2, freq 10, trialLength 1000, interTrialWait 300, hue 1
START
```
FRAME@ HUE fields should show live sensor values, not -99. [ok]

---

## Pass criteria

- Diagonal boustrophedon traversal visits all `steps x steps` grid points, starting corner matches `order`
- FRAME `LEDA`/`LEDB` fields report LED names; matching color columns carry the swept intensities
- Stim phase (LEDA + LEDB + background) runs before the reference phase in each flicker cycle
- Baseline trials use `baselineLed1/2/3`, independent of `ref1/2/3Led`
- LEDA/LEDB cannot be set to the same LED (rejected); cross-phase reuse (e.g. same LED for baseline and stim) is allowed
- Trigger HIGH during each trial, LOW during ITI
- STOP halts immediately with LEDs off
- Firmware returns to IDLE after natural completion
