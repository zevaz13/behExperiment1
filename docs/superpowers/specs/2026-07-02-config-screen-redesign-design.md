# Config screen redesign — Linear/Grid/Behavioral

Status: approved, not yet implemented.

## Problem

The Linear, Grid, and Behavioral config screens (`linear_view.py`, `grid_view.py`,
`behavioral_view.py`, all built on `param_form.py`'s `ParamForm`) currently render
every configurable parameter as one flat `QFormLayout`, row label = the raw firmware
key (`bgStim1Led`, `ref2Int`, `baselineLed3Val`, ...). Linear has 25 such rows, Grid
28, Behavioral 17. There's no grouping, no explanation of what a param does or which
part of the experiment it affects, and no visual feedback — you can't tell what LED
is assigned where, or what the stim/reference phases will actually look like, without
reading raw text.

This redesign reorganizes those three screens around the experiment's actual
structure (timing / stimulus / reference / baseline / hue / saving), gives every
field a clear label instead of the firmware variable name, and adds light visual
feedback (LED color swatches, a live stim-vs-reference phase diagram).

## Non-goals

- Solid mode is unaffected (it has no config screen — just sliders).
- The firmware SET/GET protocol does not change. This is a GUI-only redesign.
- No new firmware params, no new sub-modes.
- No fancy custom range-slider widgets — combined rows use plain paired spinboxes.
- Data-saving-to-file scope doesn't expand: Behavioral still doesn't save experiment
  data (deferred, per M12 status); this redesign doesn't add that.

## Stages

Six stages. A mode only gets a `QGroupBox` for a stage if it has at least one field
in that stage.

| Stage | Linear | Grid | Behavioral |
|---|---|---|---|
| Timing | freq, trialLength, interTrialWait | freq, trialLength, interTrialWait, order | freq, interTrialWait |
| Stimulus | LEDA+range, steps, bgStim1, bgStim2 | + LEDB+range | LEDA+range, LEDB+range, bgStim1, bgStim2 (no steps) |
| Reference | ref1, ref2, ref3 | ref1, ref2, ref3 | ref1, ref2, ref3 |
| Baseline | nBaselinesStart/End, baselineLed1/2/3 | same | — (not supported by firmware) |
| Hue | hue checkbox | hue checkbox | — (not supported by firmware) |
| Saving | experiment name, save-hue-data, destination | same | — (no data saving exists for Behavioral yet) |

Config-file Load/Save (`linearParamConfig_*.json` etc.) stays a **top toolbar
action**, above all stages, unchanged from today — that's saving/loading the
*configuration itself*. The **Saving** stage is a distinct concept: it's about the
*experiment's data output* (the hue log file), which only Linear/Grid produce today.

Stage order on screen, top to bottom: Timing, Stimulus, Reference, Baseline, Hue,
Saving. (Rationale: timing/stimulus/reference are the core of every mode and belong
together at the top; baseline/hue are secondary/optional; saving is the last thing
you touch before hitting Start.)

## Data model changes (`param_form.py`)

`PARAM_SPEC` keeps its existing per-key entries (`kind`, numeric range) and gains a
`label` (and `unit` where meaningful — `"Hz"`, `"ms"`). Example:

```python
PARAM_SPEC: dict[str, ParamMeta] = {
    "freq":        ParamMeta("int", (1, 500), "Flicker frequency", unit="Hz", stage="Timing"),
    "trialLength": ParamMeta("int", (200, 30000), "Stimulus duration", unit="ms", stage="Timing"),
    "interTrialWait": ParamMeta("int", (50, 30000), "Inter-trial interval", unit="ms", stage="Timing"),
    "nBaselinesStart": ParamMeta("int", (0, 50), "Baseline trials (start)", stage="Baseline"),
    "nBaselinesEnd":   ParamMeta("int", (0, 50), "Baseline trials (end)", stage="Baseline"),
    "steps":       ParamMeta("int", (2, 50), "Number of steps", stage="Stimulus"),
    "LEDA":        ParamMeta("led", None, "Primary LED (LEDA)", stage="Stimulus", exclusion_group="stim"),
    "LEDB":        ParamMeta("led", None, "Secondary LED (LEDB)", stage="Stimulus", exclusion_group="stim"),
    "hue":         ParamMeta("bool", None, "Enable hue sensor", stage="Hue"),
    ...
}
```

`ParamMeta` is a small `NamedTuple`/`dataclass`: `kind`, `range`, `label`, `unit=None`,
`stage=None`, `exclusion_group=None`. This is additive to the existing dict — no
behavioral change to `ParamForm.values()`/`set_values()`/`changed_values()`, which
still operate on the same flat `self._widgets: dict[str, Widget]` keyed by firmware
param name. **This is the key invariant that keeps `main_window.py` untouched**: the
round-trip contract between the form and the SET/GET protocol doesn't change, only
how the widgets are laid out and labeled.

Two new rendering-only tables (they don't introduce new firmware-facing types, just
describe how two already-typed keys share one visual row):

```python
# (row_label, low_key, high_key) -> renders as "label: [spin lo] to [spin hi]"
RANGE_PAIRS = [
    ("LEDA sweep range", "minA", "maxA"),
    ("LEDB sweep range", "minB", "maxB"),
]
```

LED+intensity rows reuse the **existing** `_LED_PHASE_FIELDS` table (already present
in `param_form.py` for `format_led_assignments()`): `(led_key, val_key, phase_label)`
tuples for bgStim1/2, ref1/2/3, baselineLed1/2/3. Each renders as one row:
`[LED dropdown+swatch]  intensity [spinbox]`.

`order`'s raw range is `[0,4]`, but `gridMode.cpp` confirms order 0 and 1 are
identical (both "identity" traversal — "no distinct meaning defined for 0"). The GUI
drops `0` and shows a 4-item dropdown mapped to firmware values `{1,2,3,4}`:
- "Standard" → 1 (default)
- "Flip LEDB axis" → 2
- "Flip LEDA axis" → 3
- "Flip both axes" → 4

`LED_COLORS` (`{"RED": "#f70404", ...}`) moves from `solid_view.py` into
`param_form.py` as the single source of truth; `solid_view.py` imports it from there
instead of keeping its own copy.

## `ParamForm` rendering changes

`ParamForm.__init__(keys)` keeps its signature. Internally, instead of one
`QFormLayout`, it:

1. Groups `keys` by `PARAM_SPEC[key].stage`, preserving first-seen order among the
   five canonical stages `ParamForm` handles (Timing, Stimulus, Reference, Baseline,
   Hue) — the Saving stage is *not* built by `ParamForm` (see below, it's GUI-only
   and has no firmware keys).
2. For each non-empty stage, creates a `QGroupBox(stage_name)` containing a
   `QFormLayout`.
3. Within a stage, renders `RANGE_PAIRS` and `_LED_PHASE_FIELDS` entries whose keys
   are present as single combined rows (two widgets in one `QHBoxLayout` cell); all
   other keys render as their own row as before.
4. Every LED-kind widget (`QComboBox`) gets a small fixed-size `QLabel` swatch to its
   left, colored via `LED_COLORS`, updated on `currentTextChanged`.
5. Every widget is still registered in `self._widgets[key]` exactly as before —
   `values()`, `set_values()`, `changed_values()` are unchanged.
6. A new `values_changed` `Signal()` is emitted whenever any child widget changes
   (each widget's own change signal is connected to re-emit this). Used by
   `PhaseDiagram` and by the exclusion-filtering pass below.

### LED exclusion filtering

For each `exclusion_group` (`"stim"`: LEDA/LEDB/bgStim1Led/bgStim2Led; `"reference"`:
ref1Led/ref2Led/ref3Led; `"baseline"`: baselineLed1/2/3), `ParamForm` keeps a list of
the `QComboBox` widgets sharing that group. On `values_changed` (and once right after
`set_values()` populates initial values), for every combo in a group: enable all
items, then disable (via `QStandardItemModel` item flags — not remove, so the combo's
`currentText()`/index stays stable) whichever LED names are the *current selection*
of some *other* combo in the group. `"NONE"` is never disabled. A combo's own current
value is never disabled (so it can't accidentally invalidate itself).

This is a GUI-side convenience only — the firmware's own duplicate-LED rejection
(`serialParser.cpp`, already tested) remains the actual source of truth and stays
unchanged; this just stops the invalid choice from being picked in the first place.

## `PhaseDiagram` (new widget, `param_form.py`, shared by all 3 modes)

A small `QWidget` with two side-by-side titled panels, "Stim" and "Reference". Each
panel lists small colored chips (reusing `LED_COLORS`) with a role label, built from
a snapshot of the current form values:

- Stim panel: LEDA (if set), LEDB (if set, Grid/Behavioral only), bgStim1, bgStim2.
- Reference panel: ref1, ref2, ref3.

Constructed with a reference to the owning `ParamForm` (or just fed a `dict` via a
`refresh(values: dict)` method) and connected to `ParamForm.values_changed`. No
timing/animation — a static "what's on in each phase right now" summary. Placed
between the Stimulus and Reference group boxes in each config page's layout.

Baseline doesn't get a diagram: it's a distinct trial type (solid display for the
whole `trialLength`, not a two-phase flicker), and its own group box (LED+intensity
rows, already using swatches) is self-explanatory without one.

## Saving stage (Linear/Grid only): `SavingSection` (new widget)

Replaces today's flow, where `LinearConfigPage`/`GridConfigPage._on_start()` pops a
`QInputDialog` (experiment name) and then a `QFileDialog` (destination) *at* Start
time. New behavior, all decided ahead of time on the config screen itself:

- `QLineEdit` "Experiment name" (optional, as today).
- The existing "Save hue data to file" `QCheckBox` (disabled until `hue` is
  checked — unchanged behavior, just relocated here).
- A read-only `QLineEdit` showing the destination path (or a placeholder like
  "(default location)"), plus a "Choose file..." button that opens the same
  `QFileDialog.getSaveFileName` as today, pre-filled with the same default name
  pattern (`<mode>hue_exp_<name>_<timestamp>.txt`) — just triggered by a button
  instead of automatically at Start.

`_on_start()` no longer opens any dialog: if "Save hue data to file" is checked, it
uses whatever destination is currently shown (the explicitly-chosen path, or — if
the user never clicked "Choose file...") the auto-computed default path in the
current working directory, computed silently at Start time. `start_requested` fires
immediately, matching every other button ordering already used for Stop/Back.

`hue_log_path()` keeps its existing signature/meaning; only how it gets populated
changes (no longer "populated inside `_on_start()`'s dialog handling", now
"populated by `SavingSection`, read by `_on_start()`").

## Per-file impact summary

- `param_form.py`: `ParamMeta`, enriched `PARAM_SPEC`, `RANGE_PAIRS`, `LED_COLORS`
  (moved here), `ParamForm` internals (grouping, pairing, swatches, exclusion
  filtering, `values_changed` signal), new `PhaseDiagram`, new `SavingSection`.
- `solid_view.py`: import `LED_COLORS` from `param_form` instead of defining it
  locally; no other change (Solid has no config screen).
- `linear_view.py` / `grid_view.py`: `LinearConfigPage`/`GridConfigPage` add a
  `PhaseDiagram` and a `SavingSection` to their layout (after the `ParamForm`);
  `_on_start()` simplifies to remove the dialog logic (moved into `SavingSection`).
- `behavioral_view.py`: no `SavingSection` (no data-saving exists for this mode);
  gets the stage-grouped `ParamForm` and a `PhaseDiagram` for free from the shared
  changes, no other code changes needed.
- `main_window.py`: **no changes** — `changed_values()`/`full_settings()`/
  `hue_log_path()` keep their existing signatures.

## Testing

Targeted additions to `test_offscreen.py`, not a rewrite of the existing suite:

- Stage grouping produces the expected `QGroupBox` titles for each mode (e.g.
  Behavioral has no "Baseline"/"Hue"/"Saving" boxes).
- Range-pair and LED-intensity-pair rows still round-trip correctly through
  `values()`/`set_values()`/`changed_values()` (the underlying contract other tests
  already depend on).
- Exclusion filtering: picking an LED in one dropdown of a group disables it in the
  others of the same group, but not across groups, and never disables "NONE".
- `order` dropdown maps its 4 labels to firmware values `{1,2,3,4}` correctly in both
  directions (`set_values`/`values`).
- `PhaseDiagram` reflects the current Stim/Reference assignments and updates on
  `values_changed`.
- `SavingSection`: checkbox stays disabled until hue is checked; "Choose file..."
  sets the path shown; Start with no explicit path falls back to the default
  computed path without opening a dialog.

Per current project convention: implement and verify with targeted runs (a small
standalone script or a single test function), not repeated full-suite runs during
development — see `test_offscreen.py`'s existing 90-ish tests, which are slow and
have a known offscreen/Qt teardown segfault unrelated to correctness.

## Open questions for the implementation plan (not blocking this spec)

- Exact pixel sizing/spacing of the new group boxes and `PhaseDiagram` — left to
  implementation, should look reasonable within the now-maximized windows (M13.3).
- Whether `QGroupBox` titles get a short one-line description under them (e.g.
  Baseline: "Solid LED display shown between stimulus trials") — nice-to-have, not
  required by this spec; can be added during implementation if it's cheap.
