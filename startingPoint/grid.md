# Grid (EEG) experiment firmware: review and modular change plan

Covers `startingPoint/eegEXP_grid_fixed/eegEXP_grid_fixed.ino` (reference,
untouched) and the plan to rebuild it as a modular firmware mirroring
`prototype/firmware/knobsBehavioral/`. This was milestone 3.1 (analysis + plan).

> Implemented in milestone 3.2: the modular firmware now lives in
> `prototype/firmware/gridEEG/`, with `GRIDSTART [order]`/`GRIDSTOP`, the eleven
> configurable settings, and the 6-field data stream described below. User-facing
> reference: `docs/grid-configure.md`. Open questions below were resolved with
> the user (self-contained directory, `GRIDSTART`/`GRIDSTOP`, reuse the
> behavioral frame, `order` as a setting with a `GRIDSTART <order>` override).

## What the grid experiment is

Unlike the behavioral "knobs" task, where the participant turns knobs to find a
metamer, the grid experiment **presents stimuli automatically** for EEG
recording. The participant does nothing; the firmware steps through a fixed
grid of red/green combinations, flickering each against amber at 10 Hz while a
trigger pin pulses for EEG synchronization.

- A 10x10 grid (`NUM_STEPS = 10`, `NUM_STIMS = 100`) of linearly spaced red
  (`0..3200`) and green (`0..2000`) values.
- Each of the 100 stimuli is shown for `trialLength` (3000 ms) with
  `interTrialWait` (750 ms) between, preceded and followed by `numBaselineTr`
  amber-only baseline trials.
- `digitalWrite(trigger, HIGH)` for the duration of every trial marks it for
  the EEG amplifier.

## How the current firmware works

- **Pins**: button 20, amber 0, red 3, green 1, trigger 13, `AIred` 19,
  `AIgreen` 22. These are *identical* to the behavioral PCB pins (there
  `AIred`/`AIgreen` are the red/green knob inputs). The grid uses neither the
  button nor the analog inputs.
- **Sequence generation**:
  - `getLinSpacedArrays()` fills `redArray[10]`/`greenArray[10]` with linearly
    spaced values.
  - `produceSequence()` walks the 100 grid cells in a diagonal/zigzag order.
  - `modSeqOrder(order)` flips X and/or Y so the sequence starts from one of
    the 4 corners (`order` 1-4) for counterbalancing.
  - `getExpSequence(order)` maps each grid cell to actual red/green values into
    `expSequence[100][2]`.
- **Presentation** (`blink_red_green`): runs start baselines, then for each of
  the 100 stimuli sets red/green, turns the flicker timers on, pulses the
  trigger, busy-waits `trialLength`, drops the trigger, then `threads.delay`s
  the intertrial wait; finally runs end baselines and resets.
- **Flicker**: three independent `IntervalTimer`s (`timerAmber`, `timerRed`,
  `timerGreen`), each toggling its LED every half period (50 ms -> 10 Hz).
- **Threading**: a `TeensyThreads` thread (`amber_red_green`) waits on a
  `started` flag and dispatches on `mode`; `loop()` parses serial.
- **Protocol** (two-step): send `grid` (or `fixed`), then a parameter line
  `@order!` (or `reps@RED!green`); `stop` ends it. Uses `@`/`!` delimiters and
  prints human-prompt strings.
- **Modes**: `mode 1` = grid (above); `mode 2` = "fixed" (a constant red/green
  repeated `numValsLW` times); `mode 0` = off.

## Problems (it mirrors the pre-rewrite behavioral firmware)

1. **Three independent flicker timers** drift relative to each other, so
   RED+GREEN and AMBER are not reliably out of phase. This is the same bug
   fixed in the behavioral firmware with a single-timer ISR.
2. **A second "fixed" experiment** (`mode 2`) is bundled in. Out of scope: only
   the grid should remain.
3. **Blocking presentation**: busy-wait loops plus `threads.delay` for the
   intertrial wait, which is why it needs `TeensyThreads` at all.
4. **Clunky protocol**: two-step `grid`/`@order!` with `@`/`!` delimiters and
   prompt strings, unlike the behavioral `START`/`STOP`/`SET`/`MODE`/`GET`.
5. **Dead code**: `Bounce2` button (attached, never read), `AIred`/`AIgreen`
   (never read), `pressFlag` (never set), `~~~` end-of-frame sentinel,
   `SERIAL_FREQ`, `outputValue*`, `initialOffset*`.
6. **Baseline off-by-one**: `for (ri = 0; ri <= reps; ri++)` runs `reps + 1`
   baselines.
7. **One baseline count** (`numBaselineTr`) for both ends; CLAUDE.md wants
   separate start/end counts.
