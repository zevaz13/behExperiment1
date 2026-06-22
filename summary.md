# Project Summary: behExperiment1

## What this is

A behavioral neuroscience experiment ("knobs test" / metamers project) with two
components: Teensy 4.0 firmware that drives the stimulus and reads inputs, and a
C# WinForms GUI that talks to the Teensy over serial, logs data, and acts as the
experiment runner. CLAUDE.md's goal is to modernize both pieces; new work lives
under `prototype/`, tracked in `PLAN.md`.

## Repo layout (current)

```
CLAUDE.md                              project goals, role, coding standards
PLAN.md                                milestone tracker, updated after every change
docs/
  configure.md                         user-facing: commands, modes, experimental procedure
  firmware-architecture.md             internals: module-by-module design of the new firmware
startingPoint/
  experiment.md                        spec for the original experiment
  knobsExperimentTeensy/knobsExperimentTeensy.ino   legacy, untouched firmware (reference only)
  GUImetamers/                         legacy C# (.NET 8, WinForms) GUI (untouched so far)
prototype/firmware/knobsBehavioral/    the new, modular firmware (see below)
.agents/skills/agent-browser/          agent-browser skill (web search)
skills-lock.json
.gitignore                             added; .NET bin/obj untracked
```

## What's been done, and why

### 1. Firmware cleanup: legacy `.ino` -> modular `prototype/firmware/knobsBehavioral/`

The legacy firmware was a single ~512-line `.ino` implementing seven
experiment "modes" via a numeric `mode` variable. Only `mode == 2` (the
knobs/variable-resistor behavioral task) was actually finished; the rest
were `Serial.println("boing")` stubs for EEG/linear-walk variants that were
never built out. Per CLAUDE.md's instruction to keep things simple and not
carry dead code forward, the rewrite:

- Split the single file into `pins.h`, `config.h`, `flicker.{h,cpp}`,
  `knobs.{h,cpp}`, `trial.{h,cpp}`, `serial_commands.{h,cpp}` (later joined
  by `settings`, `dataframe`, `telemetry` — see below), each with one clear
  responsibility. Full module-by-module design: `docs/firmware-architecture.md`.
- Dropped every unfinished mode — only the working knobs/behavioral task was
  kept.
- Dropped the `Bounce2` library dependency: the legacy code configured a
  `Bounce` object (`attach`/`interval`) but never actually called `.fell()`
  or `.read()` on it anywhere — the real button-edge handling was a separate
  raw `attachInterrupt`. It was dead weight.
- Dropped the `~~~` end-of-frame sentinel the legacy firmware sent after
  each result: the GUI's serial parser only ever processes lines containing
  `@` (`if (data.Contains('@'))` in `screen3RandBeh.cs`), so a line of just
  `~~~` was silently ignored — it had no effect and was removed.
- Renamed the serial protocol from the legacy numeric codes (`1789` to
  start, `6969` to stop — chosen specifically because the GUI will be
  rewritten anyway, so this was a good time to make the protocol
  self-describing instead of preserving arbitrary magic numbers).
- The legacy firmware sent its result line 9 times in a row on button press,
  commented as "redundancy" for "an already-fixed bug" — i.e. dead
  workaround code. Changed to send once.
- `minRed`/`minGreen` existed as legacy constants (300/300) but were never
  actually used as a floor in the ADC-to-PWM `map()` call — a latent no-op.
  Fixed: they're now genuinely applied as the lower bound of the mapping,
  and their default was changed to 0/0 to match `startingPoint/experiment.md`'s
  stated spec (which the legacy 300/300 values contradicted).
- Flashed to real Teensy 4.0 + PCB hardware: this surfaced a real bug not
  visible from reading the code — the original three-independent-timer
  design (one `IntervalTimer` per LED channel) let RED+GREEN and AMBER
  overlap because the timers drift relative to each other. Fixed by
  switching to a single timer whose ISR writes all three channels together
  each tick, making the two phases strictly exclusive by construction.

### 2. Runtime configuration (`settings.{h,cpp}`, `SET`/`MODE`/`GET` commands)

CLAUDE.md asks for serial-configurable flicker frequency, amber/yellow
reference, max red/green, and min red/green, so values can be tuned without
reflashing. Decisions made along the way:

