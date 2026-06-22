#pragma once

// Drives the amber/red/green LEDs as independent square waves using a
// hardware timer, so RED+GREEN and AMBER are always strictly out of phase.
void flickerInit();
void flickerStart(int redValue, int greenValue, int amberValue);
void flickerSetRedGreen(int redValue, int greenValue);

// Stops the alternating timer but leaves the last red/green/amber values in
// place (used between searches, e.g. for the acknowledge blink).
void flickerFreeze();

// Writes all three LEDs at once: their last values if on, or off. Used for
// the acknowledge blink and the inter-search break.
void flickerSetAllOn(bool on);

// Full stop: ends the timer and zeroes all three channels (session STOP).
void flickerStop();
