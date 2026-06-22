#include <Arduino.h>
#include <IntervalTimer.h>

#include "flicker.h"
#include "config.h"
#include "pins.h"
#include "settings.h"

namespace {

// A single timer governs both phases of the cycle, so RED+GREEN and AMBER
// are always strictly out of phase with each other (no half-period where
// both or neither are lit).
IntervalTimer flickerTimer;

volatile int currentAmber = 0;
volatile int currentRed   = 0;
volatile int currentGreen = 0;

volatile bool redGreenPhase = false;
volatile bool flickering    = true;

void flickerISR() {
  redGreenPhase = !redGreenPhase;

  if (redGreenPhase) {
    analogWrite(kRedPin, currentRed);
    analogWrite(kGreenPin, currentGreen);
    analogWrite(kAmberPin, 0);
  } else {
    analogWrite(kRedPin, 0);
    analogWrite(kGreenPin, 0);
    analogWrite(kAmberPin, currentAmber);
  }
}

void writeSteadyState() {
  analogWrite(kRedPin, currentRed);
  analogWrite(kGreenPin, currentGreen);
  analogWrite(kAmberPin, currentAmber);
}

}  // namespace

void flickerInit() {
  pinMode(kAmberPin, OUTPUT);
  pinMode(kRedPin, OUTPUT);
  pinMode(kGreenPin, OUTPUT);
  pinMode(kTriggerPin, OUTPUT);
  analogWriteResolution(kPwmResolutionBits);
}

void flickerStart(int redValue, int greenValue, int amberValue) {
  currentRed   = redValue;
  currentGreen = greenValue;
  currentAmber = amberValue;
  redGreenPhase = false;

  unsigned int frequencyHz = settingsFlickerFrequencyHz();
  flickering = frequencyHz > 0;

  if (!flickering) {
    // 0 Hz means "no flicker": all three channels are shown at once,
    // continuously, at their current values.
    writeSteadyState();
    return;
  }

  unsigned long halfPeriodUs = 1000000UL / (2 * frequencyHz);
  flickerTimer.begin(flickerISR, halfPeriodUs);
}

void flickerSetRedGreen(int redValue, int greenValue) {
  currentRed   = redValue;
  currentGreen = greenValue;
  if (!flickering) {
    writeSteadyState();
  }
}

void flickerStop() {
  if (flickering) {
    flickerTimer.end();
  }

  currentAmber = currentRed = currentGreen = 0;
  analogWrite(kAmberPin, 0);
  analogWrite(kRedPin, 0);
  analogWrite(kGreenPin, 0);
}
