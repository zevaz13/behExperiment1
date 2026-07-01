# M1 Manual Test — Shared Firmware Infrastructure

Open the Arduino IDE Serial Monitor at **38400 baud**, line ending set to **Newline**.
Flash `configurableFirmware.ino` and press reset. Run each check in order.

---

## 1. Boot

**Expected on reset:**
```
Ready.
```

---

## 2. MODE command

Send:
```
MODE SOLID
```
**Expected:**
```
OK MODE SOLID
```

Send an invalid mode:
```
MODE BOGUS
```
**Expected:**
```
ERR unknown mode: BOGUS
```

---

## 3. GET — full config

Send:
```
GET
```
**Expected:** a block of `key=value` lines ending with `mode=SOLID`. Verify defaults:
- `freq=10`
- `trialLength=3000`
- `interTrialWait=750`
- `steps=10`
- `LEDA=NONE`
- `hue=0`
- `mode=SOLID`

---

## 4. GET — single param

Send:
```
GET freq
```
**Expected:**
```
freq=10
```

---

## 5. SET — numeric param

Send:
```
SET freq 20
```
**Expected:**
```
OK SET freq
```

Then verify:
```
GET freq
```
**Expected:**
```
freq=20
```

Restore:
```
SET freq 10
```

---

## 6. SET — LED assignment

Send:
```
SET LEDA RED
```
**Expected:**
```
OK SET LEDA
```

Verify:
```
GET LEDA
```
**Expected:**
```
LEDA=RED
```

Reset it:
```
SET LEDA NONE
```

---

## 7. SET rejected in IDLE

Send:
```
STOP
```
**Expected:**
```
OK STOP
```

Now try SET without a mode:
```
SET freq 5
```
**Expected:**
```
ERR no mode selected
```

Re-enter CONFIGURED:
```
MODE SOLID
```

---

## 8. START / STOP and data frame stream

Send:
```
START
```
**Expected:**
```
OK START
```

Then `FRAME@` lines should appear every ~100 ms. Example:
```
FRAME@0@0@0@0@0@0@-99@-99@-99@-99@-99@-99@-99@0@0
```

Verify:
- Lines start with `FRAME@`
- 16 `@`-separated tokens per line
- Fields are all integers
- Interval is roughly 100 ms (count ~10 lines over ~1 second)

Send:
```
STOP
```
**Expected:**
```
OK STOP
```
Frame output must stop immediately.

---

## 9. SET solid LED value while running

Send `MODE SOLID`, then `START`, then while frames are streaming:
```
SET REDLED 2000
```
**Expected:**
```
OK SET REDLED
```

And the Red LED on the PCB should light up at the set brightness. The frame `Red` field should now show `2000`.

Send `STOP` when done.

---

## Pass criteria

All responses match expected output and the FRAME stream behaves as described. Any `ERR` where `OK` is expected, or missing/malformed frames, is a failure.
