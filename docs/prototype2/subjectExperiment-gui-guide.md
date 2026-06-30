# subjectExperiment GUI — User Guide

GUI for controlling the subjectExperiment firmware on the Teensy 4.0.
Located at `prototype2/GUIsubjectExp/`.

---

## Requirements

- Windows 10/11 (the Teensy enumerates as a COM port; WSL2 cannot see it without passthrough)
- Python managed by `uv` (install from https://docs.astral.sh/uv/getting-started/installation/)
- Teensy 4.0 flashed with `prototype2/Firmware/subjectExperiment/`

---

## Starting the GUI

Open a PowerShell or Command Prompt window, navigate to the project, and run:

```
cd prototype2\GUIsubjectExp
uv run python main.py
```

`uv` will install all dependencies into a local `.venv` on first run. Subsequent starts are fast.

---

## Application flow

```
Connect  ->  Participant  ->  Experiment Select  ->  Mode Config  ->  Session
                                    ^                                     |
                                    |__________ Back (re-queries GET) ____|
```

---

## Step-by-step walkthrough

### 1. Connect

The app scans all USB serial ports and automatically selects the first port
with a PJRC vendor ID (Teensy). It retries every 500 ms up to six times.

- If the Teensy is not found automatically, a port dropdown and Connect button
  appear. Select the correct COM port and click Connect.
- The app sends a `get` command to confirm the firmware identity. Once the
  firmware replies, the app advances to the Participant page.

### 2. Participant

**Save folder** — click Browse and select the folder where data files will be
written. This choice is remembered across sessions.

**Existing participant** — if the save folder contains a `participants_master.csv`
from previous sessions, existing subject IDs appear in a dropdown. Select one
and click Continue.

**New participant** — enter a Subject ID (any unique string, e.g. `S01`) and
choose a group (HC, PD, MD, Protan, Deutan, other), then click Continue.

### 3. Experiment Select

Choose one of four experiment / color-mode combinations:

| Radio button | Experiment type | Color pair |
|---|---|---|
| Behavioral — Red/Green | Knob-search behavioral | Red stimulus, Green secondary |
| Behavioral — Blue/Green | Knob-search behavioral | Blue stimulus, Green secondary |
| Grid (EEG) — Red/Green | 10x10 grid EEG | Red stimulus, Green secondary |
| Grid (EEG) — Blue/Green | 10x10 grid EEG | Blue stimulus, Green secondary |

The app color scheme (button borders, plot accents) updates immediately when
you change the selection. Click Continue to proceed.

### 4. Mode Config

The app queries the firmware for its current parameter values and pre-fills
the form.

**Default** — runs the experiment with the firmware's current parameters. No
changes are sent to the board. Click Continue.

**Advanced** — shows a form with all configurable parameters:

| Parameter | Description | Range |
|---|---|---|
| freq | Flicker frequency (Hz) | 1 – 100 |
| refAmber | Amber reference PWM during Phase B | 0 – 4095 |
| refCyan | Cyan reference PWM during Phase B | 0 – 4095 |
| maxA | Primary LED maximum (Red in RG, Blue in BG) | 0 – 4095 |
| minA | Primary LED minimum | 0 – 4095 |
| maxB | Green (secondary) maximum | 0 – 4095 |
| minB | Green (secondary) minimum | 0 – 4095 |
| nBaselinesStart | Baseline trials before stimuli (grid only) | 0 – 20 |
| nBaselinesEnd | Baseline trials after stimuli (grid only) | 0 – 20 |
| trialLength | Trial duration (ms) | 100 – 30000 |
| interTrialWait | Inter-trial interval (ms) | 0 – 10000 |
| order | Grid diagonal traversal start corner (grid only) | 1 – 4 |

Parameters grayed out are irrelevant for the selected experiment type (grid-only
params are grayed out when running behavioral, and vice versa). Only parameters
you change from their current values are sent to the board. Click Continue.

### 5. Session — Behavioral

The behavioral session page shows a live scatter plot and a press table.

- **X axis** — primary LED channel (Red in RG, Blue in BG), range [minA, maxA]
- **Y axis** — Green secondary channel, range [minB, maxB]
- **Circle marker** (amber/cyan) — live position of the current trial, updated
  every 100 ms from the firmware stream
- **X markers** (gray) — recorded button presses, one per trial
- **Star marker** (primary color) — running median of all press coordinates

**Start** — sends the start command to the firmware. The session file
(`{sub_id}_R{n}.txt`) is created in the save folder and the subject's row is
written to the CSV databases.

**Stop** — sends `stop` to the firmware. The session can be restarted with
Start (a new session number is not assigned; the existing file continues).

**Save Results** — opens a file dialog to export the current press table to a
text file. Auto-save already happens on every button press.

**Back** — returns to Experiment Select (disabled while running). The same
participant and folder are kept; you can run a different experiment type or
color mode without re-entering participant information.

### 5. Session — Grid (EEG)

The grid session page shows a 10x10 dot plot and a progress bar.

- **Dark gray dots** — not yet visited stimulus positions
- **Primary-color dots** (red/blue) — visited stimulus positions
- **Large amber/cyan dot** — current active stimulus
- **TRIG indicator** — lights up (amber/cyan) when the EEG trigger output is HIGH
- **Progress bar** — advances on each TRIG falling edge (end of each trial)
- **Status label** — shows "Baseline trial", "Stimulus N / 100", or "Done"

**Start** — sends the start command. The subject's row is written to
`participants_grid.csv` and `participants_master.csv`.

**Stop** — halts the experiment mid-run. Press Start again to restart from the
beginning (a new session entry is not created if Start was already pressed).

**Back** — enabled only when stopped or done.

The session completes automatically when the firmware sends `DONE`.

---

## Data files

All files are written to the save folder selected on the Participant page.

### participants_master.csv

One row per session start, for all experiment types.

```
sub_id, group, experiment, session, datetime
```

### participants_behavioral.csv

One row per behavioral session, with all firmware parameters at session start.

```
sub_id, group, session, file, datetime, mode, freq, refAmber, refCyan,
maxA, minA, maxB, minB, trialLength, interTrialWait
```

### participants_grid.csv

One row per grid session, with all firmware parameters at session start.

```
sub_id, group, session, datetime, mode, freq, refAmber, refCyan,
maxA, minA, maxB, minB, nBaselinesStart, nBaselinesEnd,
trialLength, interTrialWait, order
```

### {sub_id}_R{n}.txt (behavioral only)

Space-separated text file, one row per button press, appended in real time.

```
Trial Primary Green
1 1620 980
2 1540 1050
...
```

`Trial` is the trial counter (increments each search). `Primary` is the primary
LED value (Red for RG, Blue for BG) at the moment of the button press.
`Green` is the green secondary LED value at the button press.

---

## Troubleshooting

**Teensy not detected automatically**
- Make sure the firmware is flashed and the Teensy is plugged in via USB.
- On the Connect page, wait for the six auto-detect attempts to finish, then
  select the correct COM port from the dropdown.
- If the COM port does not appear, check Device Manager for the Teensy serial
  device and install PJRC drivers if needed.

**"Verifying firmware..." hangs**
- The app sent `get` but did not receive a `mode=` response within the
  expected window. Confirm the correct firmware (`subjectExperiment`) is
  flashed. Unplug and replug the Teensy, then click Refresh / retry.

**ERR busy displayed in session**
- The firmware was already running when a start command was sent. Click Stop
  first, then Start.

**No data in session file after pressing button**
- Make sure a valid save folder is selected. Check that the folder path is
  accessible and not read-only.
