# Combined firmware: commands and procedure

Firmware: `prototype/firmware/experimentStimControl/` (Teensy 4.0, Arduino
IDE). Combines the behavioral (knobs) and grid (EEG) experiments in one
sketch; they share the three LEDs, the trigger pin, and one flicker driver.
Only one experiment may be active at a time — starting one while the other
is running is rejected.

Each experiment has its own full, symmetric command set: no bare
`START`/`STOP`/`MODE`/`SET`/`GET` exist anymore (this is a protocol change
from `knobsBehavioral`'s old vocabulary; `gridEEG`'s `GRIDSTART`/`GRIDSTOP`
already used this naming).

## Commands

Connect at 38400 baud. Commands are newline-terminated.

### Behavioral (knobs)

- `BEHAVIORALSTART` - start a session. Rejected with `Grid trial active` if
  a grid run is in progress.
- `BEHAVIORALSTOP` - stop the session and reset.
- `BEHAVIORALMODE DEFAULT` - pin all behavioral settings to compile-time
  defaults; reject `BEHAVIORALSET`. Boot default.
- `BEHAVIORALMODE ADVANCED` - allow `BEHAVIORALSET`.
- `BEHAVIORALSET <name> <value>[, <name> <value>...]` - e.g.
  `BEHAVIORALSET maxRed 2800, amberValue 2200`.
- `BEHAVIORALGET` - print mode and all six behavioral settings.

### Grid (EEG)

- `GRIDSTART [order]` - start a run. `order` (1-4) sets the traversal start
  corner; defaults to the `order` setting if omitted. Rejected with
  `Behavioral trial active` if a behavioral session is in progress.
- `GRIDSTOP` - stop the run and reset.
- `GRIDMODE DEFAULT` / `GRIDMODE ADVANCED` - same semantics as behavioral,
  scoped to grid settings.
- `GRIDSET <name> <value>[, <name> <value>...]` - e.g.
  `GRIDSET trialLengthMs 2500, baselinesStart 3`.
- `GRIDGET` - print mode and all eleven grid settings.

## Settings

Behavioral and grid settings are entirely independent (separate defaults,
separate `BEHAVIORALMODE`/`GRIDMODE`), even where names overlap.

### Behavioral

| Name | Default |
|---|---|
| `flickerFrequencyHz` | 10 |
| `amberValue` | 2400 |
| `maxRed` / `minRed` | 3000 / 0 |
| `maxGreen` / `minGreen` | 2400 / 0 |

### Grid

| Name | Default |
|---|---|
| `flickerFrequencyHz` | 10 |
| `amberValue` | 2400 |
| `minRed` / `maxRed` | 0 / 3200 |
| `minGreen` / `maxGreen` | 0 / 2000 |
| `trialLengthMs` | 3000 |
| `interTrialWaitMs` | 750 |
| `baselinesStart` / `baselinesEnd` | 1 / 1 |
| `order` | 1 |

## Data formats

Both experiments use the same six `@`-separated-integer frame shape, with
different field meanings:

- Behavioral: `TriggerCue@TrialNumber@Amber@Red@Green@Press` (`TriggerCue`
  always 0; `Press` 1 on a button-press result, 0 on the 100 ms live stream).
- Grid: `TriggerCue@StimNumber@Amber@Red@Green@Phase` (`TriggerCue` is the
  real trigger pin state; `Phase` 0=baseline, 1=stimulus, 2=intertrial).

See `docs/configure.md` and `docs/grid-configure.md` for the full per-task
procedure narrative; only the command names differ here (`BEHAVIORAL`-
prefixed instead of bare).
