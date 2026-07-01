#ifndef BEHAVIORAL_MODE_H
#define BEHAVIORAL_MODE_H

// Run Behavioral mode: knobs (PIN_KNOB_A/B) drive LEDA/LEDB intensity live via
// an anchor-offset strategy. A button press (physical, or serial PRESS) ends
// the trial, logs the response, and walks to a new randomized target. No
// baselines, no hue support. Runs indefinitely until STOP (started=false).
void runBehavioral();

#endif
