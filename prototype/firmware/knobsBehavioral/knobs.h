#pragma once

// Samples the red/green knob potentiometers, smooths them over a short
// window, and applies a per-trial random offset so the dial-to-brightness
// mapping can't be memorized across trials.
void knobsInit();
void knobsRandomizeOffsets();
int knobsCurrentRed();
int knobsCurrentGreen();

// Runs forever on its own thread: samples while a trial is active and
// pushes results into the flicker module.
void knobsThreadLoop();