8. **No machine-readable data stream**: only human-readable debug prints; the
   serial-send thread is commented out. The variables for a dataframe exist
   (`trigFlag`, `trCnt`, `current*Tri`) but nothing streams them.

## Proposed modular firmware

New directory `prototype/firmware/gridEEG/`, mirroring `knobsBehavioral/`:

| Behavioral module | Grid equivalent | Notes |
|---|---|---|
| `pins.h` | `pins.h` | Identical pin values; drop the button/analog-input aliases the grid doesn't use. |
| `config.h` | `config.h` | Compile-time defaults for the grid settings below. |
| `settings.{h,cpp}` | `settings.{h,cpp}` | Runtime settings + Default/Advanced mode, same `SET`/`GET` design. |
| `flicker.{h,cpp}` | `flicker.{h,cpp}` | Reuse the single-timer ISR (RED+GREEN vs AMBER strictly out of phase); add an amber-only mode for baselines. |
| `knobs.{h,cpp}` | `sequence.{h,cpp}` | The grid has no knobs; instead this builds the 100-stimulus sequence (linspace -> diagonal order -> corner remap -> red/green values). |
| `trial.{h,cpp}` | `trial.{h,cpp}` | Non-blocking `millis()` state machine (see below) replacing the busy-wait + `threads.delay`. |
| `dataframe.{h,cpp}` | `dataframe.{h,cpp}` | One serial log line per event, parser-compatible with the behavioral frame. |
| `telemetry.{h,cpp}` | (optional) | Per-stimulus frames may be enough; a periodic stream can be added if the grid GUI needs it. |
| `serial_commands.{h,cpp}` | `serial_commands.{h,cpp}` | Improved command set (below). |
| `knobsBehavioral.ino` | `gridEEG.ino` | Setup/loop wiring. |

### Drop TeensyThreads

The behavioral firmware needs a thread only because it samples the ADC
continuously. The grid reads no inputs, so the presentation can be a
non-blocking state machine polled from `loop()`, with the flicker on an
`IntervalTimer`. Proposed states:

```
Idle -> BaselineStart(n) -> GridStim(i) -> ... -> BaselineEnd(n) -> Done -> Idle
```

Each trial has an active phase (`trialLengthMs`, trigger HIGH, flicker on) and
an intertrial phase (`interTrialWaitMs`, trigger LOW, LEDs off); `trialPoll()`
advances on `millis()` like the behavioral `Acknowledging`/`OnBreak` states.

### Configurable settings (`SET <name> <value>`, `GET`, `MODE`)

Mirrors the behavioral settings module and naming:

`flickerFrequencyHz`, `amberValue`, `minRed`, `maxRed`, `minGreen`, `maxGreen`,
`trialLengthMs`, `interTrialWaitMs`, `baselinesStart`, `baselinesEnd`.

`NUM_STEPS` (grid resolution, 100 = 10x10) stays a compile-time constant for
now, since the sequence arrays are statically sized; making it a runtime
setting would need dynamic allocation and is not in the CLAUDE.md list.

### Improved commands (distinct from the behavioral ones)

Per CLAUDE.md, the grid's start/stop should differ from the behavioral
`START`/`STOP` so a future combined firmware can't confuse them:

- `GRIDSTART <order>` - start the grid with corner `order` 1-4 (default 1).
- `GRIDSTOP` - stop and reset.
- `SET ... , GET, MODE DEFAULT|ADVANCED` - same syntax/behavior as behavioral,
  so the configuration UX is shared.

`order` is a per-run argument (counterbalancing) rather than a stored setting.

### Data stream

Reuse the behavioral 6-field frame shape so the GUI parser can be shared, with
the grid's meanings: `TriggerCue, StimNumber, Amber, Red, Green, Phase`, where
`TriggerCue` is the EEG trigger state (0/1) and `Phase` encodes
baseline/grid/intertrial. One frame at each trial onset and offset; a periodic
stream can be added later if needed. (Final format is an open question below.)

### Removed entirely

The "fixed" mode and its parameters (`constantRed/Green`, `numValsLW`), the
two-step `grid`/`@order!` parsing and prompt strings, and all dead code listed
above.

## Open questions for the implementation milestone

- Command names: `GRIDSTART <order>` / `GRIDSTOP` acceptable, or different
  verbs?
- Should `order` be a `GRIDSTART` argument (proposed) or a stored `SET`
  setting?
- Data stream: include the per-stimulus dataframe now (recommended for the
  future grid GUI), or defer until the grid GUI requirements are defined?
- Final dataframe field meanings (the `Phase`/`TriggerCue` mapping above).
- Share `pins.h`/`flicker.*` with the behavioral firmware now, or duplicate
  until the later "combine firmware" milestone?
- Directory name `gridEEG/` ok?
