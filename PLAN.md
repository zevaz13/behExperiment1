# Plan

## Milestones

### 1. Firmware cleanup (1.1-1.5 hardware-verified)
- [x] Split monolithic `knobsExperimentTeensy.ino` into modules under
      `prototype/firmware/knobsBehavioral/`: `pins.h`, `config.h`,
      `flicker.*`, `knobs.*`, `trial.*`, `serial_commands.*`.
- [x] Drop unused experiment modes (random walk, linear EEG/behavioral
      walks) — only the knobs/variable-resistor behavioral experiment is
      kept.
- [x] Drop unused `Bounce2` dependency (configured but never queried in the
      legacy code) and the unused `~~~` end-of-frame sentinel (the GUI's
      parser ignores lines without `@`, so it had no effect).
- [x] Renamed serial protocol to `START`/`STOP` (legacy GUI used
      `1789`/`6969` — GUI will need updating to match, see milestone 3).
- [x] Trial result is now sent once per button press instead of 9x
      (legacy code repeated it as a workaround for an already-fixed bug).
- [X] Build/flash-test on actual Teensy 4.0 + PCB hardware.
      - Code Builds and runs.
      - Issues were detected with the flickering. Both the yellow and red+green Combination are been used at the same time. These must be out of fase. First part of the period for RED+Green (No Yellow), second part for Yellow (No Red+green)
### 1.1 Solve Flickering issues
- [x] `flicker.cpp` now uses a single `IntervalTimer` whose ISR alternates
      between two strictly exclusive phases: RED+GREEN on/AMBER off, then
      AMBER on/RED+GREEN off. Public API (`flickerInit/Start/SetRedGreen/
      Stop`) unchanged, so `trial.cpp`/`knobs.cpp` needed no changes.
- [x] Re-flash and verify on hardware that RED+GREEN and AMBER no longer
      overlap.

### 1.2 Configuration and serial printing
- [x] Added `settings.{h,cpp}`: flicker frequency, amber reference, max/min
      red/green are now runtime values (defaults from `config.h`),
      configurable via `SET <name> <value>` (e.g. `SET maxRed 2800`) —
      plain text, one setting per line, chosen so a desktop app can build
      commands with simple string formatting (no JSON parser needed on
      the Teensy).
- [x] Default mode (`MODE DEFAULT`, the boot default): settings are pinned
      to the `config.h` constants; `SET` is rejected. Advanced mode
      (`MODE ADVANCED`): `SET` takes effect immediately, applied live
      (mid-trial changes to max/min red/green take effect on the next
      knob sample; frequency changes take effect on the next trial start).
- [x] Added `telemetry.{h,cpp}`: a second `IntervalTimer` ticks every
      100 ms; while a trial is active it streams the same dataframe format
      used for the final result (Press=0), so a GUI can plot red/green
      live. The one-shot send on button press is unchanged (Press=1) and
      still marks the authoritative trial result in the log.
- [x] Extracted `dataframe.{h,cpp}` (`sendDataFrame`) so the periodic
      stream and the final button-press result share one implementation
      instead of duplicating the `Serial.print` sequence.
- [x] Default `minRed`/`minGreen` changed from the legacy 300/300 to 0/0,
      matching the `startingPoint/experiment.md` spec.
- [x] Documented mode/SET usage and the experimental procedure in
      `docs/configure.md`.
### 1.3 Refining configuration
- [x] `SET` now accepts multiple comma-separated assignments on one line,
      e.g. `SET flickerFrequencyHz 20, amberValue 500`.
