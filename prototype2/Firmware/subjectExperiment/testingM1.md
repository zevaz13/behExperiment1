# M1 Testing Commands

Open the Arduino Serial Monitor at 38400 baud. Commands are newline-terminated.

## 1. Sanity check — idle state

```
stop
```
Expected: `Stopped.`

Send an unknown command:
```
foo
```
Expected: `ERR unknown: foo`

---

## 2. Behavioral Red-Green (beh-rg)

Start experiment with defaults (10 Hz, Amber ref=2400, Cyan ref=0):
```
beh-rg
```
Expected: `START beh-rg`

Observe:
- Red and Green LEDs flicker at 10 Hz (alternating with Amber reference)
- Serial frames streaming: `&@STIM:{n},Mode:RG,RED:{v},GREEN:{v},BLUE:0,AMBER:2400,CYAN:0,TRIG:1%!`
- Knob 1 (AIred) controls Red brightness; Knob 2 (AIgreen) controls Green brightness
- Press button → `RESP,Trial:{n},A:{red},B:{green}` logged, new trial starts

Stop:
```
stop
```
Expected: `DONE` then `Stopped.`

---

## 3. Behavioral Blue-Green (beh-bg)

```
beh-bg
```
Expected: `START beh-bg`

Observe:
- Blue and Green flicker; Cyan+Amber reference (refCyan=1400, refAmber=500)
- Frames: `Mode:BG,RED:0,GREEN:{v},BLUE:{v},AMBER:500,CYAN:1400`
- Knob 1 controls Blue; Knob 2 controls Green

```
stop
```

---

## 4. Grid Red-Green (grid-rg)

```
grid-rg
```
Expected: `START grid-rg`

Observe:
- 2 baseline trials: Amber solid (2400), frames with `TRIG:1`, `RED:0,GREEN:0,BLUE:0`
- 100 stimulus trials: Red+Green flicker at diagonal grid values, Amber reference
- 2 end baseline trials
- `DONE` printed when complete

---

## 5. Grid Blue-Green (grid-bg)

```
grid-bg
```
Observe:
- Baselines: Cyan+Amber solid (1400+500)
- 100 trials: Blue+Green flicker
- `DONE` after end baselines

---

## 6. Grid with non-default order

```
order=2
grid-rg
```
Expected: `SET order=2`, `START grid-rg`
Verify first trial values differ from order=1 (first trial should be minA + maxB rather than minA + minB).

Repeat with:
```
order=3
grid-rg
order=4
grid-rg
order=1
grid-rg
```

---

## 7. Configuration — frequency

Change to 5 Hz:
```
freq=5
beh-rg
```
Expected: `SET freq=5`, flicker visibly slower.

Change back:
```
stop
freq=10
```

---

## 8. Configuration — reference values

Change Amber reference:
```
refAmber=1200
beh-rg
```
Expected: Amber reference dimmer in Phase B.

```
stop
```

For BG mode, change Cyan:
```
refCyan=800
beh-bg
```

---

## 9. Configuration — stimulus range

Narrow the Red/Blue range:
```
maxA=1500
minA=500
beh-rg
```
Expected: Red channel stays in [500, 1500] regardless of knob position.

---

## 10. Configuration — grid timing

Shorter trials and less baselines:
```
trialLength=1000
interTrialWait=300
nBaselinesStart=1
nBaselinesEnd=1
grid-rg
```
Expected: faster grid run (~101 × 1.3s ≈ 2.2 min instead of ~9 min).

---

## 11. Config rejected while running

```
beh-rg
beh-bg
```
Expected second command: `ERR busy`

```
stop
```

---

## 12. Stop mid-grid

```
grid-rg
stop
```
Expected: experiment halts early, `Stopped.` printed (grid thread exits on `!started`).

---

## 13. Verify serial frame fields

After starting any mode, confirm every frame:
- Starts with `&@STIM:`
- Ends with `%!`
- Contains `Mode:RG` or `Mode:BG`
- Unused LED fields (e.g. BLUE in RG mode) are `0`
- `TRIG:1` during trials, `TRIG:0` during ITI / baselines

---

## 14. Get command — read current parameters

On a fresh board (no prior config commands):
```
get
```
Expected output (RG defaults):
```
freq=10
refAmber=2400
refCyan=0
maxA=3200
minA=0
maxB=2000
minB=0
nBaselinesStart=2
nBaselinesEnd=2
trialLength=3000
interTrialWait=750
order=1
mode=beh-rg
```

Verify get reflects changes after config commands:
```
freq=5
maxA=1500
refCyan=800
get
```
Expected: `freq=5`, `maxA=1500`, `refCyan=800`, all other values unchanged.

Verify get works while experiment is running:
```
beh-rg
get
stop
```
Expected: parameters printed mid-experiment without interrupting it.

Verify mode field updates after mode command:
```
grid-bg
get
stop
```
Expected: `mode=grid-bg`, plus BG defaults (`refAmber=500`, `refCyan=1400`, `maxA=2800`).

---

## 15. Baseline trials — solid reference, no flicker

```
grid-rg
```

Observe during the 2 start baselines:
- Amber LED is solid ON at refAmber (2400) — no flickering
- Red, Green, Blue, Cyan are OFF
- Serial frames: `STIM:101`, then `STIM:102` with `RED:0,GREEN:0,BLUE:0,AMBER:2400,CYAN:0,TRIG:1`
- After each baseline Amber turns OFF, then ITI (750 ms dark), then next baseline or stimulus trial

Then for stimulus trials: Red+Green flicker normally, `STIM:1` through `STIM:100`.

After the 100 grid trials, 2 end baselines appear as `STIM:103` and `STIM:104`.

---

## 16. Trial numbering — baselines 101+, grid 1–100

From the `get` command or by inspecting serial frames:
- Start baselines: `STIM:101`, `STIM:102`
- Grid stimulus trials: `STIM:1` … `STIM:100`
- End baselines: `STIM:103`, `STIM:104`

Change nBaselinesStart to 3 and verify:
```
nBaselinesStart=3
grid-rg
```
Expected start baselines: `STIM:101`, `STIM:102`, `STIM:103`. Grid trials: `STIM:1`–`STIM:100`. End baselines: `STIM:104`, `STIM:105`.

---

## 17. Batch config — multiple parameters in one command

```
freq=5;maxA=1500;minA=300;refAmber=1200
get
```

Expected: four `SET` lines printed, then `get` confirms all four changed simultaneously.

Verify order does not matter:
```
minB=100;maxB=1800;nBaselinesStart=1;nBaselinesEnd=1
```
Expected: four `SET` lines confirming each parameter.

---

## 18. Behavioral — anchored knob start (intertrial strategy)

```
beh-rg
```

Observe across several trials:
- The first trial's LED output starts near `minA + (maxA−minA)/5` regardless of where the knobs are physically (this is the anchor point — the board maps the current physical position to the interior margin).
- After each button press, the next trial begins anchored to a new target that is close to (but not equal to) the previous press value, shifted by ±range/5.
- The starting LED value after ITI never equals the exact previous press value; it is always offset by the walk jump.
- Knob turning feels continuous — no "snap" as the trial starts.

```
stop
```
