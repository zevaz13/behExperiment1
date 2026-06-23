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
- [ ] Please add selected configuration of the stimulator to the metadata database. That is, the configuration for the experiment is saved. 
- [ ] Please show the current median under the right panel table.  That is, when computed, we show the median coordinate in numerical format. 

### 3. Grid Experiment Firmware
### 3.1. Grid experiment details
- [ ] Review the code in /startingPoint/eegEXP_grid_fixed.
- [ ] Summarize the grid experiment's firmware in /startingPoint/grid.md.  
- [ ] Suggest all changes needed so only the grid experiment is present.
- [ ] The solution must be modular, like the one for the behavioral experiment.  
- [ ] The solution must fit with the implementation of the behavioral experiment. 

### 4. Firmware + GUI integration (not started)
- [ ] End-to-end test of new firmware against new/updated GUI.

## Known gaps surfaced during cleanup
- Fixed as part of 1.2: `minRed`/`minGreen` are now actually applied as the
  floor of the knob-to-PWM mapping (`map(raw, 0, 4095, minX, maxX)` in
  `knobs.cpp`), instead of being unused constants like in the legacy code.
  Defaults are now 0/0, matching `startingPoint/experiment.md`.
- All of milestone 1 (1.1 through 2.4) is now hardware-verified on Teensy
  4.0 + PCB — see the entries above. 
