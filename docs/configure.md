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

`START` always runs with whatever values are currently active, regardless of
mode. There is no separate "run with my configured values" command — set up
`MODE ADVANCED` + `SET ...` once, then every `START` after that (across as
many trials as you like) keeps using those values until you either change
them again or send `MODE DEFAULT`.

## Setting variables

In Advanced mode, send a `SET <name> <value>` command. Multiple settings can
be combined on one line, comma-separated:

```
SET maxRed 2800
SET minGreen 0
SET flickerFrequencyHz 20, amberValue 500
```

| Name | Default | Meaning |
|---|---|---|
| `flickerFrequencyHz` | 10 | Square-wave frequency for the RED+GREEN / AMBER alternation. `0` disables flicker entirely (see below). Takes effect on the next `START`. |
| `amberValue` | 2400 | Fixed PWM value (0-4095) for the amber/yellow reference. |
| `maxRed` | 3000 | Upper bound of the red knob's PWM output range. |
| `maxGreen` | 2400 | Upper bound of the green knob's PWM output range. |
| `minRed` | 0 | Lower bound of the red knob's PWM output range. |
| `minGreen` | 0 | Lower bound of the green knob's PWM output range. |

`maxRed`/`minRed`/`maxGreen`/`minGreen` changes apply on the next knob sample
(roughly every 50 ms, even mid-trial). `flickerFrequencyHz` and `amberValue`
apply the next time a trial starts.

The firmware replies to each assignment on its own line, e.g. `OK
maxRed=2800`, `SET requires MODE ADVANCED`, or `Unknown setting: foo`.

### `flickerFrequencyHz 0`: disabling flicker

Setting the flicker frequency to `0` stops the RED+GREEN / AMBER alternation.
All three channels are shown at once, continuously, at their current values
— useful for checking the raw color mix without the flicker illusion.

### Reading back the current configuration

Send `GET` at any time (including mid-trial) to print the active mode and all
six setting values on one line, e.g.:

```
mode=ADVANCED flickerFrequencyHz=20 amberValue=500 maxRed=2800 maxGreen=2400 minRed=0 minGreen=0
```

## Experimental procedure / pipeline

1. Connect to the Teensy at 38400 baud. It prints a ready message on boot.
2. Optionally configure the session: `MODE ADVANCED`, then any `SET`
   commands. Skip this to run with the `config.h` defaults. Send `GET` to
   confirm what's active before starting.
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
7. Repeat from step 3 for the next trial — the same configuration carries
   over automatically; no need to re-send `SET` between trials.

## Data format

Every data line (telemetry and final result) is six `@`-separated fields,
matching the GUI's log header:

```
TriggerCue@TrialNumber@Amber@red@green@Press
```

`TriggerCue` and `TrialNumber` are always `0` (unused in this experiment).
`Press` is `0` for live telemetry and `1` for the final button-press result.
