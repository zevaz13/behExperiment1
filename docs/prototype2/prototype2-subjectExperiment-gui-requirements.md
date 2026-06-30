# subjectExperiment GUI requirements

Requirements for `prototype2/GUI/subjectExperiment/`, the desktop GUI that
controls `prototype2/Firmware/subjectExperiment/`. Modelled after
`prototype/combined_gui/` (see `docs/prototype1/combined-gui-requirements.md`)
with a revised serial protocol, two color modes, and an updated data model.

---

## Overview

The GUI controls a Teensy 4.0 running the subjectExperiment firmware over a
USB serial port (COM port on Windows). It supports two experiment types
(behavioral knob-search and EEG grid) each runnable in two color-pair modes
(Red-Green or Blue-Green). The app must run natively on Windows; the Teensy
enumerates as a COM port that WSL2 cannot see without extra passthrough.

---

## Technology stack

- Python 3.x, managed by `uv`
- PySide6 — UI framework
- pyqtgraph — real-time plotting
- pyserial — serial communication
- No additional dependencies

When developing from WSL/Linux, set `UV_PROJECT_ENVIRONMENT=.venv-linux` to
avoid colliding with the Windows `.venv`.

---

## Path

```
This gui should exist in prototype2/GUIsubjectExp/ If the folder does not exist, create it
---

## Application flow

```
Connect -> Participant -> ExperimentSelect -> ModeConfig -> Session
                              ^                                |
                              |______ Back (re-queries get) __|
```

- **Connect**: auto-detect Teensy by PJRC USB vendor ID `0x16C0`; manual
  port selector fallback. One `SerialLink` per app session. Firmware
  identity confirmed by sending `get` and checking for a parseable multi-line
  key=value response (must contain `mode=` line).
- **Participant**: pick save folder, then select an existing participant from
  `participants_master.csv` or create a new one (Subject ID + Group). Groups:
  HC, PD, MD, Protan, Deutan, other.
- **ExperimentSelect**: four radio choices combining experiment type and color
  mode — `beh-rg`, `beh-bg`, `grid-rg`, `grid-bg`. No default preselected.
  Color scheme updates immediately when the user changes selection.
- **ModeConfig**: Default or Advanced configuration for the chosen
  experiment/color-mode pair. Settings pre-filled by sending `get` and parsing
  the response. Default: sends no parameter changes, starts with current
  firmware state. Advanced: shows a form for all configurable parameters,
  sends them as a batch before starting.
- **Session**: experiment-type-specific screen. Back returns to
  ExperimentSelect (re-sends `get` to refresh settings).

---

## Color modes and theming

The GUI must reflect the active color mode at all times. The color scheme
applies to: page backgrounds or accent borders, plot colors, button highlights,
and status indicators. However, the background of the whole application must be black, like that of prototype.

| Mode | Primary color | Secondary color | Reference |
|------|--------------|-----------------|-----------|
| RG   | Red `#f70404` | Green `#b1ff01` | Amber `#fabd04` |
| BG   | Blue `#0493ff` | Green `#b1ff01` | Cyan `#50fefe` |

Color mode is chosen on ExperimentSelect and stays visible on all subsequent
pages. When the user navigates back to ExperimentSelect, the scheme resets to
neutral until a new choice is made.

---

## Serial protocol

Baud: **38400**. Line terminator: `\n`. All commands are ASCII strings.
Parsing must be case-insensitive.

### Commands: GUI -> Teensy

**Query all parameters** (sent before ModeConfig, and on Back from Session):
```
get
```

**Set a single parameter** (accepted at any time, even while running):
```
freq=<int>
refAmber=<int>
refCyan=<int>
maxA=<int>
minA=<int>
maxB=<int>
minB=<int>
nBaselinesStart=<int>
nBaselinesEnd=<int>
trialLength=<int>
interTrialWait=<int>
order=<int>
```

**Batch set** (semicolon-separated, all accepted in one line):
```
freq=10;maxA=3200;minA=0;refAmber=2400
```

**Apply factory defaults without starting**:
```
defaults-rg
defaults-bg
```

**Start experiment** (rejected while busy with `ERR busy`):
```
beh-rg
beh-bg
grid-rg
grid-bg
```

**Start with factory defaults applied first**:
```
beh-rg-default
beh-bg-default
grid-rg-default
grid-bg-default
```

**Stop** (always accepted, even while idle):
```
stop
```

### Responses: Teensy -> GUI

**Startup confirmation** (appears once on power-on/reconnect):
```
Ready.
```

**Parameter acknowledgment** (one line per parameter set):
```
SET freq=10
SET maxA=3200
```

