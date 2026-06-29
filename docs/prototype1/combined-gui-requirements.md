# Combined GUI requirements

Requirements for `prototype/combined_gui/`, a single app that runs both the
behavioral (knobs) and grid (EEG) experiments against the combined firmware
(`prototype/firmware/experimentStimControl/`, see
`docs/experimentStimControl-configure.md`). Supersedes `prototype/gui/` and
`prototype/grid_gui/` as the GUI actually used going forward; both are kept
untouched as reference.

## Flow

Connect -> Participant -> Experiment select (Behavioral / Grid) -> Mode
(Default / Advanced, scoped to the chosen experiment) -> Session.

- **Connect**: same as both existing GUIs (auto-detect by PJRC vendor ID,
  manual fallback). One `SerialLink` for the whole app session.
- **Participant**: pick a save folder, then add a session to an existing
  participant or create a new one (Subject ID + Group), same UI as the
  current behavioral GUI's `ParticipantPage`.
- **Experiment select**: a new screen, radio choice Behavioral vs Grid (no
  default preselected). Determines which command prefix
  (`BEHAVIORAL*`/`GRID*`), which settings shape, and which session screen
  comes next.
- **Mode**: Default/Advanced for the chosen experiment, settings form
  pre-filled from `BEHAVIORALGET`/`GRIDGET` as appropriate. Sends
  `BEHAVIORALMODE ...`/`BEHAVIORALSET ...` or `GRIDMODE ...`/`GRIDSET ...`.
- **Session**: behaves exactly like the matching existing GUI's session
  screen (behavioral: live scatter + press table + autosave; grid: stimulus
  grid + progress bar, no data logging). "Back" returns to Experiment select
  (re-querying `*GET` so settings reflect whatever is active on the
  firmware), not all the way to Participant, so the same participant can run
  both experiments without re-entering their info.

## Protocol

Both existing GUIs predate the combined firmware's renamed commands and need
updating regardless of unification:

- Behavioral: `START`/`STOP`/`MODE`/`SET`/`GET` -> `BEHAVIORALSTART`/
  `BEHAVIORALSTOP`/`BEHAVIORALMODE`/`BEHAVIORALSET`/`BEHAVIORALGET`.
- Grid: `MODE`/`SET`/`GET` -> `GRIDMODE`/`GRIDSET`/`GRIDGET` (`GRIDSTART`/
  `GRIDSTOP` are unchanged).
- Mutual exclusion is enforced firmware-side (`"Grid trial active"` /
  `"Behavioral trial active"`); the GUI should surface that rejection text
  if it ever arrives (it shouldn't in normal use, since Experiment select
  prevents starting one while genuinely running the other from this GUI,
  but another serial client or a stale session could still trigger it).

## Participant metadata

Three CSVs per save folder (per the user's decision):

- `participants_behavioral.csv` — one row per behavioral session: `sub_id,
  group, session, file, datetime` + the six behavioral config columns
  (`mode, flickerFrequencyHz, amberValue, maxRed, maxGreen, minRed,
  minGreen`). Same shape as the current `participants.py` schema.
- `participants_grid.csv` — one row per grid session: `sub_id, group,
  session, datetime` + the eleven grid config columns (no `file` column,
  since grid doesn't save a data file — the EEG recording is the data).
- `participants_master.csv` — one row per session across *either*
  experiment: `sub_id, group, experiment, session, datetime`, where
  `experiment` is `behavioral`/`grid` and `session` is that experiment's own
  session number (matches the row just written to the per-experiment file).
  This is what the Participant screen reads to list "existing participants"
  in the folder regardless of which experiment they did before, and what
  resolves the per-experiment session numbering
  (`next_session_number(folder, sub_id, experiment)`).

All three are written together at session start (behavioral: when "Start"
is first pressed for that session, same as today; grid: same point, even
though no data file is created for it).

## Module layout

New `prototype/combined_gui/` (own `uv` app: `pyside6`, `pyqtgraph`,
`pyserial`), built by combining and adapting the existing modules rather
than importing across the two reference directories:

- `serial_link.py` — copied verbatim (identical in both source GUIs).
- `protocol.py` — merges both `protocol.py` files: behavioral and grid each
  keep their own `Settings` dataclass, `SETTING_NAMES`, `parse_get_response`,
  `parse_dataframe`, `build_set_command` (distinct field shapes, no
  unification of the dataclasses), prefixed `behavioral_`/`grid_` where
  names would otherwise collide.
- `participants.py` — generalizes the current one to the three-CSV scheme
  above, parameterized by experiment (`"behavioral"`/`"grid"`).
- `main_window.py` — `ConnectPage` (shared), `ParticipantPage` (adapted to
  read `participants_master.csv`), new `ExperimentSelectPage`, `ModePage`
  variants per experiment (or one page parameterized by experiment, reusing
  `SETTING_NAMES`), `BehavioralSessionPage` (current behavioral
  `SessionPage`, renamed) and `GridSessionPage` (current grid `SessionPage`,
  renamed).
- `main.py` — entry point.

## Verification

Same standard as prior milestones: end-to-end with a fake serial link under
`QT_QPA_PLATFORM=offscreen` (both experiment paths, Default and Advanced,
Back-to-Experiment-select re-entry, all three CSVs), then a real-hardware
pass on native Windows once the offscreen pass is clean.
