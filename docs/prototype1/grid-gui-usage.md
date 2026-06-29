# Using the grid GUI

Code: `prototype/grid_gui/`. Python, managed with `uv`. Run on native Windows
(the Teensy connects as a COM port WSL2 can't see without extra setup):

```
cd prototype/grid_gui
uv run main.py
```

The `.venv` here is OS-specific. If you also run this from WSL/Linux against
the same checkout, set `UV_PROJECT_ENVIRONMENT=.venv-linux` there so it doesn't
collide with the Windows `.venv` (same as the behavioral GUI).

This GUI is a monitor/controller for the grid (EEG) experiment: it configures
and runs the firmware and shows the stimulus grid filling in live. It does not
save any data - the experiment's data is the EEG recording, synchronized by the
firmware's trigger pulses.

The window has four screens: Connect, Participant, Mode/settings, Session. The
"Back to experiment selection" button on the session screen returns to the
Participant screen.

## 1. Connecting

On launch the GUI scans for a Teensy by USB vendor ID and connects
automatically; if it can't find one within a few seconds, a port dropdown and
a Connect button appear for manual selection.

## 2. Participant

Enter a Subject ID and pick a Group (`HC, PD, MD, Protan, Deutan, other`,
default `HC`). This is shown during the run for reference but not saved.

## 3. Mode and settings

- **Default** - run with the firmware's built-in defaults.
- **Advanced** - a form for the eleven settings (`flickerFrequencyHz`,
  `amberValue`, `minRed`, `maxRed`, `minGreen`, `maxGreen`, `trialLengthMs`,
  `interTrialWaitMs`, `baselinesStart`, `baselinesEnd`, `order`), pre-filled
  from the firmware's current values. `order` (1-4) is the grid start corner.

Click **Continue** to send the corresponding `MODE`/`SET` commands and go to
the session screen. See `docs/grid-configure.md` for what each setting does.

## 4. Running

The active configuration (and the participant) is shown at the top of the
screen.

- **Start** - sends `GRIDSTART`. The run proceeds automatically through the
  start baselines, the 100 grid stimuli, and the end baselines.
- The plot shows the 10x10 grid of stimulus coordinates (red on x, green on y,
  axes fixed to the configured min/max ranges). Each point starts dim; as its
  stimulus is presented it turns bold yellow, and the stimulus currently on
  screen is highlighted in red. Baseline trials don't correspond to a grid
  point, so they don't change the plot.
- The **progress bar** fills across every trial (baselines included) until the
  run finishes; the firmware's `GRID DONE` marks it complete.
- **Stop** - sends `GRIDSTOP` and ends the run.
- **Back to experiment selection** - only enabled while no run is in progress;
  returns to the Participant screen.
