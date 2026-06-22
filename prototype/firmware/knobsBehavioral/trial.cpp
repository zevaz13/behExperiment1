#include <Arduino.h>

#include "trial.h"
#include "config.h"
#include "pins.h"
#include "flicker.h"
#include "knobs.h"
#include "settings.h"
#include "dataframe.h"

namespace {

volatile bool active = false;
volatile unsigned long lastButtonMs = 0;

void sendResult() {
  sendDataFrame(settingsAmberValue(), knobsCurrentRed(), knobsCurrentGreen(), 1);
}

void onButtonPress() {
  unsigned long now = millis();
  if (now - lastButtonMs < kButtonDebounceMs) {
    return;
  }
  lastButtonMs = now;

  if (!active) {
    return;
  }
  sendResult();
  trialStop();
}

}  // namespace

void trialInit() {
  pinMode(kButtonPin, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(kButtonPin), onButtonPress, FALLING);
}

void trialStart() {
  knobsRandomizeOffsets();
  flickerStart(0, 0, settingsAmberValue());
  active = true;
}

void trialStop() {
  active = false;
  flickerStop();
}

bool trialIsActive() {
  return active;
}
