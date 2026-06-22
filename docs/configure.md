# Configuring and running the knobs behavioral experiment

Firmware: `prototype/firmware/knobsBehavioral/`. Serial: 38400 baud, line-based
commands (`\n`-terminated), case-sensitive.

## Default vs Advanced mode

The firmware boots in **Default mode**: flicker frequency, amber reference,
and max/min red/green are pinned to the built-in defaults in `config.h`, and
any `SET` command is rejected.

**Advanced mode** lets a connected application override those values for the
current session.

| Command | Effect |
|---|---|
| `MODE DEFAULT` | Reset all settings to the `config.h` defaults; reject `SET`. |
| `MODE ADVANCED` | Keep current setting values; allow `SET` to change them. |

Switching `MODE DEFAULT` → `MODE ADVANCED` does not change any values by
itself — it only unlocks `SET`. Switching back to `MODE DEFAULT` always
resets every setting to its default, even if it was changed in Advanced mode.

## Setting variables

In Advanced mode, send one `SET <name> <value>` command per variable:

```
SET maxRed 2800
SET minGreen 0
SET flickerFrequencyHz 12
```

| Name | Default | Meaning |
|---|---|---|
| `flickerFrequencyHz` | 10 | Square-wave frequency for the RED+GREEN / AMBER alternation. Takes effect on the next `START`. |
| `amberValue` | 2400 | Fixed PWM value (0-4095) for the amber/yellow reference. |
| `maxRed` | 3000 | Upper bound of the red knob's PWM output range. |
| `maxGreen` | 2400 | Upper bound of the green knob's PWM output range. |
| `minRed` | 0 | Lower bound of the red knob's PWM output range. |
| `minGreen` | 0 | Lower bound of the green knob's PWM output range. |

`maxRed`/`minRed`/`maxGreen`/`minGreen` changes apply on the next knob sample
(roughly every 50 ms, even mid-trial). `flickerFrequencyHz` and `amberValue`
apply the next time a trial starts.

The firmware replies to every command on a single line, e.g. `OK maxRed=2800`,
`SET requires MODE ADVANCED`, or `Unknown setting: foo`.

## Experimental procedure / pipeline

1. Connect to the Teensy at 38400 baud. It prints a ready message on boot.
2. Optionally configure the session: `MODE ADVANCED`, then any `SET`
   commands. Skip this to run with defaults.
3. Send `START` to begin a trial:
   - The knob-to-brightness offset is re-randomized (so the dial position
     can't be learned across trials).
   - The amber LED flickers at the fixed reference value; red/green flicker
     at whatever the knobs currently read, mapped into `[minRed, maxRed]` /
     `[minGreen, maxGreen]`.
   - Every 100 ms, the firmware streams a live telemetry line (see Data
     format below, `Press=0`) for real-time plotting.
4. The participant turns the knobs until red+green+amber reads as a single
   solid color (no flicker), then presses the button.
5. On button press, the firmware sends one final line with `Press=1` (the
   trial's logged result) and stops the trial automatically. No `STOP` is
   needed in this case.
6. To abort a trial without a button press, send `STOP`.
7. Repeat from step 3 for the next trial.

## Data format

Every data line (telemetry and final result) is six `@`-separated fields,
matching the GUI's log header:

```
TriggerCue@TrialNumber@Amber@red@green@Press
```

`TriggerCue` and `TrialNumber` are always `0` (unused in this experiment).
`Press` is `0` for live telemetry and `1` for the final button-press result.
