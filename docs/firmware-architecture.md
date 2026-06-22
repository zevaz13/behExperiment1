# Firmware architecture: knobsBehavioral

Location: `prototype/firmware/knobsBehavioral/`. Target: Teensy 4.0, built with
the Arduino IDE + Teensyduino. For the serial command reference and the
experimental procedure, see `docs/configure.md`. This document covers the
internal module structure instead.

## Why this exists

The original firmware (`startingPoint/knobsExperimentTeensy/knobsExperimentTeensy.ino`)
was a single ~512-line `.ino` implementing seven experiment "modes" behind a
numeric `mode` variable, of which only one (`mode == 2`, the knobs/variable-
resistor behavioral task) was actually finished — the rest were `Serial.println("boing")`
stubs. `knobsBehavioral` is a from-scratch rewrite of that one working mode,
split into focused modules, with the unfinished modes dropped entirely (see
`docs/configure.md`'s sibling `PLAN.md` for the full history of why each
change was made).

## Required libraries

- `TeensyThreads` (cooperative threads on Teensy) — used for knob sampling.
- `IntervalTimer` — part of the Teensy core, no separate install.
- No `Bounce2`: the legacy code depended on it but never actually queried it
  (button edges were handled by a raw hardware interrupt the whole time), so
  it was dropped as dead weight.

## Module map

```
pins.h              PCB pin assignments (compile-time constants)
config.h            Compile-time defaults for every tunable parameter
settings.{h,cpp}     Runtime-configurable values + Default/Advanced mode
flicker.{h,cpp}      Drives the 3 LEDs (timer-based alternation, blink, steady)
knobs.{h,cpp}        ADC sampling, smoothing, deadband, anchored offset
trial.{h,cpp}        Session/search state machine, button handling
dataframe.{h,cpp}    Shared serial log-line formatting
telemetry.{h,cpp}    100 ms live-data stream
serial_commands.{h,cpp}  Parses START/STOP/MODE/SET/GET
knobsBehavioral.ino  setup()/loop() wiring only
```

Dependency direction (who includes whom): `trial` and `telemetry` are the
two "orchestrator" modules — they pull together `flicker`, `knobs`,
`settings`, and `dataframe`. `knobs` depends on `trial` only for
`trialIsSearching()` (so it knows when to sample). `flicker` and `settings`
have no dependencies on the others. There are no circular includes.

### `pins.h`

Pin numbers are fixed by the custom PCB and must not be changed without
updating the board itself:

| Constant | Pin | Purpose |
|---|---|---|
| `kButtonPin` | 20 | Participant's response button (interrupt, `INPUT_PULLUP`, `FALLING`) |
| `kAmberPin` | 0 | Amber/yellow reference LED (PWM) |
| `kRedPin` | 3 | Red LED (PWM) |
| `kGreenPin` | 1 | Green LED (PWM) |
| `kTriggerPin` | 13 | Wired on the PCB; configured as `OUTPUT` but purpose undocumented — preserved as-is |
| `kRedKnobPin` | 19 | Red knob potentiometer (analog in) |
| `kGreenKnobPin` | 22 | Green knob potentiometer (analog in) |

### `config.h`

Every constant a future maintainer might want to tune lives here, grouped
by the module that uses it. Two categories:

1. **Defaults for runtime-configurable settings** (`kFlickerFrequencyHz`,
   `kAmberValue`, `kMaxRed`, `kMaxGreen`, `kMinRed`, `kMinGreen`) — these
   seed `settings.cpp` and are restored whenever `MODE DEFAULT` is sent.
2. **Fixed firmware behavior** that isn't exposed over serial: ADC/PWM
   resolution, knob smoothing window (`kNumSamples` x `kSampleIntervalMs` ≈
   50 ms), button debounce, telemetry interval (100 ms), the acknowledge
   blink (3 blinks, 80 ms per phase) and break duration (2 s), the random
   walk jump range (`kWalkJumpMin`/`kWalkJumpMax` = 500-1500), and the
   deadband threshold (25 units).

### `settings.{h,cpp}`

Holds the six runtime-configurable values plus the current `Mode`
(`Default` or `Advanced`):

- **Default mode** (boot default): values are pinned to the `config.h`
  constants; `settingsTrySet()` always returns `false`.
- **Advanced mode**: `settingsTrySet(name, value)` mutates the matching
  value immediately and returns `true`; unknown names return `false`.
- Switching to `Default` via `settingsSetMode()` resets every value back to
  the `config.h` defaults, even if it was customized in Advanced mode.
  Switching to `Advanced` only unlocks `SET` — it does not change any
  values by itself.

Every other module reads these through getters (`settingsMaxRed()`, etc.)
instead of touching `config.h` constants directly, so a value can change
mid-session and take effect on the next read.

