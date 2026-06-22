#include <Arduino.h>

#include "trial.h"
#include "config.h"
#include "pins.h"
#include "flicker.h"
#include "knobs.h"

namespace {

volatile bool active = false;
volatile unsigned long lastButtonMs = 0;

// Field order matches the GUI's log header: TriggerCue TrialNumber Amber
// red green Press. TriggerCue/TrialNumber/Press are unused in this
// experiment but kept so the log format stays consistent.
void sendResult() {
  Serial.print(0);
  Serial.print('@');
  Serial.print(0);
  Serial.print('@');
  Serial.print(kAmberValue);
  Serial.print('@');
  Serial.print(knobsCurrentRed());
  Serial.print('@');
  Serial.print(knobsCurrentGreen());
  Serial.print('@');
  Serial.println(0);
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
  flickerStart(0, 0, kAmberValue);
  active = true;
}

void trialStop() {
  active = false;
  flickerStop();
}

bool trialIsActive() {
  return active;
}
