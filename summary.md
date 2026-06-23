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
  configure.md                         user-facing: firmware commands, modes, experimental procedure
  firmware-architecture.md             internals: module-by-module design of the new firmware
  gui-usage.md                         user-facing: GUI screens and controls
startingPoint/
  experiment.md                        spec for the original experiment
  knobsExperimentTeensy/knobsExperimentTeensy.ino   legacy, untouched firmware (reference only)
  GUImetamers/                         legacy C# (.NET 8, WinForms) GUI (untouched, reference only)
prototype/
  firmware/knobsBehavioral/            the new, modular firmware (see below)
  gui/                                 the new GUI: Python, uv-managed (see below)
.agents/skills/agent-browser/          agent-browser skill (web search)
skills-lock.json
.gitignore                             .NET bin/obj, Python .venv*/__pycache__, Arduino build artifacts
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
- **Interior start points** (milestone 2.4): a search anchored to the exact
  edge of the range puts the knob's raw ADC value on the modulo-4096 wrap
  boundary, where a couple of units of noise flip the mapped output between
  min and max — the LEDs visibly cycle before the participant has touched
  anything. Fixed by keeping every search's start inside a margin of
  `(max - min) / kStartMarginDivisor` (divisor 5) from each edge: the first
  search now starts at the low interior corner instead of `(0, 0)`, and
  `beginNextSearch()` clamps each target to `[min + margin, max - margin]`
  instead of `[min, max]`. The full range stays reachable by turning the
  knob; only the start point is constrained. Chosen over the
  movement-threshold alternative for simplicity; divisor is a compile-time
  constant like the other tuning values. Hardware-verified on Teensy 4.0.

### 5. New GUI (`prototype/gui/`)

CLAUDE.md calls for evaluating a replacement language/framework for the
experiment logger GUI, and explicitly mandates `uv` if Python is chosen.
Decisions made, in order:

- **Stack** — Python + PySide6 (UI) + `pyqtgraph` (live plot, embedded as a
  Qt widget) + `pyserial` (Teensy link), one integrated window. This wasn't
  picked blind: I measured import/launch overhead for the candidates
  (`python3`/`uv` are both on `PATH` already, no setup friction) —
  PySide6+pyqtgraph comes to ~1.2-1.5s to a window (pyqtgraph's import is
  the slow part, ~1s alone), versus ~300ms for PySide6+Dear PyGui or an
  all-Dear-PyGui app. The faster combo was rejected once it became clear
  Dear PyGui owns its own render loop/window and can't embed as a widget
  inside a PySide6 window — the realistic alternative would've been two
  separate top-level windows, which was judged worse UX than the slower
  single-window option for a desktop research tool.
- **Environment** — developed and run on native Windows (Windows Python +
  `uv`), not WSL2, because the Teensy enumerates as a COM port that WSL2
  can't see without `usbipd-win` passthrough. This surfaced a real,
  non-obvious problem: a `.venv` built by Linux `uv` contains a `lib64`
  symlink that Windows' `uv` can't remove through the `\\wsl$` UNC bridge,
  so trying to reuse the same `.venv` directory from both OSes fails with a
  cryptic file-removal error. Fixed by using
  `UV_PROJECT_ENVIRONMENT=.venv-linux` whenever the project is run from
  WSL/Linux, so each OS gets its own venv directory and neither has to
  delete the other's.
- **Connection flow** — auto-detect by PJRC's USB vendor ID (`0x16C0`),
  auto-connect, blocking "Connecting..." screen; falls back to a manual
  port dropdown after ~3s of no match (`ConnectPage`).
- **Mode/settings screen** mirrors the firmware directly: Default sends
  `MODE DEFAULT`; Advanced sends `MODE ADVANCED` plus one multi-assignment
  `SET`. Advanced-mode field suggestions are read from a `GET` sent right
  after connecting, not hardcoded — same "single source of truth" principle
  used on the firmware side, so the GUI can't drift from whatever the
  firmware actually has active.
- **Live plot**: red on x, green on y, axis limits set with `padding=0` so
  they're exactly `[minRed, maxRed]`/`[minGreen, maxGreen]` rather than
  pyqtgraph's auto-padded default. Black background with a solid yellow
  round marker for the live position (the marker was originally black,
  which is invisible against black — caught once the background changed).
  Each button press leaves a permanent gray X, accumulated for the whole
  session and cleared only when a new session is configured.
- **Side table** (Trial/Red/Green) appends one row per button press only
  (not per telemetry tick), with a **Save Results** button that writes the
  table to a `.txt` file (header line + space-separated rows) via a native
  save dialog.