**Get response** (12 key=value lines + mode line + comment line):
```
freq=10
refAmber=2400
refCyan=0
maxA=3200
minA=0
maxB=2000
minB=0
nBaselinesStart=2
nBaselinesEnd=2
trialLength=3000
interTrialWait=750
order=1
mode=beh-rg
# use defaults-rg / defaults-bg to restore color-pair defaults
```

The `mode` field format is `<beh|grid>-<rg|bg>`. Lines beginning with `#`
are comments; ignore them. The `get` response is complete when a line
starting with `mode=` has been received.

**Start confirmation**:
```
START beh-rg
START beh-bg
START grid-rg
START grid-bg
START beh-rg (defaults)
START beh-bg (defaults)
START grid-rg (defaults)
START grid-bg (defaults)
```

**Defaults applied** (when `defaults-rg`/`defaults-bg` sent without start):
```
DEFAULTS rg applied
DEFAULTS bg applied
```

**Stop confirmation**:
```
Stopped.
```

**Errors**:
```
ERR busy
ERR unknown: <cmd>
ERR unknown param: <tok>
```
Display these in the status bar. `ERR busy` indicates the GUI tried to start
while the firmware was already running — surface the text.

**Behavioral press event** (one line per button press):
```
RESP,Trial:<n>,A:<primaryVal>,B:<greenVal>
```
- `A` = primary channel value (Red in RG, Blue in BG), in [minA, maxA]
- `B` = secondary channel value (Green), in [minB, maxB]
- `n` = trial counter, increments each new search

**Streaming data frame** (every 100 ms while started):
```
&@STIM:<n>,Mode:<RG|BG>,RED:<val>,GREEN:<val>,BLUE:<val>,AMBER:<val>,CYAN:<val>,TRIG:<0|1>%!
```
- Delimiters `&@` and `%!` mark frame boundaries; discard any line not
  matching this structure
- `STIM`: trial counter (1–100 for grid stimuli, 101+ for baselines,
  increments each behavioral trial)
- `Mode`: `RG` or `BG`
- `RED`, `GREEN`, `BLUE`, `AMBER`, `CYAN`: current 12-bit PWM output (0–4095)
- `TRIG`: 1 during active trial (EEG trigger HIGH), 0 during ITI or idle

**Experiment complete**:
```
DONE
```

### Parsing notes

- Parse frames defensively: lines that do not match the `&@...%!` structure
  are silently ignored (firmware may emit status text or error messages at
  any time).
- `RESP` lines and `DONE` are recognized by prefix matching.
- Lines beginning with `SET `, `START `, `DEFAULTS `, `ERR `, `Stopped.`,
  `Ready.`, or `#` are status/control text; display or log as appropriate,
  do not confuse them with data frames.

---

## Configurable parameters reference

All parameters are integers (12-bit ADC/PWM range 0–4095 for values, positive
integers for timing/counts).

| Key | Applies to | Default RG | Default BG | Description |
|-----|-----------|-----------|-----------|-------------|
| `freq` | both | 10 | 10 | Flicker frequency (Hz) |
| `refAmber` | both | 2400 | 500 | Amber reference PWM (Phase B) |
| `refCyan` | both | 0 | 1400 | Cyan reference PWM (Phase B) |
| `maxA` | both | 3200 | 2800 | Primary LED max (Red in RG, Blue in BG) |
| `minA` | both | 0 | 0 | Primary LED min |
| `maxB` | both | 2000 | 2000 | Green (secondary) max |
| `minB` | both | 0 | 0 | Green (secondary) min |
| `nBaselinesStart` | grid | 2 | 2 | Baseline trials before stimuli |
| `nBaselinesEnd` | grid | 2 | 2 | Baseline trials after stimuli |
| `trialLength` | both | 3000 | 3000 | Trial duration (ms) |
| `interTrialWait` | both | 750 | 750 | ITI duration (ms) |
| `order` | grid | 1 | 1 | Grid traversal start corner (1–4) |

ModeConfig Advanced form shows all parameters; for behavioral mode, gray out
`nBaselinesStart`, `nBaselinesEnd`, and `order` (they are irrelevant but
harmless to keep at firmware level).

---

## Pages

### ConnectPage

- On open: scan ports, auto-select first port with PJRC vendor ID `0x16C0`
- If none found: retry every 500 ms up to 6 times, then show dropdown of all
  available ports with a Refresh button
- On connect: send `get`, wait up to 2 s for a `mode=` line response to
  confirm firmware identity
- Show connection status and port name
- Emit `connected(SerialLink)` on success

### ParticipantPage