- [x] `SET flickerFrequencyHz 0` now stops the flicker entirely: RED, GREEN,
      and AMBER are all written continuously at their current values
      instead of alternating (`flicker.cpp`'s `flickering` flag).
- [x] "Command to start a default experiment": no new command needed —
      `START` already always uses whatever settings are currently active,
      and they persist across trials until `MODE DEFAULT` is sent. Documented
      this explicitly in `docs/configure.md` so it's not assumed to be a gap.
- [x] Added `GET`: prints the current mode and all six setting values on one
      line, so the configuration can be checked before `START`.
- [x] Wrote `docs/configure.md` for human users: Default/Advanced mode,
      every command, and the full experimental procedure.

### 1.4 Experimental pacing and location variability
- [x] `trial.cpp` is now a state machine (`Searching` -> `Acknowledging` ->
      `OnBreak` -> `Searching`, looping automatically) instead of a single
      `active` bool. A button press no longer stops the session: it
      acknowledges (all 3 LEDs blink together 3x over ~0.5s,
      `kAcknowledgeBlinkCount`/`kAcknowledgeBlinkIntervalMs`), goes dark for
      2s (`kBreakDurationMs`), then resumes searching automatically. `STOP`
      still fully ends the session from any state.
- [x] Replaced the free-random per-search ADC offset
      (`knobsRandomizeOffsets`) with `knobsAnchorTo(targetRed, targetGreen)`:
      it samples the knobs once and back-solves the offset so the next
      sample lands exactly on a target value. The target for each new
      search is `clamp(lastPressValue +/- random(kWalkJitterRed/Green),
      minX, maxX)` — computed when the break starts, applied when it ends.
      The first search of a session targets `(0, 0)`.
- [x] Fixed `knobs.cpp`'s ADC wraparound to true modulo-4096 (the legacy
      single-direction subtraction only handled positive overflow; offsets
      can now be negative since they're solved rather than drawn from
      `random(0, max)`).
- [x] Guarded the new offset math against `maxRed == minRed` (or green) —
      would have been a division by zero if set via `SET`.
- [x] `TrialNumber` in the dataframe now increments per search (was always
      0), starting at 1, exposed via `trial.h`'s `trialCurrentNumber()` and
      used by both the button-press result and the live telemetry stream.
- [x] Documented the new pacing and per-session `TrialNumber` behavior in
      `docs/configure.md`.
### 1.5 Minor changes
- [x] The walk jump is now randomized rather than fixed at 1000: magnitude
      drawn uniformly from `[kWalkJumpMin, kWalkJumpMax]` = [500, 1500]
      (same range for both channels), with a random sign — every jump is a
      real move, never a negligible one. Replaces `kWalkJitterRed/Green` in
      `config.h`; logic lives in `trial.cpp`'s `randomJump()`.
- [x] Added a deadband: in `knobs.cpp`, the mapped red/green output is
      snapped to exactly 0 if it's within `kDeadbandThreshold` (25) units of
      0, to suppress ADC noise jitter near the low end of the range.
- [x] Re-flashed and verified on real Teensy 4.0 + PCB hardware: `SET`/
      `MODE`/`GET`, the 100 ms telemetry stream, min/max red-green
      clamping, the deadband, the randomized walk jump, and the full
      Searching/Acknowledging/OnBreak auto-continue pacing all confirmed
      working as designed.

### 2. GUI refactor (in progress)

