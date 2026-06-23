#pragma once

// Owns the grid presentation as a non-blocking state machine: baselinesStart
// amber-only trials, the kNumStims grid stimuli, then baselinesEnd amber-only
// trials. Each trial is an active phase (trigger HIGH, flicker/steady amber)
// followed by an intertrial wait (trigger LOW, all off). gridTrialPoll()
// advances it on millis(); the run ends automatically after the last trial
// or on a GRIDSTOP.
void gridTrialInit();
void gridTrialStart(int order);  // start corner 1-4 (clamped)
void gridTrialStop();

// True for the whole run. Used to allow/reject GRIDSTART and GRIDSTOP, and
// to bar the behavioral experiment from starting while a grid run is active.
bool gridTrialIsActive();

void gridTrialPoll();
