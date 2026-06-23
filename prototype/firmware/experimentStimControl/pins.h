#pragma once

// Pin assignments are fixed by the custom PCB and shared by both
// experiments. The grid experiment drives only the LEDs and the trigger;
// the button and analog-knob inputs are behavioral-only.
constexpr int kButtonPin    = 20;
constexpr int kAmberPin     = 0;
constexpr int kRedPin       = 3;
constexpr int kGreenPin     = 1;
constexpr int kTriggerPin   = 13; // pulsed HIGH for the duration of a grid trial
constexpr int kRedKnobPin   = 19;
constexpr int kGreenKnobPin = 22;
