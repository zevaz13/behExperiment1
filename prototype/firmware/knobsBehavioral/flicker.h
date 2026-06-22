#pragma once

// Drives the amber/red/green LEDs as independent 10 Hz square waves using
// hardware timers, so each channel flickers on/off in sync.
void flickerInit();
void flickerStart(int redValue, int greenValue, int amberValue);
void flickerSetRedGreen(int redValue, int greenValue);
void flickerStop();
