# Plan

## Prototype 2 Rapid Experiment Prototyping Tool

Design spec: `docs/superpowers/specs/2026-07-01-configurable-firmware-design.md`
Requirements: `docs/prototype2/requirementsREP.md`

Output paths:
- Firmware: `prototype2/Firmware/configurableFirmware/`
- GUI: `prototype2/GUI/configurableFirmware/`

### Testing convention
- Firmware: manual test instruction files (`tests/test_mN_instructions.md`) run via Arduino IDE serial monitor
- GUI: offscreen tests + mock serial link

---

## Milestones

### M16: Randomized knob-LED mapping in Behavioral mode

Randomize which knob drives LEDA vs LEDB in Behavioral mode, on each trial
stop, gated behind a new `knobShuffle` flag (default off = current fixed
knob1->LEDA/knob2->LEDB behavior). The live press table and saved data must
show which LED each knob drove per press. Bounded to the already-shipped
Behavioral mode code paths only — no new subsystems. Full design in
`randomKnobsplan.md`.

#### Firmware (`prototype2/Firmware/configurableFirmware/`)
- [x] `globals.h`/`globals.cpp`: add `knobShuffleEnabled` (bool) and
      `knobsSwapped` (`volatile bool`); default both `false`; reset in
      `applyDefaults()`
- [x] `serialParser.cpp`: `GET`/`SET knobShuffle` following the `hue`
      triple-touch pattern (`printGet`, `printGetParam`, `applyParam`), no
      mode-guard needed
- [x] `behavioralMode.cpp`: resolve `pinA`/`pinB` from `knobsSwapped` at the
      top of each trial (anchor + live loop use the resolved pins); after a
      press stops a trial, if `knobShuffleEnabled`, draw uniform `[0,1)` and
      flip `knobsSwapped` when `>= 0.5`
- [x] `dataFrame.cpp`: append `Knob1`/`Knob2` fields to
      `serialFrameOutput()` — role name (`LEDA`/`LEDB`) per current
      `knobsSwapped` state in Behavioral mode, `NONE`/`NONE` otherwise
- [x] `docs/prototype2/statusREP.md`: document `knobShuffleEnabled`/
      `knobsSwapped` globals, `SET knobShuffle 0/1`, new 17-field frame
      layout, updated M6 (Behavioral mode) description, file-map/milestone
      table entries, new "What M16 implements" sections (firmware + GUI)
- [x] New `tests/test_m16_instructions.md`: manual serial-monitor test for
      `SET`/`GET knobShuffle`, default-off fixed mapping, enabled-mode
      alternation across ~20+ trials, and press-frame timing (reflects the
      mapping used *during* the trial, not the post-press swap)

#### GUI (`prototype2/GUI/configurableFirmware/`)
- [x] `protocol.py`: append `Knob1`/`Knob2` to `FRAME_FIELDS`, exclude from
      int-coercion, update docstring
- [x] `param_form.py`: add `knobShuffle` to `PARAM_SPEC` (Stimulus stage,
      bool) and `_ROW_ORDER`
- [x] `behavioral_view.py`: add `knobShuffle` to `BEHAVIORAL_PARAM_KEYS`;
      widen `BehavioralSessionPage` table to 5 columns
      (`Press #`, LEDA name, LEDB name, `Knob1`, `Knob2`); populate the new
      columns in `_on_line()` from the frame
- [x] `test_offscreen.py`: added `knob1=`/`knob2=` params (default `"NONE"`)
      to the shared `_frame()` helper, `"knobShuffle": "0"` to
      `_BEHAVIORAL_DEFAULTS`; added `test_behavioral_knob_shuffle_checkbox_round_trips`,
      `test_behavioral_table_has_knob_columns`, and extended
      `test_parse_frame_valid` for the 17-field frame

#### Verification
- [x] `UV_PROJECT_ENVIRONMENT=.venv-linux uv run python test_offscreen.py`:
      60/61 tests pass. The full-suite run hits a pre-existing Qt/offscreen
      teardown segfault partway through (documented in `statusREP.md`'s M14
      notes) — confirmed unrelated to M16 by reproducing it identically on
      unmodified baseline code via `git stash`. Every test run in isolation
      (all 61, one subprocess each) passes except
      `test_grid_save_figure_contents_depend_on_hue`, which also fails
      identically on unmodified baseline code (pre-existing, unrelated to
      Behavioral/knob code — Grid mode, untouched by M16). All Behavioral
      and M16-specific tests pass, including the 2 new ones.
- [x] Firmware: manual flash + `tests/test_m16_instructions.md` via Arduino
      IDE serial monitor (user step, per CLAUDE.md) — passed
- [x] GUI: live-hardware run on native Linux Mint (not WSL), Teensy over
      `/dev/ttyACM*`; required installing the `libxcb-cursor0` system package
      for the Qt6 xcb platform plugin — all tested and working

**M16: done.**
### M17: Per-session config memory (Linear / Grid / Behavioral)

A session is one GUI run with one Teensy connection. Each mode opens with
firmware defaults the first time; after that, its config form keeps the last
values (edited or loaded from JSON) until the connection drops or the GUI
closes.

#### GUI (`prototype2/GUI/configurableFirmware/`)
- [x] `linear_view.py`, `grid_view.py`, `behavioral_view.py`: config page
      populates the form from GET only on the first `setup()` of a session
      (`_configured` flag); `_baseline` is still refreshed every time, so
      `changed_values()` re-sends the kept values via SET on Start
- [x] Same three pages: `forget_session()` clears the flag
- [x] `main_window.py`: `_teardown_link()` calls `forget_session()` on every
      config page (disconnect or window close)
- [ ] Not changed: experiment name and hue log path still reset on each
      `setup()` (`SavingSection.reset()`)

#### Verification
- [x] Scratch script (offscreen): edit a Linear param, call `setup()` again,
      value kept and reported by `changed_values()`; after `forget_session()`
      the form returns to defaults
- [ ] `test_offscreen.py`: full-suite run hits the known Qt teardown crash;
      no automated test added for M17 yet
- [ ] GUI: live-hardware check (run Linear, Back, reopen Linear: config
      unchanged; unplug/replug: defaults) -- user step
