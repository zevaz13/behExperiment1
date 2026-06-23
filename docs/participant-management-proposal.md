# Proposal: participant / session management and data export (GUI)

Status: proposal for milestone 2.4, second item. Not yet implemented — this
documents the design and the decisions needed before building.

## Goal

CLAUDE.md and `startingPoint/experiment.md` call for the GUI to act as the
experiment logger: "Creating participants and saving data in txt files." The
new Python GUI (`prototype/gui/`) currently has none of this. This proposal
covers what participant/session metadata to capture, where it fits in the
flow, how runs map to files, what gets logged, and how data is saved.

## What exists now

- **New GUI flow**: Connect -> Mode/Settings -> Session. The session screen
  logs one row per button press into a `Trial/Red/Green` table and offers a
  manual "Save Results..." button that writes that table to a `.txt` at the
  end (`main_window.py`). No participant identity, no session number, no
  auto-save. If the app closes before Save, the data is lost.
- **Legacy C# GUI conventions** (reference, `startingPoint/GUImetamers/`):
  - A setup screen captures a **subject ID** and an **output folder** (both
    required) before the experiment screen opens (`secreen2.cs`).
  - Each run is auto-saved to its own file named
    `{subID}_{expType}_R{n}.txt`, where `n` auto-increments by scanning for
    the first name that does not already exist (`GetNextFileName`), so runs
    never overwrite each other.
  - The file starts with the header
    `TriggerCue TrialNumber Amber red green Press`, then **every** received
    dataframe is appended space-separated and flushed immediately (streaming
    auto-save, not save-at-end).

## Proposed design (recommended path)

### 1. New "Participant" screen

Insert one screen between Connect and Mode:

```
Connect -> Participant -> Mode/Settings -> Session
```

Fields:
- **Participant ID** (required, free text, e.g. `S01`).
- **Output folder** (required; folder picker, remembered across runs).
- **Notes** (optional, free text).

Rationale for placing it after Connect and before Mode: identity is
session-level metadata, set once, independent of the per-run firmware
settings chosen on the Mode screen. Keeping it separate also mirrors the
legacy two-step setup the operators already know.

### 2. Run / file mapping

In the new firmware one `START`..`STOP` is a single session that can span
many searches (auto-continue). Map **one Start..Stop session = one run file**,
named `{participantID}_R{n}.txt` with `n` chosen by the same
"first name that doesn't exist" scan the legacy GUI uses. Each new Start in
the same participant folder gets the next `n`. (Dropped the `_{expType}`
segment the legacy name had — there is only one experiment type here. It
comes back naturally if the grid experiment, milestone 3, is added later.)

### 3. Auto-save (the main robustness change)

Open the run file on **Start** and append each logged button-press result
immediately, flushing as it goes — so a crash or accidental close never loses
collected metamer points. Keep the existing "Save Results..." button as a
manual export/copy convenience, but it is no longer the only path to durable
data.

### 4. File contents

Each run file starts with a short metadata header so the file is
self-describing, then the data:

```
# participant: S01
# session: R3
# datetime: 2026-06-23T14:02:11
# mode: ADVANCED  flicker: 10 Hz  amber: 2400  red: [0,3000]  green: [0,2400]
Trial Red Green
1 1420 980
2 1605 1120
...
```

The `#` comment lines are easy for analysis scripts to skip. The data block
keeps the current GUI's `Trial Red Green` columns (the metamer points are
what the experiment produces, per `experiment.md`'s "cloud of points").

## Decisions needed before building

1. **What to log per run** — the experiment's data product is the cloud of
   button-press metamer points, so the recommendation is to log **presses
   only** (`Press=1`), as the table already does. The alternative is to also
   write the full 100 ms telemetry stream (`Press=0`) to capture each
   search's whole trajectory, matching the legacy "write every frame"
   behavior, at the cost of much larger files that analysis must filter.
   Option: write presses to the main run file and, if wanted, the raw stream
   to a separate `{participantID}_R{n}_raw.txt`.
2. **Metadata header** — include the `#` comment block shown above, or keep
   files header-line-only like the legacy format for drop-in compatibility
   with any existing analysis scripts?
3. **Session numbering** — auto-increment `_R{n}` by scanning the folder
   (recommended, matches legacy, no manual entry), or let the operator set
   the session number explicitly?
4. **Folder memory** — remember the last-used output folder between launches
   (small `QSettings` store), or ask every time?

Once these are settled this becomes a concrete implementation task: a new
`ParticipantPage`, a small `run_logger` helper for the auto-save file, and
wiring Start/Stop and the press handler to it.