- **Command syntax** — chosen specifically because a *separate desktop
  application* (not a human at a serial terminal) will generate these
  commands: plain-text `SET <name> <value>` lines, not a packed positional
  frame and not JSON. Rationale: any language can build a line like this
  with plain string formatting (no JSON library needed on the Teensy, which
  would mean pulling in ArduinoJson just for this); it's self-describing
  (the app doesn't need to track a fixed field order); and it's easy to
  extend with a new setting later without breaking existing app code.
- **Default vs Advanced mode** — boots in `Default` (values pinned to
  `config.h` constants, `SET` rejected). `MODE ADVANCED` unlocks `SET`;
  `MODE DEFAULT` both locks it again *and* resets every value back to the
  compile-time defaults, even if customized in Advanced mode. This was a
  deliberate choice over the alternative (settings persisting forever
  regardless of mode) so there's always a guaranteed clean baseline to
  return to.
- **Live application** — `maxRed`/`maxGreen`/`minRed`/`minGreen` changes
  apply on the very next knob sample (~every 50 ms), even mid-search;
  `flickerFrequencyHz`/`amberValue` apply at the start of the next search.
  No "apply" command needed.
- **`GET`** — added so a connected app (or a human) can read back the
  active mode and all six values before starting, rather than having to
  track client-side state that might drift from the firmware's actual
  state.
- **Multiple `SET`s per line** — `SET flickerFrequencyHz 20, amberValue 500`
  applies both in one round trip, comma-separated.
- **`flickerFrequencyHz 0`** — a deliberate special case: disables the
  alternation entirely and shows RED+GREEN+AMBER simultaneously and
  continuously at their current values. Useful for inspecting the raw
  color mix without the flicker illusion.
- Considered and explicitly rejected: a separate "start a default
  experiment" command. Settings already persist as global state across
  searches regardless of mode — `START` always just uses whatever is
  currently active. The only way values reset is `MODE DEFAULT`. This was
  confirmed with the user rather than assumed, since the milestone note was
  ambiguous about whether new behavior was wanted here.

### 3. Experimental pacing and location variability (the biggest behavioral change)

The original ask: instead of fully stopping on a button press, acknowledge
it, take a short break, and continue automatically — and make the next
search's starting point depend on where the participant just was, rather
than being fully independent each time.

- **Why this matters**: a fully independent random start point (the
  legacy/original design) provides no information from trial to trial,
  which is simpler but doesn't let the experiment control how "far" each
  new search is from the last — the new design anchors each jump to the
  previous result so the step size and direction can be reasoned about and
  tuned (see the deadband/jump-range work below).
- `trial.cpp` became a state machine
  (`Searching -> Acknowledging -> OnBreak -> Searching`, looping
  automatically) instead of a single on/off flag. A button press no longer
  ends the session — only an explicit `STOP` does.
- **Acknowledge**: all three LEDs blink together 3 times over ~0.5 s.
  Implemented with an odd number of toggles (`2*count - 1`) so the sequence
  ends naturally on "off" instead of wasting a toggle that the following
  break would instantly overwrite anyway — a small but real correctness
  fix made during implementation, not part of the original ask.
- **Break**: all LEDs off for 2 s. The next search's target is computed
  during the break (`clamp(lastPress +/- randomJump, minX, maxX)`) and
  applied automatically when the break ends — no host command needed to
  continue.
- **Anchored starting point**: replaced the old "draw a free random ADC
  offset" mechanism with `knobs.cpp`'s `knobsAnchorTo(targetRed,
  targetGreen)`, which samples the knob once and *solves* for the offset
  needed so the next sample lands exactly on a target value — necessary
  because the new design needs to hit a specific computed target (the last
  press plus a jump), not just any unpredictable value.
- This anchoring math can produce **negative offsets** (target below the
  knob's current raw position), which the legacy wraparound logic
  (`value > 4095 ? value - 4095 : value`) can't handle correctly — it only
  ever subtracted, never added, so it broke for negative inputs. Fixed to
  true modulo-4096 arithmetic. This was a necessary side-effect of the
  anchoring redesign, not an independent fix.
- The anchoring math also divides by `(maxOut - minOut)`; guarded against
  `maxOut <= minOut` (a real risk now that these are `SET`-able at runtime)
  to avoid a hard division-by-zero crash on the Teensy.
- `TrialNumber` in the logged dataframe (previously always sent as `0`,
  unused) now increments once per search, shared between that search's live
  telemetry and its eventual button-press result — added because a single
  `START` can now span many searches, so rows needed a way to be
  distinguished for analysis.
- Live telemetry: a second `IntervalTimer` (independent of the flicker
  timer) ticks every 100 ms; the actual `Serial` write happens in a
  `telemetryPoll()` called from the main loop rather than directly in the
  timer ISR, specifically to avoid doing serial I/O from interrupt context.
  Streams the same dataframe format as the final result (`Press=0` instead
  of `1`) so a future GUI can plot red/green live during a search.
- Extracted `dataframe.{h,cpp}` so the `Serial.print` sequence for the
  six-field log line exists in exactly one place, shared by the final
  result and the live telemetry stream (previously duplicated).

### 4. Minor refinements to the jump/variability mechanics

- The jump size was originally a fixed `±1000`. Changed to a random
  magnitude drawn from `[500, 1500]` with an independent random sign, so
  every jump is guaranteed to be a real, noticeable move — never a
  negligible step that would leave the next search starting almost where
  the last one ended.
- Added a deadband: any mapped red/green output within 25 units of 0 is
  snapped to exactly 0, to suppress ADC noise jitter that would otherwise
  show up as small spurious nonzero readings when the true position is at
  or near the bottom of the range.

## Documentation produced

- `docs/configure.md` — user-facing: Default/Advanced mode, every serial
  command, the full experimental procedure (session/search lifecycle), and
  the dataframe format.
- `docs/firmware-architecture.md` — internals: every module's
  responsibility and public API, the dependency graph, the single-timer
  flicker design and why it replaced three independent timers, the
  anchoring/offset math, the trial state machine, and the threading/ISR
  model.
- `PLAN.md` — kept up to date after every milestone with what was done and
  why; also tracks what's explicitly *not* yet done (the GUI rewrite;
  GUI/firmware integration).

## Hardware status

All of milestone 1 (1.1 through 1.5: the single-timer flicker fix, runtime
`SET`/`MODE`/`GET` configuration, the 100 ms telemetry stream, min/max
red/green clamping, the deadband, the randomized walk jump, and the full
Searching/Acknowledging/OnBreak auto-continue pacing) has been flashed to
real Teensy 4.0 + PCB hardware and confirmed working as designed.

## What hasn't been done yet

- The GUI (`startingPoint/GUImetamers/`) hasn't been touched: it still
  speaks the legacy `1789`/`6969` protocol, not `START`/`STOP`/`SET`/`MODE`/
  `GET`. GUI refactor and firmware/GUI integration are separate, not-yet-
  started milestones in `PLAN.md`.
- An improved variability *routine* was explicitly asked for and partially
  delivered (the anchored random walk); further refinements (e.g. different
  jump distributions) remain open-ended per `PLAN.md`.
