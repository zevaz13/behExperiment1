# M4 Manual Test — Sub-mode B (Linear)

Open the Arduino IDE Serial Monitor at **38400 baud**, line ending **Newline**.
Flash and reset.

---

## 1. Baseline trials (start) OK

```
MODE LINEAR
SET LEDA RED, ref1Led YELLOW, ref1Int 2000, baselineLed1 YELLOW, baselineLed1Val 2000, minA 500, maxA 3000, steps 3, freq 10, trialLength 1000, interTrialWait 300, nBaselinesStart 1, nBaselinesEnd 1
START
```

Immediately after START, `nBaselinesStart` baseline trials run:
- YELLOW LED on solid at 2000 for 1000 ms, then off for 300 ms.
- FRAME@: `trCnt=1001`, `Yellow=2000`, all others 0, `trigFlag=1` during trial, `trigFlag=0` during ITI.

Note: baseline display uses `baselineLed1/2/3` + `baselineLed1/2/3Val`, independent of `ref1/2/3Led` (which only apply to the reference phase of the flicker below).

---

## 2. Stimulus trials — step sweep OK

After baselines, stimulus trials run (trCnt = 1, 2, 3):
- RED flickers at 10 Hz against YELLOW (2000) reference.
- Step values: 500 → 1750 → 3000 (linear from minA to maxA).
- FRAME@: `trCnt=1/2/3`, `LEDA=RED`, `trigFlag=1`.
- Between trials: all LEDs off, `trigFlag=0`.

Verify RED LED brightness increases visibly across the 3 steps.

---

## 3. Baseline trials (end) + natural completion OK

After stimulus trials, `nBaselinesEnd` baselines run (trCnt = 1002), then the experiment ends naturally:
- YELLOW solid again for 1000 ms.
- After completion: no more FRAME@ lines, `GET` returns `mode=NONE`.

---

## 4. STOP mid-experiment OK

```
MODE LINEAR
SET LEDA RED, ref1Led YELLOW, ref1Int 2000, baselineLed1 YELLOW, baselineLed1Val 2000, minA 500, maxA 3000, steps 3, freq 10, trialLength 1000, interTrialWait 300, nBaselinesStart 1, nBaselinesEnd 1
START
```
During a stimulus trial, send:
```
STOP
```
**Expected**: `OK STOP`, LEDs off immediately, no more frames.

---

## 5. Background LEDs during stim phase OK

```
MODE LINEAR
SET LEDA RED, bgStim1Led GREEN, bgStim1Int 1000, ref1Led YELLOW, ref1Int 2000, minA 500, maxA 3000, steps 3, freq 10, trialLength 1000, interTrialWait 300
START
```
- Stim phase runs first (LEDA + background LEDs), then the reference phase (ref1/2/3).
- Stim phase: RED flickers + GREEN on at 1000.
- Ref phase: YELLOW at 2000 only.
- Visually verify both RED and GREEN are active during stim phase.

---

## 6. Hue mode (if sensor connected) OK

```
MODE LINEAR
SET LEDA RED, ref1Led YELLOW, ref1Int 2000, minA 500, maxA 3000, steps 3, freq 10, trialLength 1000, interTrialWait 300, hue 1
START
```
- FRAME@ HUE fields (positions 8–12) should show live sensor values, not -99.
- Values should change between trials as LED illumination changes.

---

## 7. Invalid LED name rejected

```
MODE LINEAR
SET LEDA BLU
```
**Expected**: `ERR unknown param: LEDA BLU` (LEDA is left unchanged, not silently reset to NONE). Confirm with `GET LEDA` that the previous value still holds.

---

## Pass criteria

- Baseline trials: solid `baselineLed1/2/3` LEDs at their configured `Val`, trCnt starts at 1001
- Stimulus trials: LEDA steps linearly from minA to maxA, trCnt from 1; FRAME `LEDA`/`LEDB` fields report the assigned LED name (e.g. `RED`), not intensity
- Stim phase (LEDA + background) runs before the reference phase in each flicker cycle
- Trigger HIGH during each trial, LOW during ITI
- Background LEDs active only during stim phase
- Baseline LEDs are independent of reference LEDs (setting only `ref1Led` does not affect baseline display, and vice versa)
- Invalid LED names are rejected with an error, not silently applied
- STOP halts immediately with LEDs off
- Firmware returns to IDLE after natural completion
