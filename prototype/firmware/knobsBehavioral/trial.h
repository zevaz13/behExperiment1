#pragma once

// Owns the session state machine: Searching -> Acknowledging -> OnBreak,
// looping back to Searching automatically until STOP. A button press during
// Searching ends that search, logs the result, and starts the
// acknowledge-blink + break sequence; knob sampling resumes on its own
// afterward at a new, last-press-anchored start point.
void trialInit();
void trialStart();
void trialStop();

// True for the whole session (Searching/Acknowledging/OnBreak), false when
// idle. Used to allow/reject START and STOP.
bool trialIsActive();

// True only while knobs should be sampled and drive the flicker.
bool trialIsSearching();

// The search currently in progress (or most recently started), starting at
// 1 for the first search of a session. Used to tag log lines.
int trialCurrentNumber();

// Advances the Acknowledging/OnBreak timing. Call from the main loop.
void trialPoll();
