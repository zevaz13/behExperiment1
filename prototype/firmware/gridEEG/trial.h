#pragma once

// Owns the grid presentation as a non-blocking state machine: baselinesStart
// amber-only trials, the kNumStims grid stimuli, then baselinesEnd amber-only
// trials. Each trial is an active phase (trigger HIGH, flicker/steady amber)
// followed by an intertrial wait (trigger LOW, all off). trialPoll() advances
// it on millis(); the run ends automatically after the last trial or on a
// GRIDSTOP.
void trialInit();
void trialStart(int order);  // start corner 1-4 (clamped)
void trialStop();
bool trialIsActive();
void trialPoll();
