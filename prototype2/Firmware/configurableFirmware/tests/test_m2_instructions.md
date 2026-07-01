# M2 Manual Test — Sub-mode A (Solid)

Open the Arduino IDE Serial Monitor at **38400 baud**, line ending **Newline**.
Flash and reset. Run each check in order.

---

## 1. Enter Solid mode and start

Send:
```
MODE SOLID
START
```
**Expected:**
```
OK MODE SOLID
OK START
```
FRAME@ lines begin streaming every ~100 ms.

---

## 2. Set LED values and verify in frame

Send:
```
SET REDLED 2000
```
**Expected:** `OK SET REDLED`
- The Red LED on the PCB lights up.
- In the next FRAME@ line, the Red field (3rd token) reads `2000`.

Send:
```
SET CYANLED 1500, GREENLED 800
```
**Expected:** two `OK SET` lines.
- Cyan and Green LEDs light up.
- Frame fields reflect the new values.

---

## 3. Physical button press

Press the push button on the PCB.
- The next FRAME@ line should have `Press=1` (15th token).
- `TrialNumber` (2nd token) increments by 1.
- Subsequent frames return to `Press=0`.

Repeat two more times and confirm TrialNumber increments each time.

---

## 4. GUI button press (PRESS command)

Send:
```
PRESS
```
**Expected:** `OK PRESS`
- Next frame has `Press=1` and TrialNumber increments.

---

## 5. PRESS rejected outside Solid/Running

Send `STOP`, then try:
```
PRESS
```
**Expected:** `ERR PRESS only valid in SOLID mode while running`

---

## 6. STOP clears LEDs

Send:
```
MODE SOLID
SET REDLED 3000
START
STOP
```
**Expected:** `OK STOP`
- All LEDs on the PCB turn off immediately.
- No more FRAME@ lines.

---

## Pass criteria

- LED brightness matches SET values while running
- Button press (physical and PRESS command) increments TrialNumber and sets Press=1 for one frame
- All LEDs off after STOP