### `flicker.{h,cpp}`

Owns the three LED outputs and the single hardware timer that alternates
between them. Public API:

- `flickerInit()` — pin modes + PWM resolution. Call once in `setup()`.
- `flickerStart(red, green, amber)` — sets the three channel values and
  either starts the alternating timer (if `settingsFlickerFrequencyHz() >
  0`) or writes all three continuously ("steady state", see below).
- `flickerSetRedGreen(red, green)` — live update during a search; if
  currently in steady state, also re-writes the pins immediately (otherwise
  the next timer tick picks it up).
- `flickerFreeze()` — stops the alternating timer but leaves the last
  values in place (used right after a button press, before blinking).
- `flickerSetAllOn(on)` — writes all three channels at once, either their
  last values or off. Used for both the acknowledge blink and the break's
  "all off".
- `flickerStop()` — full stop: ends the timer and zeroes everything
  (session `STOP`).

**Why one timer instead of three:** an earlier version used three
independent `IntervalTimer`s (one per channel), each toggling on its own
half-period. On real hardware this let RED+GREEN and AMBER overlap (both on,
or both off, during parts of the cycle) because the three timers drift
relative to each other. The current version uses a single timer whose ISR
flips one `redGreenPhase` flag and writes all three channels together each
tick, so RED+GREEN and AMBER are always strictly exclusive by construction.

**`flickerFrequencyHz == 0`** is a special case ("steady state"): no timer
runs at all: RED, GREEN, and AMBER are all written continuously at their
current values, with no alternation. Useful for inspecting the raw color
mix without the flicker illusion.

### `knobs.{h,cpp}`

Samples the two knob potentiometers and turns raw ADC readings into the
red/green values that drive the flicker.

- `knobsInit()` — sets ADC resolution. Call once in `setup()`.
- `knobsCurrentRed()` / `knobsCurrentGreen()` — last computed values.
- `knobsAnchorTo(targetRed, targetGreen)` — see below.
- `knobsThreadLoop()` — runs forever on its own `TeensyThreads` thread
  (added in `setup()`); only does work while `trialIsSearching()` is true,
  otherwise yields.

**Sampling**: each iteration averages `kNumSamples` (10) readings spaced
`kSampleIntervalMs` (5 ms) apart — a ~50 ms smoothing window, matching the
original spec.

**Offset and anchoring**: the firmware deliberately decouples the knob's
physical position from the displayed value, so a participant can't memorize
"knob position X = output Y" across searches. This is done with a per-axis
integer `redOffset`/`greenOffset` added to the raw ADC reading before
mapping:

```
mapped = map(wrap(rawADC + offset), 0, 4095, minOut, maxOut)
```

`knobsAnchorTo(targetRed, targetGreen)` computes the offset needed so that,
given the knob's *current* physical position, the very first post-anchor
sample maps exactly to `(targetRed, targetGreen)` — it samples the raw ADC
once, inverse-maps the target back into raw ADC units (`rawFromMapped()`,
guarded against `maxOut <= minOut` to avoid a division by zero if `SET`
ever makes `minRed == maxRed`), and sets `offset = rawTarget - rawNow`.
`trial.cpp` calls this once per search with a deliberately chosen target
(see Search lifecycle below) — this replaced an earlier, simpler mechanism
that just drew the offset from `random(0, max)` independent of any target,
which couldn't anchor to a specific starting point.

Because the anchor's offset can now be negative (target below current
position) as well as positive, `wrapToAdcRange()` was changed from the
legacy single-direction "subtract 4095 if over" to true modulo-4096
arithmetic, so it wraps correctly in both directions.

**Deadband**: after mapping, `applyDeadband()` snaps any value under
`kDeadbandThreshold` (25) to exactly 0, to suppress ADC noise jitter when
the true value is at or near the bottom of the range.

### `trial.{h,cpp}`

The orchestrator: owns the session/search state machine and the button
interrupt handler.

States: `Idle`, `Searching`, `Acknowledging`, `OnBreak`.

```
        START                                button press
Idle ----------> Searching -------------------------------------> Acknowledging
                     ^                                                  |
                     |                                    (blink done)  |
                     |                                                  v
                     +-------------------- beginNextSearch() <----- OnBreak
                                            (2s elapsed)

STOP (from any non-Idle state) -> Idle
```

- **Searching**: knobs drive the flicker; live telemetry streams every
  100 ms; the button is armed.
- A button press (debounced, `kButtonDebounceMs` = 250 ms, and only acted
  on while `Searching`) captures the current red/green as `lastPress*`,
  sends the result frame (`Press=1`), freezes the flicker, and enters
  **Acknowledging**.
