#pragma once

// Drives the amber/red/green LEDs as independent square waves using a single
// hardware timer, so RED+GREEN and AMBER are always strictly out of phase.
// Shared by both experiments since they drive the same three LEDs the same
// way; each experiment passes its own configured frequency.
void flickerInit();

// Starts (or restarts) the alternating cycle. frequencyHz == 0 means "no
// flicker": all three channels are shown at once, continuously.
void flickerStart(int redValue, int greenValue, int amberValue, unsigned int frequencyHz);

// Updates red/green without touching amber or restarting the cycle.
// Behavioral: pushes live knob readings while a search is active.
void flickerSetRedGreen(int redValue, int greenValue);

// Stops the alternating timer but leaves the last red/green/amber values in
// place. Behavioral: used between searches, for the acknowledge blink.
void flickerFreeze();

// Writes all three LEDs at once: their last values if on, or off.
// Behavioral: used for the acknowledge blink and the inter-search break.
void flickerSetAllOn(bool on);

// Steady amber on, red/green off, no alternation. Grid: baseline trials.
void flickerSteadyAmber(int amberValue);

// Full stop: ends the timer and zeroes all three channels. Behavioral:
// session STOP. Grid: intertrial gaps and GRIDSTOP.
void flickerStop();
