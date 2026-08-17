# Plan: Randomized knob-LED mapping in Behavioral mode

## Context

`PLAN.md` was just reset after M1-M15 (all prior firmware/GUI milestones for
the Rapid Experiment Prototyping Tool) shipped and were hardware-verified.
The one new milestone on the board: in Behavioral mode, knob1 always drives
LEDA and knob2 always drives LEDB. The researcher wants this relationship
randomized on each trial stop (optionally, via a new flag), so subjects can't
learn a fixed knob->LED mapping across trials, and wants the GUI to both show
and save which LED each knob drove per press.

This is a bounded feature addition — no new subsystems, only changes inside
the already-shipped Behavioral mode code paths in
`prototype2/Firmware/configurableFirmware/` and
`prototype2/GUI/configurableFirmware/`.

Clarified with the user:
- The live on-screen press table in Behavioral mode should show the knob->LED
  mapping in real time (not saved-file-only).
- The new frame fields (shared code path across all sub-modes) report `NONE`
  for both knobs outside Behavioral mode.

## Firmware changes (`prototype2/Firmware/configurableFirmware/`)

### `globals.h` / `globals.cpp`
- Add near the LED-assignments block (`globals.h:27-42`):
  - `extern bool knobShuffleEnabled;` — user-facing flag, mirrors `hueEnabled`.
  - `extern volatile bool knobsSwapped;` — runtime state (must be `volatile`:
    written in `runBehavioral()`'s experiment thread, read from
    `serialFrameOutput()` which also fires off a periodic timer).
- `globals.cpp`: initialize both to `false`; add both to `applyDefaults()`
  (alongside `hueEnabled = false;` at `globals.cpp:65`) so a fresh
  `MODE BEHAVIORAL` always starts unswapped with the flag off.

