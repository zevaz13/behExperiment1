#include <Arduino.h>
#include <IntervalTimer.h>

#include "flicker.h"
#include "config.h"
#include "pins.h"

namespace {

IntervalTimer amberTimer;
IntervalTimer redTimer;
IntervalTimer greenTimer;

volatile int currentAmber = 0;
volatile int currentRed   = 0;
volatile int currentGreen = 0;

volatile bool amberOn = false;
volatile bool redOn   = false;
volatile bool greenOn = false;

void toggleAmber() {
  amberOn = !amberOn;
  analogWrite(kAmberPin, amberOn ? currentAmber : 0);
}

void toggleRed() {
  redOn = !redOn;
  analogWrite(kRedPin, redOn ? currentRed : 0);
}

void toggleGreen() {
  greenOn = !greenOn;
  analogWrite(kGreenPin, greenOn ? currentGreen : 0);
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
  amberOn = redOn = greenOn = false;

  amberTimer.begin(toggleAmber, kFlickerHalfPeriodUs);
  redTimer.begin(toggleRed, kFlickerHalfPeriodUs);
  greenTimer.begin(toggleGreen, kFlickerHalfPeriodUs);
}

void flickerSetRedGreen(int redValue, int greenValue) {
  currentRed   = redValue;
  currentGreen = greenValue;
}

void flickerStop() {
  amberTimer.end();
  redTimer.end();
  greenTimer.end();

  currentAmber = currentRed = currentGreen = 0;
  analogWrite(kAmberPin, 0);
  analogWrite(kRedPin, 0);
  analogWrite(kGreenPin, 0);
}