- Folder picker (persisted in `QSettings`)
- Toggle: Existing participant (dropdown from `participants_master.csv`) vs
  New participant (Subject ID text field + Group combo)
- Validate: reject new participant ID already present in master CSV
- Emit `participant_confirmed(sub_id, group, folder)` on Continue
- Re-reads master CSV on every show event

### ExperimentSelectPage

- Four radio buttons: `beh-rg`, `beh-bg`, `grid-rg`, `grid-bg`
- Labels: "Behavioral — Red/Green", "Behavioral — Blue/Green",
  "Grid (EEG) — Red/Green", "Grid (EEG) — Blue/Green"
- No default preselected
- Changing selection updates the app color scheme immediately
- On Continue: send `get`, collect response, navigate to ModeConfig

### ModeConfig

- Single page parameterized by the chosen `<exp>-<color>` mode
- Header shows the chosen mode string
- Default radio: no parameter changes; the batch send step is skipped
- Advanced radio: shows a form with one spin box per parameter
  - `freq`: 1–100
  - PWM values (`refAmber`, `refCyan`, `maxA`, `minA`, `maxB`, `minB`): 0–4095
  - `nBaselinesStart`, `nBaselinesEnd`: 0–20 (grayed out for behavioral)
  - `trialLength`: 500–30000 ms
  - `interTrialWait`: 0–10000 ms
  - `order`: 1–4 (grayed out for behavioral)
  - Form pre-filled from `get` response values
- On confirm: if Advanced, send a single batch command with all changed
  parameters (`key=value;key2=value2;...`); then send the start command
  (`beh-rg`, `beh-bg`, `grid-rg`, or `grid-bg`)
- Wait for `START ...` confirmation line before navigating to Session
- Emit `session_starting(mode_str, settings)` on confirmed start

### BehavioralSessionPage

- Color scheme: RG palette or BG palette per active mode
- Scatter plot (pyqtgraph, black background):
  - X axis: primary channel (Red in RG, Blue in BG), range [minA, maxA]
  - Y axis: Green (secondary), range [minB, maxB]
  - Axis labels: "Primary LED (A/D)" and "Green LED (A/D)", or the specific
    color name ("Red LED", "Blue LED")
  - Live position marker (circle, primary color): updated on every stream
    frame from the `RED`/`BLUE` and `GREEN` fields
  - Press markers (cross, gray): one per `RESP` event, accumulated
  - Median marker (star, amber/cyan): median of all press coordinates
- Press table: columns Trial, Primary, Green; one row per `RESP` event
- Buttons: Start, Stop, Back, Save
  - Start: sends `beh-rg` or `beh-bg` (matching active mode)
  - Stop: sends `stop`
  - Back: disabled while running; navigates to ExperimentSelect on click
  - Save: re-saves the current session file (auto-save already happens on
    each press; this is a manual trigger)
- Session CSV row written to `participants_behavioral.csv` on first Start press
- Master CSV row also written at that point
- Session data file `{sub_id}_R{n}.txt` written/appended on every press

### GridSessionPage

- Color scheme: RG or BG palette per active mode
- 10×10 stimulus grid (pyqtgraph scatter, black background):
  - Unvisited stimuli: dark gray dots
  - Visited stimuli: primary-color dots (red in RG, blue in BG)
  - Current active stimulus: larger dot, amber/cyan color
  - Grid axes: primary channel level (X) vs Green level (Y)
- Progress bar: 0–(nBaselinesStart + 100 + nBaselinesEnd) trials
- Status label: "Baseline trial", "Stimulus N / 100", "Stopped", "Done"
- Trigger indicator: small LED-style indicator in the status area showing
  TRIG value from the stream frame (on/off)
- Buttons: Start, Stop, Back
  - Start: sends `grid-rg` or `grid-bg`
  - Stop: sends `stop`
  - Back: disabled while running; navigates to ExperimentSelect
- On `DONE` received: progress bar fills to 100 %, Back re-enables, status
  shows "Done"
- Session CSV row written to `participants_grid.csv` and master CSV on Start

---

## Data model and storage

Three CSV files per save folder. All appended, never overwritten. New files
get headers on first write.

**`participants_master.csv`**
```
sub_id, group, experiment, session, datetime
```
- `experiment`: `behavioral` or `grid`
- `session`: session number for that experiment type for that subject
- Written at session start for both experiment types
- Read by ParticipantPage to list existing participants

**`participants_behavioral.csv`**
```
sub_id, group, session, file, datetime, mode, freq, refAmber, refCyan,
maxA, minA, maxB, minB, trialLength, interTrialWait
```
- `mode`: `beh-rg` or `beh-bg`
- `file`: basename of the session data file

