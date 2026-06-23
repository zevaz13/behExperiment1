#include <Arduino.h>
#include <IntervalTimer.h>

#include "flicker.h"
#include "config.h"
#include "pins.h"
#include "settings.h"

namespace {

// A single timer governs both phases of the cycle, so RED+GREEN and AMBER are
// always strictly out of phase with each other.
IntervalTimer flickerTimer;

volatile int currentAmber = 0;
volatile int currentRed   = 0;
volatile int currentGreen = 0;

volatile bool redGreenPhase = false;
bool flickering             = false;

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

void stopTimer() {
  if (flickering) {
    flickerTimer.end();
    flickering = false;
  }
}

}  // namespace

void flickerInit() {
  pinMode(kAmberPin, OUTPUT);
  pinMode(kRedPin, OUTPUT);
  pinMode(kGreenPin, OUTPUT);
  pinMode(kTriggerPin, OUTPUT);
  analogWriteResolution(kPwmResolutionBits);
}

void flickerStartStimulus(int redValue, int greenValue, int amberValue) {
  stopTimer();
  currentRed    = redValue;
  currentGreen  = greenValue;
  currentAmber  = amberValue;
  redGreenPhase = false;

  unsigned int frequencyHz = settingsFlickerFrequencyHz();
  if (frequencyHz == 0) {
    // No flicker: show all three channels at once, continuously.
    analogWrite(kRedPin, currentRed);
    analogWrite(kGreenPin, currentGreen);
    analogWrite(kAmberPin, currentAmber);
    return;
  }

  unsigned long halfPeriodUs = 1000000UL / (2 * frequencyHz);
  flickering = true;
  flickerTimer.begin(flickerISR, halfPeriodUs);
}

void flickerSteadyAmber(int amberValue) {
  stopTimer();
  currentRed   = 0;
  currentGreen = 0;
  currentAmber = amberValue;
  analogWrite(kRedPin, 0);
  analogWrite(kGreenPin, 0);
  analogWrite(kAmberPin, amberValue);
}

void flickerOff() {
  stopTimer();
  currentAmber = currentRed = currentGreen = 0;
  analogWrite(kRedPin, 0);
  analogWrite(kGreenPin, 0);
  analogWrite(kAmberPin, 0);
}
