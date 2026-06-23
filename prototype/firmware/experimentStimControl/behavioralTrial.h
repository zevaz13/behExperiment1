#pragma once

// Owns the behavioral session state machine: Searching -> Acknowledging ->
// OnBreak, looping back to Searching automatically until BEHAVIORALSTOP. A
// button press during Searching ends that search, logs the result, and
// starts the acknowledge-blink + break sequence; knob sampling resumes on
// its own afterward at a new, last-press-anchored start point.
void behavioralTrialInit();
void behavioralTrialStart();
void behavioralTrialStop();

// True for the whole session (Searching/Acknowledging/OnBreak), false when
// idle. Used to allow/reject BEHAVIORALSTART and BEHAVIORALSTOP, and to bar
// the grid experiment from starting while a behavioral trial is active.
bool behavioralTrialIsActive();

// True only while knobs should be sampled and drive the flicker.
bool behavioralTrialIsSearching();

// The search currently in progress (or most recently started), starting at
// 1 for the first search of a session. Used to tag log lines.
int behavioralTrialCurrentNumber();

// Advances the Acknowledging/OnBreak timing. Call from the main loop.
void behavioralTrialPoll();
