# Using the GUI

Code: `prototype/gui/`. Python, managed with `uv`. Run on native Windows
(the Teensy connects as a COM port WSL2 can't see without extra setup):

```
cd prototype/gui
uv run main.py
```

The window has four screens: Connect, Participant, Mode/settings, and
Session. You move forward through them; the "Back to experiment selection"
button on the session screen returns you to the Participant screen (see
below) to start another session or switch participant.

## 1. Connecting

On launch, the GUI scans serial ports for a Teensy (matching PJRC's USB
vendor ID) and connects automatically — no action needed if exactly one
Teensy is plugged in. If it can't find one within a few seconds, a port
dropdown and a "Connect" button appear so you can pick one manually.

## 2. Participant and session

Pick a **save folder** (remembered between launches). The folder holds all
data files plus a `participants.csv` database that tracks who has been run
there, in which group, and the stimulator configuration each session used
(mode and the six settings, one column per session). Then either:

- **Existing participant** — pick someone already in this folder's database
  from the dropdown; a new session is added to them.
- **New participant** — enter a **Subject ID** and pick a **Group** from
  `HC, PD, MD, Protan, Deutan, other` (default `HC`). The group is recorded
  once, when the participant is first created.

Click **Continue** to go to the mode/settings screen. Each session is saved
to its own file named `{SubjectID}_R{n}.txt`, where `n` is the next number
that doesn't already exist in the folder, so sessions never overwrite each
other.

## 3. Mode and settings

Once connected, choose:

- **Default** — runs with the firmware's built-in default values.
- **Advanced** — opens a form for the six tunable settings
  (`flickerFrequencyHz`, `amberValue`, `maxRed`, `maxGreen`, `minRed`,
  `minGreen`). The fields are pre-filled with whatever the firmware
  currently reports as active, so they're a starting point to edit, not
  fixed suggestions.

Click **Continue** to send the corresponding `MODE`/`SET` commands and move
to the session screen. See `docs/configure.md` for what each setting does
and how it affects the experiment.

## 4. Running a session

- **Start** — begins a session. On the first Start it creates the session's
  data file (`{SubjectID}_R{n}.txt`) in the save folder and records the
  session in `participants.csv`. The plot's axes are fixed to the resolved
  `minRed`-`maxRed` / `minGreen`-`maxGreen` range; the background is black,
  and a solid yellow round marker tracks the live red/green position as the
  participant turns the knobs.
- Each button press on the device leaves a permanent gray X on the plot at
  that location, and appends a row (Trial, Red, Green) to the table on the
  right. The table is **auto-saved** to the session file on every press, so
  data is never lost if the app closes. Rows accumulate for the whole
  session — they're cleared only when you go Back and start another session.
- A red star on the plot marks the running median of all presses so far, and
  its numeric value is shown as a **Median  Red: x  Green: y** label directly
  under the table (updated on every press).
- **Stop** — ends the session (sends `STOP`). The firmware also lets a
  session run indefinitely through any number of button presses without a
  new Start; see `docs/configure.md`'s pacing section.
- **Save Results...** — optional manual export: writes the current table to a
  `.txt` file of your choosing (same `Trial Red Green` format as the
  auto-saved session file). The auto-save already keeps the session file up
  to date, so this is only for saving an extra copy elsewhere.
- **Back to experiment selection** — only enabled while no session is
  running (before the first Start, or after Stop). Returns to the Participant
  screen, where you can start another session for the same participant, add a
  session for a different one, or create a new participant. The mode/settings
  form is re-populated from a fresh `GET` so it always reflects whatever is
  actually active on the firmware.

## Always-visible configuration line

The bottom of the window always shows the active configuration — mode,
flicker frequency, amber value, and the red/green ranges — as soon as it's
known (right after connecting), and stays visible across every screen.
