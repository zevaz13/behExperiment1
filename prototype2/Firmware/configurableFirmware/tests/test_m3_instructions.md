# M3 Manual Test — Hue Sensor Module

Open the Arduino IDE Serial Monitor at **38400 baud**, line ending **Newline**.
Flash and reset.

---

## 1. Hue disabled (default) — fields are -99

Send:
```
MODE SOLID
START
```
Verify the FRAME@ line has `-99` in positions 8–12 (HUE_R through HUE_L):
```
FRAME@0@0@0@0@0@0@-99@-99@-99@-99@-99@-99@-99@0@0
```
Send `STOP`.

---

## 2. START with hue=true and sensor absent

Disconnect the hue sensor from I2C. Then:
```
MODE SOLID
SET hue 1
START
```
**Expected:**
```
ERR hue sensor not connected
```
Firmware stays in CONFIGURED (GET should still work, no frames).

---

## 3. Hue sensor connected — fields populated

Reconnect the sensor. Send:
```
MODE SOLID
SET hue 1
START
```
**Expected:** `OK START`

FRAME@ lines should now have real values in positions 8–12:
```
FRAME@0@0@0@0@0@0@<R>@<G>@<B>@<CT>@<L>@-99@-99@0@0
```
- R, G, B should be non-zero integers reflecting the ambient light
- CT is the colour temperature in Kelvin (typically 2000–8000)
- L is lux (varies with lighting)

---

## 4. Values change with illumination

While running with hue enabled, shine a red light at the sensor and verify HUE_R increases. Point a brighter light and verify HUE_L increases.

---

## 5. Hue fields reset to -99 after SET hue 0

While running (hue enabled):
```
SET hue 0
```
**Expected:** `OK SET hue`
Next frame should have `-99` in all HUE positions.

Re-enable: `SET hue 1` — values return.

Send `STOP` when done.

---

## Pass criteria

- Sensor absent + `hue=1` → `ERR hue sensor not connected`, stays in CONFIGURED
- Sensor absent + `hue=0` → runs normally, HUE fields are -99
- Sensor present + `hue=1` → HUE fields show real sensor values that change with illumination
- `SET hue 0` while running → HUE fields immediately return to -99