### 2.1 Definition of requirements (done)
- [x] Stack: Python, managed by `uv`. PySide6 for the UI, `pyserial` for the
      Teensy link, `pyqtgraph` embedded as a Qt widget for the live plot —
      one integrated window. Chosen over an all-Dear-PyGui app (faster
      launch, ~300ms, but no mature plotting+forms toolkit) because
      PySide6+pyqtgraph keeps everything in a single window; measured
      launch overhead is ~1.2-1.5s (pyqtgraph's import is the slow part),
      judged acceptable for a desktop research tool. PySide6 and Dear PyGui
      can't share one window (Dear PyGui owns its own render loop), which
      ruled out mixing them.
- [x] Environment: developed and run on native Windows (Windows Python +
      `uv`), not WSL2 — the Teensy enumerates as a COM port that WSL2 can't
      see without `usbipd-win` passthrough. Code still lives in this repo.
- [x] Connection flow: on launch, scan ports for the Teensy's USB vendor ID
      (PJRC, `0x16C0`) via `pyserial`'s `list_ports`, auto-connect, and show
      a blocking "Connecting..." screen until it succeeds. Falls back to a
      manual port-picker if no match is found.
- [x] Mode/settings screen: choosing "Default" sends `MODE DEFAULT`;
      choosing "Advanced" sends `MODE ADVANCED` and opens a form for the six
      settings, pre-filled from a `GET` sent right after connecting (the
      firmware boots in Default mode, so this reflects the real `config.h`
      defaults — no hardcoded duplicate values in the GUI to drift from the
      firmware).
- [x] Live plot: scatter plot, red on the x-axis, green on the y-axis, axis
      limits taken from that same `GET` response's
      `minRed/maxRed/minGreen/maxGreen`, single black round marker updated
      from the 100 ms telemetry stream.
- [x] Protocol: `START`/`STOP`/`SET`/`MODE`/`GET` only — no legacy
      `1789`/`6969`.

### 2.2 First draft
- [x] Scaffolded `prototype/gui/` with `uv init --app` (real `pyproject.toml`
      + `uv.lock`, not hand-written). Dependencies: `pyside6`, `pyqtgraph`,
      `pyserial`.
- [x] `protocol.py`: parses `GET` responses and telemetry/result dataframes,
      builds multi-assignment `SET` commands. Pure functions, no Qt/serial
      dependency, easy to test in isolation.
- [x] `serial_link.py`: `find_teensy_port()` matches on PJRC's USB vendor ID
      (`0x16C0`); `list_all_ports()` for the manual fallback. `SerialLink` is
      a `QThread` that owns the `pyserial` connection, reads lines in the
      background, and emits Qt signals (`line_received`,
      `connection_lost`) — writes (`send()`) happen directly from the
      caller's thread.
- [x] `main_window.py`: three `QStackedWidget` pages —
      `ConnectPage` (auto-detect every 500 ms, falls back to a manual port
      dropdown after ~3 s of no match), `ModePage` (Default/Advanced radio +
      a form for the six settings, pre-filled from the post-connect `GET`),
      `SessionPage` (Start/Stop buttons, a `pyqtgraph` scatter plot with a
      single black marker tracking live red/green, axis limits from the
      resolved settings).
- [x] Verified end-to-end (Connect -> Mode -> Session, both Default and
      Advanced paths, telemetry updating the plot) using a fake serial link
      run with `QT_QPA_PLATFORM=offscreen` — this environment (WSL2) has no
      Teensy COM port and no display, so this is as far as testing could go
      here. Not yet run against real hardware (needs native Windows per the
      2.1 decision).

### 2.3 Improve plotting
- [x] Axis limits set with `padding=0` so they're exactly
      `[minRed, maxRed]` / `[minGreen, maxGreen]` from the resolved
      settings, instead of pyqtgraph's default auto-padding.
- [x] X axis labeled "Red LED intensity (A/D)", Y axis "Green LED
      intensity (A/D)".
- [x] Plot background set to black (`setBackground("k")`); the live
      position is now a solid yellow round marker (was black, invisible
      against the new background).
- [x] Added a second `pyqtgraph` series, accumulated for the whole session:
      one gray X per button press (`Press=1` frame), left in place
      permanently. Cleared on `start_session()` (i.e. each time the
      mode/settings screen is confirmed), so marks don't carry over
      between sessions.
- [x] Added a `QTableWidget` side panel (Trial / Red / Green columns); one
      row appended per button press, scrolled to the bottom each time.
- [x] Added a "Back to experiment selection" button on the session screen.
      Enabled whenever no session is running (i.e. before the first Start,
      or after Stop) and disabled while running, so the firmware can't be
      left in an active session that the GUI has navigated away from.
      Decided this also applies before the very first Start (not just
      strictly "after Stop") since there's nothing running to interrupt —
      the literal "only if stopped" requirement was ambiguous about that
      edge case. Going back re-queries `GET` rather than reusing stale
      local state, since settings persist on the firmware across mode
      switches.
- [x] Verified the full Start -> button-press -> Stop -> Back ->
      reconfigure -> Start flow (table rows, press marks, exact axis
      range, button enablement) with a fake serial link under
      `QT_QPA_PLATFORM=offscreen`; not yet run against real hardware.
### 2.3a. Details for plotting
- [x] Added a permanent label in the `QMainWindow` status bar (not tied to
      any one page, so it survives every screen transition) showing mode +
      all six settings, updated after connect, mode confirm, and Back.
- [x] Added a "Save Results..." button: native save dialog, writes the
      results table to a `.txt` file (header line `Trial Red Green`, then
      one space-separated line per row).
- [x] Wrote `docs/gui-usage.md`: the three-screen flow, what every button/
      marker/table column means, and the status line.
- [x] Added a "New GUI" section to `summary.md` with all the GUI decisions
      and why (stack choice incl. measured launch times, WSL/Windows venv
      split, connection flow, mode/settings single-source-of-truth design,
      plot/table/save details, Back-button gating).
- [x] Verified status bar updates and the save-to-file round trip with a
      fake serial link under `QT_QPA_PLATFORM=offscreen`; not yet run
      against real hardware.
- [x] Added a fourth `pyqtgraph` series: a red star marker at the median of
      all button-press red/green values so far this session
      (`statistics.median`, computed independently per channel). Empty
      until the first press (no median of zero points); updates on every
      press alongside the gray X marks; does not add a table row. Cleared
      on `start_session()` like the other press-derived state.
### 2.4 Add Support for participant and session number
- [x] Improve behavior of starting locations (the LEDs cycling between ~0 and
      the max value at a cold start / new search). Root cause: anchoring a
      search to the exact edge of the range puts the knob's raw ADC value on
      `knobs.cpp`'s modulo-4096 wrap boundary, where a few units of ADC noise
      flip the mapped output between min and max. Chose option (b) (interior
      reset point) over the movement-threshold approach, applied to every
      search start (not just the first):
      - Added `kStartMarginDivisor` (5) to `config.h`; `margin = (max - min)/5`.
      - `trial.cpp`'s first search now targets `(minX + margin, minY + margin)`
        instead of `(0, 0)`.
      - `beginNextSearch()` now clamps each target to
        `[minX + margin, maxX - margin]` instead of `[minX, maxX]`, so no
        search (first or later) can start on the cycling-prone edge. The full
        `[min, max]` range is still reachable by turning the knob; only the
        start point is constrained.
      - The divisor is a compile-time constant, consistent with `kWalkJump*`
        and `kDeadbandThreshold` (not exposed via `SET`); trivial to promote
        to a runtime setting later if needed.
      - Updated `docs/configure.md` and `docs/firmware-architecture.md`.
      - Flashed and verified on Teensy 4.0 hardware: cold-start cycling is
        gone, searches start away from the edges, and it integrates correctly
        with the GUI.
### 2.5. Session + ID in the GUI
- [x] see `docs/participant-management-proposal.md` for ideas. Implemented as:
      - [x] Each session is logged to a single file `{SubID}_R{n}.txt`, where
            `n` is the first index whose file doesn't yet exist in the folder
            (`participants.py:next_session_number`), so sessions never
            overwrite each other. The file is created (with its `Trial Red
            Green` header) when the session is started.
      - [x] A `participants.csv` database lives inside the chosen save folder
            (decided per-folder over one global DB: data + metadata travel
            together). One row per session: `sub_id, group, session, file,
            datetime`. New module `participants.py`.
      - [x] New `ParticipantPage` (subject info view): pick a save folder
            (remembered between launches via `QSettings`), then either add a
            session to an existing participant in that folder (shown in a
            dropdown, read from `participants.csv`) or create a new one.
      - [x] New participant has a `Group` dropdown
            `{HC, PD, MD, Protan, Deutan, other}`, default `HC`, saved to the
            database. Group is set once at creation and shown read-only when
            adding later sessions.
      - [x] Autosave: the right-side table is rewritten to the session file on
            every button press (CSV format chosen for the DB; the per-session
            data file keeps the exact `Trial Red Green` table format). Manual
            "Save Results..." kept as an extra export.
      - [x] Flow is now Connect -> Participant -> Mode -> Session; "Back to
            experiment selection" returns to the Participant screen so a
            different participant/session can be started without relaunching.
      - [x] Verified end-to-end with a fake serial link under
            `QT_QPA_PLATFORM=offscreen` (new + existing participant, R1/R2
            numbering, autosave file == table, telemetry frames ignored,
            duplicate-ID rejection, DB rows). Not yet run against real
            hardware.
      - Updated `docs/gui-usage.md`.
### 2.6. Final details
- [x] The stimulator configuration each session ran with is now saved to the
      metadata database: `participants.csv` gained one column per setting
      (`mode, flickerFrequencyHz, amberValue, maxRed, maxGreen, minRed,
      minGreen`), written alongside the existing session row in
      `record_session()`. `SessionPage` stores the resolved `Settings` and
      passes them through on Start. (Separate columns over a single packed
      string, per the user, so they're filterable in a spreadsheet.)
- [x] The current median is shown numerically under the right-side table: a
      "Median  Red: x  Green: y" label below the table, updated on every press
      (same values as the red star marker on the plot), reset to "Median: -"
      when a new session is configured.
- [x] Verified offscreen with a fake serial link: config columns written with
      the right header/values, median label formatting and reset. Not yet run
      against real hardware.
- Updated `docs/gui-usage.md`.

### 3. Grid Experiment Firmware
### 3.1. Grid experiment details (analysis + plan; implementation later)
- [x] Reviewed `startingPoint/eegEXP_grid_fixed/eegEXP_grid_fixed.ino`.
- [x] Summarized the grid firmware in `startingPoint/grid.md`: what the
      experiment is (automatic EEG stimulus presentation, no knobs/button),
      how the current code works (sequence generation, presentation, three
      drifting flicker timers, two-step `grid`/`@order!` protocol, "fixed"
      mode), and its problems (same pre-rewrite issues as the behavioral
      firmware, baseline off-by-one, dead `Bounce2`/analog-input/`pressFlag`
      code, no machine-readable stream).
- [x] Suggested the changes so only the grid remains: drop "fixed" mode and
      all dead code (decided with the user).
- [x] Modular plan (mirrors `knobsBehavioral/`): new `prototype/firmware/
      gridEEG/` with `pins/config/settings/flicker/sequence/trial/dataframe/
      serial_commands` modules, single-timer flicker, a non-blocking `millis()`
      state machine (drops TeensyThreads), and the ten configurable settings
      from CLAUDE.md (flicker freq, amber, min/max red/green, trial length,
      intertrial wait, baselines start/end). Documented in `grid.md`; to be
      built in the implementation milestone.
- [x] Fit with behavioral: same `SET`/`GET`/`MODE` config design and a
      parser-compatible dataframe; distinct `GRIDSTART <order>`/`GRIDSTOP`
      start/stop so a future combined firmware can't confuse the two. Pins are
      identical to the behavioral PCB. Open questions for implementation are
      listed at the end of `grid.md`.
### 3.2 Implementation of grid experiment Firmware
- [x] Built the modular grid firmware in `prototype/firmware/gridEEG/`
      (self-contained, own copies of the shared modules), mirroring
      `knobsBehavioral/`: `pins.h`, `config.h`, `settings.{h,cpp}`,
      `flicker.{h,cpp}` (single-timer ISR, plus steady-amber for baselines and
      all-off for intertrials), `sequence.{h,cpp}` (grid generation),
      `trial.{h,cpp}` (non-blocking `millis()` state machine), `dataframe.{h,cpp}`,
      `serial_commands.{h,cpp}`, `gridEEG.ino`.
- [x] Dropped TeensyThreads entirely: the presentation is a state machine
      (Active -> Intertrial, advanced from `loop()`), the flicker runs on one
      `IntervalTimer`. Removed the "fixed" mode and all dead code (Bounce2,
      analog inputs, pressFlag, `~~~`). Fixed the baseline off-by-one.
- [x] Commands `GRIDSTART [order]` / `GRIDSTOP` (distinct from behavioral
      START/STOP), plus the shared `SET`/`GET`/`MODE DEFAULT|ADVANCED`.
- [x] Eleven configurable settings: flickerFrequencyHz, amberValue,
      minRed/maxRed, minGreen/maxGreen, trialLengthMs, interTrialWaitMs,
      baselinesStart, baselinesEnd, order.
- [x] `order` is a configurable setting (default 1, clamped to 1-4) used when
      `GRIDSTART` has no argument; `GRIDSTART <order>` overrides it for one run
      without changing the stored value (per the user's note).
- [x] Data stream reuses the behavioral 6-field shape so a future combined GUI
      can share one parser: `TriggerCue@StimNumber@Amber@Red@Green@Phase` (phase
      0=baseline, 1=stimulus, 2=intertrial), one frame at each trial onset and
      offset.
- [x] Host-tested the sequence generator (the diagonal/order/linspace logic):
      all 4 orders produce 100 unique stimuli covering the full 10x10 grid with
      the correct start corners.
- [x] Flash + verify on real Teensy 4.0 hardware (LED phasing, trigger pulses,
      timing, GET/SET, the full baseline/grid/baseline run, GRID DONE).
- Wrote `docs/grid-configure.md` (commands, settings, procedure, data format).
- [x] Command names: GRIDSTART <order> / GRIDSTOP acceptable. If only GRIDstart it uses order = 1.  /
- [x] order should be SET setting.  /
- [x] Implement this in a Directory name /prototype/firmware/gridEEG

### 3.3 Grid Experiment GUI.
- [x] New self-contained GUI in `prototype/grid_gui/` (its own `uv` app),
      adapting the behavioral GUI's patterns: `serial_link.py` (copied),
      `protocol.py` (grid GET = 11 settings, grid frame, GRIDSTART/SET),
      `main_window.py`, `main.py`. Flow: Connect -> Participant -> Mode ->
      Session.
- [x] Connects to the Teensy (auto-detect by vendor ID + manual fallback).
      Participant screen collects Subject ID + group, shown during the run but
      NOT saved (resolved the item 2 vs item 9 contradiction with the user:
      participant screen yes, no file/DB logging).
- [x] Mode screen: Default (one click) or Advanced (form of the 11 settings,
      pre-filled from GET, `order` constrained 1-4).
- [x] Session screen shows the 10x10 grid of stimulus coordinates (red x,
      green y); axis limits are the configured min/max red/green. Points start
      dim gray, turn bold yellow as each stimulus is presented, and the current
      stimulus is highlighted red. Cells are matched by nearest (red,green)
      level, so the GUI never needs the firmware's traversal/order logic;
      baseline frames (red=green=0) deliberately don't mark a grid cell.
- [x] Progress bar over all trials (baselinesStart + 100 + baselinesEnd),
      advanced on each intertrial frame and completed on `GRID DONE`.
- [x] The active GET configuration (+ participant) is shown at the top of the
      session screen.
- [x] Same WSL/Windows split as the behavioral GUI (offscreen-testable;
      `UV_PROJECT_ENVIRONMENT=.venv-linux` on Linux).
- [x] Verified end-to-end under `QT_QPA_PLATFORM=offscreen` with a fake link:
      Default and Advanced paths, the multi-assignment SET, grid cell
      highlighting by nearest level, baselines not marking cells, progress, and
      GRID DONE. Not yet run against real hardware.
- Wrote `docs/grid-gui-usage.md`.
### 4. Behavioral experiment and Grid experiment Firmware integration.
- [x] Produce a new single arduino project that uses the modules created in /prototype/firmware/ and is able to perform both experiments with the relevant conditions for each of them.
      Built `prototype/firmware/experimentStimControl/` (Teensy 4.0). Decisions
      (confirmed with the user):
      - Settings fully separate per experiment, no shared fields (even
        `flickerFrequencyHz`/`amberValue` are independent), since the two
        experiments were tuned with different default ranges
        (`behavioralSettings.{h,cpp}` / `gridSettings.{h,cpp}`, separate
        `BehavioralMode`/`GridMode` enums).
      - One shared `flicker.{h,cpp}`: the single-timer alternating ISR was
        already nearly identical between the two source projects: superset
        API (`flickerStart(red, green, amber, frequencyHz)`,
        `flickerSetRedGreen`, `flickerFreeze`, `flickerSetAllOn` for
        behavioral; `flickerSteadyAmber` for grid baselines; `flickerStop`
        unifies behavioral's old `flickerStop`/grid's old `flickerOff`).
        Frequency is now passed in by the caller rather than queried
        internally, since there's no longer one settings module to ask.
      - Shared `pins.h` (identical pin numbers in both source trees, same
        PCB) and a minimal shared `config.h` (serial baud, PWM resolution).
      - Everything else duplicated with `behavioral`/`grid`-prefixed
        files and symbols (functions, the `BehavioralMode`/`GridMode`
        enums) to avoid collisions when compiled as one sketch:
        `behavioralKnobs/Trial/Telemetry/Dataframe.{h,cpp}`,
        `gridSequence/Trial/Dataframe.{h,cpp}`.
      - Mutual exclusion: `BEHAVIORALSTART` is rejected with
        `"Grid trial active"` while a grid run is active, and vice versa
        (`"Behavioral trial active"` for `GRIDSTART`), since both drive the
        same physical LEDs/trigger pin.
- [x] The new file should be called experimentStimControl 
      (`prototype/firmware/experimentStimControl/experimentStimControl.ino`).
- [x] Each experiment should have own commands to start, stop and get in the advanced mode.
      Fully symmetric, no shared verbs: `BEHAVIORALSTART`/`BEHAVIORALSTOP`/
      `BEHAVIORALMODE DEFAULT|ADVANCED`/`BEHAVIORALSET`/`BEHAVIORALGET` and
      `GRIDSTART [order]`/`GRIDSTOP`/`GRIDMODE DEFAULT|ADVANCED`/`GRIDSET`/
      `GRIDGET`. This renames behavioral's old bare `START`/`STOP`/`MODE`/
      `SET`/`GET` — a breaking protocol change that the existing GUIs (both
      still point at the old per-experiment firmware/protocol) will need to
      pick up in milestone 5.
      Wrote `docs/experimentStimControl-configure.md`.
- [ ] Flash and verify on real Teensy 4.0 + PCB hardware: both experiments
      individually, and the mutual-exclusion rejection in both directions.
      Not yet built/flashed — no Arduino toolchain available in this
      (WSL2/Linux) environment; reviewed manually for symbol/include
      consistency only.
 
### 5. Firmware + GUI integration (not started)
- [ ] End-to-end test of new firmware against new/updated GUI.

## Known gaps surfaced during cleanup
- Fixed as part of 1.2: `minRed`/`minGreen` are now actually applied as the
  floor of the knob-to-PWM mapping (`map(raw, 0, 4095, minX, maxX)` in
  `knobs.cpp`), instead of being unused constants like in the legacy code.
  Defaults are now 0/0, matching `startingPoint/experiment.md`.
- All of milestone 1 (1.1 through 2.4) is now hardware-verified on Teensy
  4.0 + PCB — see the entries above. 
