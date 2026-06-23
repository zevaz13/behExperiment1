#pragma once

// Drives the amber/red/green LEDs with a single hardware timer, so RED+GREEN
// and AMBER are always strictly out of phase (no half-period where both or
// neither are lit). Frequency comes from settings (0 Hz = no flicker, all
// three channels shown continuously).
void flickerInit();

// Grid stimulus: alternate the red+green combination against amber.
void flickerStartStimulus(int redValue, int greenValue, int amberValue);

// Baseline trial: steady amber on, red/green off, no alternation.
void flickerSteadyAmber(int amberValue);

// Intertrial / idle: all three channels off, timer stopped.
void flickerOff();
