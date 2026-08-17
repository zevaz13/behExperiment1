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
- [ ] Firmware: manual flash + `tests/test_m16_instructions.md` via Arduino
      IDE serial monitor (user step, per CLAUDE.md)
- [ ] After hardware verification, mark M16 done in this file