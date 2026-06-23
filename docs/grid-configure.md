# Grid (EEG) experiment: commands and procedure

Firmware: `prototype/firmware/gridEEG/` (Teensy 4.0, Arduino IDE). Unlike the
behavioral knobs task, the grid experiment presents stimuli automatically for
EEG recording: it steps through a 10x10 grid of red/green combinations,
flickering each against amber at the configured frequency, and pulses the
trigger pin HIGH for the duration of every trial for EEG synchronization. The
participant does nothing.

A run is: `baselinesStart` amber-only baseline trials, then the 100 grid
stimuli, then `baselinesEnd` amber-only baseline trials. Each trial is an
active phase (`trialLengthMs`, trigger HIGH) followed by an intertrial wait
(`interTrialWaitMs`, all LEDs off, trigger LOW). The run ends automatically and
prints `GRID DONE`.

## Commands

Connect at 38400 baud. Commands are newline-terminated.

- `GRIDSTART [order]` - start a run. `order` (1-4) sets the traversal start
  corner; if omitted, the `order` setting is used (default 1). The argument
  overrides the setting for this run only, without changing it.
- `GRIDSTOP` - stop the run and reset.
- `MODE DEFAULT` - pin all settings to the compile-time defaults; reject `SET`.
  This is the boot default.
- `MODE ADVANCED` - allow `SET`.
- `SET <name> <value>[, <name> <value>...]` - change one or more settings
  (Advanced mode only), e.g. `SET trialLengthMs 2500, baselinesStart 3`.
- `GET` - print the mode and all settings on one line.

The start/stop verbs are deliberately distinct from the behavioral firmware's
`START`/`STOP`, so a future combined firmware can't confuse the two.

## Settings

| Name | Default | Meaning |
|---|---|---|
| `flickerFrequencyHz` | 10 | Flicker frequency (0 = no flicker, all channels steady). |
| `amberValue` | 2400 | Amber reference PWM value. |
| `minRed` / `maxRed` | 0 / 3200 | Red range; the 10 grid columns are spaced across it. |
| `minGreen` / `maxGreen` | 0 / 2000 | Green range; the 10 grid rows are spaced across it. |
| `trialLengthMs` | 3000 | Active duration of each trial. |
| `interTrialWaitMs` | 750 | Gap between trials. |
| `baselinesStart` | 1 | Amber-only baseline trials before the grid. |
| `baselinesEnd` | 1 | Amber-only baseline trials after the grid. |
| `order` | 1 | Default start corner (1-4) when `GRIDSTART` has no argument. |

The grid resolution (10x10 = 100 stimuli) is a compile-time constant, since the
sequence arrays are statically sized.

`order` corners: 1 -> (minRed, minGreen), 2 -> (minRed, maxGreen),
3 -> (maxRed, minGreen), 4 -> (maxRed, maxGreen).

## Procedure

1. Connect; the board prints a ready message.
2. Optionally `MODE ADVANCED` then `SET ...`; `GET` to confirm. Skip to use the
   defaults.
3. `GRIDSTART` (or `GRIDSTART 3` to pick a start corner). The run proceeds
   automatically through baselines and the grid, streaming a data frame at each
   trial onset and offset, and prints `GRID DONE` when finished.
4. `GRIDSTOP` aborts at any time.

## Data format

Each frame is six `@`-separated integers (same shape as the behavioral
firmware's frame, so a shared GUI parser can read both):

```
TriggerCue@StimNumber@Amber@Red@Green@Phase
```

- `TriggerCue` - EEG trigger pin state: 1 during a trial, 0 in the intertrial gap.
- `StimNumber` - grid stimulus index 1..100, or 0 for a baseline trial.
- `Amber`, `Red`, `Green` - the PWM values active for that trial.
- `Phase` - 0 = baseline, 1 = grid stimulus, 2 = intertrial.

One frame is sent at each trial onset (TriggerCue 1) and one at each offset
(TriggerCue 0).