### `serialParser.cpp`
Follow the exact `hue` triple-touch pattern (`printGet()` line 39,
`printGetParam()` line 71, `applyParam()` line 120):
- `printGet()`: `Serial.print("knobShuffle="); Serial.println(knobShuffleEnabled ? 1 : 0);`
- `printGetParam()`: same, guarded by `param == "knobShuffle"`.
- `applyParam()`: `else if (p == "knobShuffle") { knobShuffleEnabled = (v.toInt() != 0); }`
  — no mode-guard (unlike `hue`'s Behavioral-only rejection): the flag is
  harmless to accept in any mode since only `behavioralMode.cpp` reads it,
  and it's reset by `applyDefaults()` on every `MODE` switch regardless.

### `behavioralMode.cpp`
Currently `PIN_KNOB_A` always feeds role A (`ledA`/`minA`/`maxA`) and
`PIN_KNOB_B` always feeds role B — hardcoded at the anchor step
(lines 73-74) and the live trial loop (lines 86-87). Change:

1. At the top of each outer-loop trial iteration (right before the anchor
   computation, so both the anchor and the live loop use the same pins for
   that trial), resolve:
   ```cpp
   int pinA = knobsSwapped ? PIN_KNOB_B : PIN_KNOB_A;
   int pinB = knobsSwapped ? PIN_KNOB_A : PIN_KNOB_B;
   ```
   and use `pinA`/`pinB` in place of `PIN_KNOB_A`/`PIN_KNOB_B` in both the
   anchor-offset lines (73-74) and the live knob-read lines (86-87). Roles
   (`ledA`/`ledB`, their ranges, `targetA`/`targetB`, `walkJump`) are
   untouched — only the physical pin source moves.
2. Inside the existing `if (pressed)` block, right after `targetA`/`targetB`
   are recomputed (after line 113, before the `break` at line 114) — i.e. at
   the moment the trial has stopped and the next trial's anchor hasn't run
   yet:
   ```cpp
   if (knobShuffleEnabled) {
       long r = random(0, 10000);
       if (r >= 5000) knobsSwapped = !knobsSwapped;
   }
   ```
   This implements "if <0.5 keep current, if >=0.5 swapped" literally. Note
   for the implementer: a 50%-keep/50%-flip toggle and a fresh 50/50 draw are
   statistically identical here (two states, p=0.5) — this form was kept
   because it matches the requirement text directly. Trial 1 is naturally
   unswapped, since nothing has "stopped" before it and `knobsSwapped`
   defaults to `false`.
3. `behavioralFlickerISR()` needs no changes — it already reads whatever
   `ledVal[ledA]`/`ledVal[ledB]` currently hold, and those are written by the
   (now pin-swapped) trial loop.

### `dataFrame.cpp`
Append two fields — `Knob1`, `Knob2` — to the end of `serialFrameOutput()`
(after the existing `trigFlag` field, which currently ends the line via
`Serial.println(trigFlag)` at line 22): change that to `Serial.print(trigFlag); Serial.print("@");`
then:
```cpp
if (activeMode == MODE_BEHAVIORAL) {
    Serial.print(knobsSwapped ? "LEDB" : "LEDA"); Serial.print("@");
    Serial.print(knobsSwapped ? "LEDA" : "LEDB");
} else {
    Serial.print("NONE@NONE");
}
Serial.println();
```
Values are the *role name* (`LEDA`/`LEDB`), not the LED color — knob1's
value tells you which role (and therefore which configured LED) it's
currently driving, matching the plan's "their value should change between
LEDA, and LEDB" requirement.

### Docs
- `docs/prototype2/statusREP.md`: add `knobShuffleEnabled`/`knobsSwapped` to
  the globals reference table, `SET knobShuffle 0/1` to the SET-commands
  table, and update the frame-format line/description to the new 17-field
  layout. Update the Behavioral-mode (M6) section description.
- New `tests/test_m16_instructions.md` (manual, via Arduino IDE serial
  monitor, per the existing `tests/test_mN_instructions.md` convention):
  verify `SET`/`GET knobShuffle`, default-off behavior (knob1 always drives
  LEDA), enabled behavior (Knob1/Knob2 frame fields alternate across
  trials — roughly 50/50 over ~20+ trials), and that the *press* frame's
  Knob1/Knob2 reflect the mapping used **during** that trial, not the one
  chosen right after (since the swap decision happens after the press is
  logged).

## GUI changes (`prototype2/GUI/configurableFirmware/`)

### `protocol.py`
- Append `"Knob1", "Knob2"` to `FRAME_FIELDS` (line 29-33).
- Exclude them from int-coercion: `_FRAME_INT_FIELDS = tuple(f for f in FRAME_FIELDS if f not in ("LEDA", "LEDB", "Knob1", "Knob2"))`.
- Update the module docstring's documented frame format (lines 14-16).

### `param_form.py`
- Add to `PARAM_SPEC` (near `hue`, line 130):
  `"knobShuffle": ParamMeta("bool", None, "Randomize knob-LED mapping", stage="Stimulus"),`
  (reuses Behavioral's existing "Stimulus" group box — no new stage needed).
- Add `"knobShuffle"` as a bare entry in `_ROW_ORDER` (near `"hue"`, line 156).
- No other changes needed — `set_values()`/`values()`/`changed_values()` are
  generic over registered widgets.

### `behavioral_view.py`
- `BEHAVIORAL_PARAM_KEYS` (line 41-46): append `"knobShuffle"` — this alone
  makes the checkbox appear on `BehavioralConfigPage`'s form and ride through
  Load/Save JSON (`beh_configparams_*.json`) and `changed_values()`/
  `full_settings()` automatically, exactly like every other Behavioral param.
- `BehavioralSessionPage`:
  - Widen the table from `QTableWidget(0, 3)` to `QTableWidget(0, 5)`
    (line 174), with static header default
    `["Press #", "A", "B", "Knob1", "Knob2"]`.
  - In `start_session()` (line 212), extend the dynamic header line to
    `["Press #", self._led_a, self._led_b, "Knob1", "Knob2"]`.
  - In `_on_line()` (line 302-323), when `frame["Press"] == 1`, read
    `frame.get("Knob1", "NONE")` / `frame.get("Knob2", "NONE")` directly
    (no last-live-frame fallback needed — these fields aren't touched by the
    `allLedsOff()` press-time zeroing that `a_val`/`b_val` need to guard
    against) and add them to the inserted row tuple (currently
    `(self._press_count, a_val, b_val)` at line 322).
  - No changes needed to `_on_save_press_log()` — `self._press_log` already
    stores whole frame dicts, and it already iterates `FRAME_FIELDS`
    generically (line 268), so `Knob1`/`Knob2` flow into the saved combined
    JSON automatically once `protocol.py` is updated.

### `test_offscreen.py`
- The single shared `_frame(...)` helper (line 63-69) builds every test's
  `FRAME@` line. Add `knob1="NONE", knob2="NONE"` parameters there (with
  those defaults) and append them to the `fields` tuple — every existing
  call site across the whole suite keeps working unchanged via the
  defaults; only new Behavioral-specific tests need to pass `knob1=`/`knob2=`
  explicitly.
- Add tests: `knobShuffle` checkbox round-trips through `ParamForm`/config
  save-load; `BehavioralSessionPage`'s table has 5 columns with the right
  headers and picks up `Knob1`/`Knob2` values from an injected frame;
  `parse_frame` correctly parses the new 17-field frame.

## Verification
- GUI: `UV_PROJECT_ENVIRONMENT=.venv-linux uv run python test_offscreen.py`
  (per project convention — offscreen, no hardware needed) to confirm no
  regressions from the frame-field-count change and that new tests pass.
- Firmware: manual flash + `tests/test_m16_instructions.md` via Arduino IDE
  serial monitor (user does this step, per CLAUDE.md — manual flash/test is
  a final approval step).
- After hardware verification, update `PLAN.md` to mark the milestone done
  (matching the existing status-note convention used for M1-M15).
