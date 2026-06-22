#pragma once

// Samples the red/green knob potentiometers and smooths them over a short
// window.
void knobsInit();
int knobsCurrentRed();
int knobsCurrentGreen();

// Re-anchors the internal ADC offset so that, given the knobs' current
// physical position, the next sample maps to (targetRed, targetGreen) —
// used to start each search at an unpredictable-but-controlled point.
void knobsAnchorTo(int targetRed, int targetGreen);

// Runs forever on its own thread: samples while a search is active and
// pushes results into the flicker module.
void knobsThreadLoop();