- **"Back to experiment selection"** is enabled only while no session is
  running (before the first Start, or after Stop) — disabled while running
  so the firmware can't be left in an active session that the GUI has
  navigated away from. The spec's literal wording ("only if they have
  pressed stop") didn't say what should happen before the very first
  Start; decided to allow Back there too, since nothing is running to
  interrupt. Going back re-queries `GET` rather than trusting local state.
- **Always-visible settings line**: a permanent label in the window's
  status bar (not tied to any one page, so it survives every screen
  transition) shows the active mode and all six settings as soon as
  they're known.
- Considered and explicitly rejected: re-sending `START`/`STOP` from a
  manual mode page re-entry without a fresh `GET` first. Every place the
  GUI needs to know the firmware's settings, it asks the firmware rather
  than caching/duplicating values client-side.
- **Median marker**: a fourth plot series — a red star at the per-channel
  median (`statistics.median`) of all button-press locations so far this
  session. Empty until the first press (no median of zero points), updated
  alongside the gray X marks on every press, and deliberately does *not*
  add a row to the results table — it's a derived summary, not a logged
  data point.

### 6. Participant / session management and per-session auto-save (`prototype/gui/`)

Milestone 2.5 ported the "create participants, save data to files" role the
legacy C# GUI had. Decisions, with the user:

- **Database location** — a `participants.csv` lives *inside each chosen save
  folder* rather than one global app-level DB. Chosen so the data files and
  their metadata travel together (copy/move the folder and nothing breaks)
  and "participants in the current folder" is simply that folder's DB, with
  no cross-folder path bookkeeping that could drift from the files.
- **Format** — CSV (the user's call), one row per session
  (`sub_id, group, session, file, datetime`); the *participants* in a folder
  are the distinct subject IDs across its rows. A new module `participants.py`
  owns all DB and filename logic (pure stdlib, no Qt), with the legacy-style
  "first index whose file doesn't exist" session-number scan so a new session
  never overwrites an old file.
- **New `ParticipantPage`** (Connect -> Participant -> Mode -> Session): pick a
  save folder (remembered across launches via `QSettings`), then add a session
  to an existing participant in that folder or create a new one. New
  participants get a `Group` dropdown `{HC, PD, MD, Protan, Deutan, other}`
  (default `HC`), recorded once at creation and shown read-only afterward.
- **Per-session file + auto-save** — each session is one file
  `{SubID}_R{n}.txt`, created with its `Trial Red Green` header when the
  session starts (not lazily on first press — the user's choice), then
  rewritten from the table on *every* button press, so the file always equals
  the right-side table and a crash/close can't lose data. The old manual
  "Save Results..." stays as an optional extra export.
- **Back** now returns to the Participant screen (was the Mode screen) so a
  different participant or a new session can be started without relaunching;
  the Mode form is still re-populated from a fresh `GET` each time into it.

## Documentation produced

- `docs/configure.md` — user-facing: Default/Advanced mode, every serial
  command, the full experimental procedure (session/search lifecycle), and
  the dataframe format.
- `docs/firmware-architecture.md` — internals: every module's
  responsibility and public API, the dependency graph, the single-timer
  flicker design and why it replaced three independent timers, the
  anchoring/offset math, the trial state machine, and the threading/ISR
  model.
- `docs/gui-usage.md` — user-facing: the three-screen flow (connect, mode,
  session), what every button/marker/table column means, and the
  always-visible settings line.
- `PLAN.md` — kept up to date after every milestone with what was done and
  why; also tracks what's explicitly *not* yet done (firmware/GUI
  integration; participant/session management).

## Hardware status

All of milestone 1 (1.1 through 1.5: the single-timer flicker fix, runtime
`SET`/`MODE`/`GET` configuration, the 100 ms telemetry stream, min/max
red/green clamping, the deadband, the randomized walk jump, and the full
Searching/Acknowledging/OnBreak auto-continue pacing) has been flashed to
real Teensy 4.0 + PCB hardware and confirmed working as designed.

## What hasn't been done yet

- The new GUI (`prototype/gui/`) has a working draft (connect, mode/
  settings, live plot, results table/save, status line) verified only with
  a fake serial link under `QT_QPA_PLATFORM=offscreen` — it has not yet
  been run against the real Teensy. The legacy GUI
  (`startingPoint/GUImetamers/`) is untouched and still speaks the legacy
  `1789`/`6969` protocol.
- Participant/session management and per-session auto-save (milestone 2.5)
  are implemented (see section 6) but, like the rest of the GUI, verified
  only under `QT_QPA_PLATFORM=offscreen`, not yet against the real Teensy.
  Firmware/GUI integration testing (milestone 4) and the grid experiment
  firmware (milestone 3) haven't started.
- An improved variability *routine* was explicitly asked for and partially
  delivered (the anchored random walk); further refinements (e.g. different
  jump distributions) remain open-ended per `PLAN.md`.
