# M16 Manual Test — Randomized knob-LED mapping (Behavioral mode)

Open the Arduino IDE Serial Monitor at **38400 baud**, line ending **Newline**.
Flash and reset. Requires a potentiometer/knob wired to `PIN_KNOB_A` (pin 20) and
`PIN_KNOB_B` (pin 21), and a button on `PIN_BUTTON` (pin 12).

---

## 1. `SET`/`GET knobShuffle`

```
MODE BEHAVIORAL
GET knobShuffle
```
**Expected**: `knobShuffle=0` (default off).

```
SET knobShuffle 1
GET knobShuffle
```
**Expected**: `OK SET knobShuffle`, then `knobShuffle=1`.

```
SET knobShuffle 0
```
**Expected**: `OK SET knobShuffle`; accepted in any state/mode (no mode-guard, unlike `hue`).

---

## 2. Default-off: knob1 always drives LEDA

```
MODE BEHAVIORAL
SET LEDA RED, minA 500, maxA 3000, LEDB GREEN, minB 500, maxB 2000, freq 10, interTrialWait 300
START
```
- Turn knob A: only RED tracks. Turn knob B: only GREEN tracks.
- FRAME@: `Knob1=LEDA`, `Knob2=LEDB` on every frame, across multiple trials (press the button a few times to confirm it never changes).
- `STOP` when done.

---

## 3. Enabled: mapping alternates across trials

```
MODE BEHAVIORAL
SET knobShuffle 1, LEDA RED, minA 500, maxA 3000, LEDB GREEN, minB 500, maxB 2000, freq 10, interTrialWait 300
START
```
- Press the button (or send `PRESS`) repeatedly, at least 20 times.
- After each press, check the frame's `Knob1`/`Knob2` fields for the *new* trial. Roughly half the trials should read `Knob1=LEDA, Knob2=LEDB` and half `Knob1=LEDB, Knob2=LEDA` (not necessarily alternating every time — each trial independently has ~50% odds of flipping).
- When swapped (`Knob1=LEDB`), confirm knob A now drives GREEN and knob B drives RED — the physical behavior actually follows the reported mapping, not just the frame field.
- `STOP` when done.

---

## 4. Press-frame timing: reflects the trial that just ended, not the next one

```
MODE BEHAVIORAL
SET knobShuffle 1, LEDA RED, minA 500, maxA 3000, LEDB GREEN, minB 500, maxB 2000, freq 10, interTrialWait 500
START
```
- Note the current `Knob1`/`Knob2` mapping from a live frame just before pressing.
- Press the button. **Expected**: the press-event frame (`Press=1`) reports the *same* mapping you just saw live (the one active during the trial that ended), not a new one — the swap decision only happens after this frame is sent.
- `STOP` when done.

---

## Pass criteria

- `GET`/`SET knobShuffle` work as documented; default is `0`.
- With `knobShuffle=0`, knob1 always drives LEDA and knob2 always drives LEDB, and `Knob1`/`Knob2` frame fields never change from `LEDA`/`LEDB`.
- With `knobShuffle=1`, the knob->LED mapping visibly alternates across trials (both physically and in the `Knob1`/`Knob2` frame fields), roughly 50/50 over 20+ trials.
- The `Press=1` frame's `Knob1`/`Knob2` reflect the mapping used during the trial that just ended, not the mapping chosen for the next trial.
- Outside Behavioral mode, `Knob1`/`Knob2` report `NONE`/`NONE`.