- **Acknowledging**: all three LEDs blink together. `kAcknowledgeBlinkCount`
  (3) blinks are driven by toggling `2*count - 1` times (an odd number, so
  the sequence ends naturally on "off" instead of being cut short by the
  break's "all off" — using `2*count` would waste the final toggle).
  `trialPoll()`, called every `loop()` iteration, advances this timing.
- **OnBreak**: all LEDs off for `kBreakDurationMs` (2 s). When the break
  ends, `beginNextSearch()` computes the next search's target as
  `clamp(lastPress +/- randomJump(), minX, maxX)` for each channel
  independently and calls `startSearch()`.
- `startSearch(targetRed, targetGreen)` increments `trialNumber`, anchors
  the knobs to the target, starts the flicker there, and re-enters
  `Searching` — this is also how the very first search of a session starts,
  with an explicit target of `(0, 0)`.
- `randomJump()`: magnitude drawn uniformly from `[kWalkJumpMin,
  kWalkJumpMax]` (500-1500) with an independent random sign, so the next
  search's start is always a real, noticeable move from the last button
  press — never a negligible one near the old location. This is what makes
  the location variability depend on where the participant just was,
  instead of being fully independent of it each time.
- `trialCurrentNumber()` exposes the running search count (1-based) so
  `telemetry.cpp` can tag its live frames with the same number that the
  eventual button-press result for that search will use.
- `trialIsActive()` (true in any non-`Idle` state) gates `START`/`STOP` in
  `serial_commands.cpp`. `trialIsSearching()` (true only in `Searching`)
  gates whether `knobs.cpp` samples and `telemetry.cpp` streams.

**Threading/interrupt note**: `onButtonPress()` runs in hardware-interrupt
context (attached via `attachInterrupt`) and calls `sendResult()`, which
does a blocking `Serial.print`/`println` sequence directly from the ISR.
This mirrors the legacy code's behavior (which also printed from the button
ISR) and works in practice on Teensy's USB-CDC serial, but it's worth
knowing if `onButtonPress()` is ever extended — printing from an ISR is not
generally best practice.

### `dataframe.{h,cpp}`

One function, `sendDataFrame(amberValue, redValue, greenValue, press,
trialNumber)`, used by both `trial.cpp` (the final per-search result,
`Press=1`) and `telemetry.cpp` (the live stream, `Press=0`) so the
`Serial.print` sequence for the six `@`-separated fields
(`TriggerCue@TrialNumber@Amber@red@green@Press`) exists in exactly one
place. `TriggerCue` is always `0` (unused in this experiment).

### `telemetry.{h,cpp}`

A second `IntervalTimer`, independent of the flicker timer, ticks every
`kTelemetryIntervalUs` (100 ms) and sets a flag (`onTelemetryTick`); the
actual `Serial` write happens in `telemetryPoll()`, called from `loop()`,
specifically to keep the ISR itself tiny and avoid doing serial I/O from
interrupt context. While `trialIsSearching()` is true, each tick sends one
live dataframe with the current red/green/amber and `Press=0`.

### `serial_commands.{h,cpp}`

Parses one line per call to `serialCommandsPoll()` (non-blocking — does
nothing if `Serial.available() <= 0`):

| Command | Dispatch |
|---|---|
| `START` | `trialStart()`, only if not already active |
| `STOP` | `trialStop()`, only if active |
| `MODE DEFAULT` / `MODE ADVANCED` | `settingsSetMode()` |
| `SET <name> <value>[, <name> <value>...]` | `handleSetCommand()` — splits on commas, applies each assignment via `settingsTrySet()` |
| `GET` | Prints mode + all six setting values on one line |

Chosen as plain-text line commands (no JSON) specifically so a desktop
application in any language can build them with simple string formatting,
without needing a parser library on the Teensy side.

### `knobsBehavioral.ino`

Intentionally minimal — just the `setup()`/`loop()` wiring:

```cpp
void setup() {
  serialCommandsInit();
  settingsInit();
  flickerInit();
  knobsInit();
  trialInit();
  telemetryInit();
  threads.addThread(knobsThreadLoop);
}

void loop() {
  serialCommandsPoll();
  telemetryPoll();
  trialPoll();
}
```

`knobsThreadLoop` runs on its own `TeensyThreads` thread (the only
non-main-loop thread); everything else is driven from `loop()` or from
interrupt/timer callbacks that only set flags for `loop()` to act on.

## Hardware status

Everything described above has been flashed to real Teensy 4.0 + PCB
hardware and confirmed working: the single-timer flicker fix, `SET`/`MODE`/
`GET`, the 100 ms telemetry stream, min/max red/green clamping, the
deadband, the randomized walk jump, and the full Searching/Acknowledging/
OnBreak auto-continue pacing. See `PLAN.md` for the current status of each
milestone, and the GUI/firmware integration milestones that haven't started
yet.
