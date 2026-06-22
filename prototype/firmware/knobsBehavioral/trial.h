#pragma once

// Owns the lifecycle of a single behavioral trial: starting the flicker and
// knob sampling, and ending the trial on a button press by reporting the
// final red/green settings over serial.
void trialInit();
void trialStart();
void trialStop();
bool trialIsActive();