**`participants_grid.csv`**
```
sub_id, group, session, datetime, mode, freq, refAmber, refCyan,
maxA, minA, maxB, minB, nBaselinesStart, nBaselinesEnd, trialLength,
interTrialWait, order
```
- No `file` column; EEG recording captures the actual trial data

**Session data file** (behavioral only): `{sub_id}_R{n}.txt`
- Written to the save folder
- Header: `Trial Primary Green`
- One row per `RESP` event: space-separated trial number, primary value, green value
- Appended incrementally on each press (streaming append, not full rewrite)

Session number `n` is the next unused integer for that subject and experiment
type, determined by scanning the per-experiment CSV for existing session rows.

---

## Module layout

```
prototype2/GUI/subjectExperiment/
  pyproject.toml         (uv project; deps: pyside6, pyqtgraph, pyserial)
  main.py                (entry point)
  serial_link.py         (QThread serial reader; identical pattern to prototype1)
  protocol.py            (frame parsing, GET response parsing, command builders)
  participants.py        (3-CSV scheme, session numbering)
  main_window.py         (all pages in QStackedWidget, MainWindow coordinator)
```

### `serial_link.py`

`QThread` subclass with a `line_received(str)` signal. Reads lines in `run()`,
emits each to the Qt main thread. Writes are done from the main thread via
`write(bytes)` — pyserial allows one reader thread + writes elsewhere.

### `protocol.py`

- `parse_get_response(lines: list[str]) -> dict[str, str]`: collects key=value
  pairs until `mode=` is seen; returns a dict including `mode`
- `parse_stream_frame(line: str) -> dict | None`: returns parsed fields if
  line matches `&@...%!` structure, else None
- `parse_resp(line: str) -> tuple[int, int, int] | None`: returns (trial, A, B)
  if line matches `RESP,...` pattern, else None
- `build_batch_command(params: dict[str, int]) -> str`: returns
  `key=val;key2=val2` string

No dataclasses required; plain dicts are sufficient given the small parameter
count.

### `participants.py`

- `record_session(folder, sub_id, group, exp_type, session_n, settings, file=None)`
  — writes to master CSV and the appropriate per-experiment CSV
- `next_session_number(folder, sub_id, exp_type) -> int`
  — scans per-experiment CSV, returns first unused integer >= 1
- `list_participants(folder) -> list[str]`
  — reads master CSV, returns sorted unique sub_ids

### `main_window.py`

- `ConnectPage`, `ParticipantPage`, `ExperimentSelectPage`, `ModeConfig`,
  `BehavioralSessionPage`, `GridSessionPage` — one class per page
- `MainWindow`: hosts all pages in `QStackedWidget`; manages `SerialLink`
  instance and cross-page state (`sub_id`, `group`, `folder`, `active_mode`,
  `settings`)
- Color scheme applied via a `set_color_mode(mode: str)` method on
  MainWindow that updates stylesheet accent variables on all pages

---

## Differences from prototype1 combined GUI

| Aspect | Prototype 1 | Prototype 2 |
|--------|-------------|-------------|
| Start commands | `BEHAVIORALSTART`, `GRIDSTART` | `beh-rg`, `beh-bg`, `grid-rg`, `grid-bg` |
| Stop command | `BEHAVIORALSTOP`, `GRIDSTOP` | `stop` |
| Query command | `BEHAVIORALGET`, `GRIDGET` | `get` |
| Set commands | `BEHAVIORALSET key val, ...` | `key=value;key2=val2;...` |
| GET response format | single space-separated line | multi-line key=value |
| Stream frame format | `0@3@2400@1420@980@0` | `&@STIM:3,Mode:RG,...%!` |
| Press events | embedded in stream (Press field = 1) | separate `RESP,Trial:n,A:v,B:v` line |
| Color modes | Red-Green only | RG and BG (Blue-Green) |
| Completion signal | `GRID DONE` | `DONE` |
| Experiment select | 2 choices (Behavioral/Grid) | 4 choices (type x color pair) |
| UI color theming | none | changes with RG/BG mode |
| Parameter names | `flickerFrequencyHz`, `amberValue` | `freq`, `refAmber` |

---

## Verification

Offline pass: fake `SerialLink` under `QT_QPA_PLATFORM=offscreen` covering:
- Both experiment types × both color modes
- Default and Advanced mode config paths
- Back-to-ExperimentSelect re-entry and settings refresh
- All three CSVs written correctly
- Press accumulation and session file append (behavioral)
- Grid progress bar reaching 100 % on `DONE`

Hardware pass on native Windows once offscreen pass is clean.
