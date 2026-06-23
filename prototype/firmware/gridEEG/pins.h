#pragma once

// Pin assignments are fixed by the custom PCB (shared with the behavioral
// firmware). The grid experiment drives the three LEDs and the EEG trigger
// only; the button and analog-knob inputs on the board are unused here.
constexpr int kAmberPin   = 0;
constexpr int kRedPin     = 3;
constexpr int kGreenPin   = 1;
constexpr int kTriggerPin = 13; // pulsed HIGH for the duration of every trial
