#include <Arduino.h>

#include "trial.h"
#include "config.h"
#include "pins.h"
#include "flicker.h"
#include "knobs.h"
#include "settings.h"
#include "dataframe.h"

namespace {

enum class State { Idle, Searching, Acknowledging, OnBreak };

volatile State state = State::Idle;
volatile unsigned long lastButtonMs = 0;

int trialNumber = 0;
int lastPressRed   = 0;
int lastPressGreen = 0;

unsigned long stateEnteredMs    = 0;
unsigned long lastBlinkToggleMs = 0;
int blinkTogglesLeft = 0;
bool blinkOn          = false;

int clampToRange(int value, int minValue, int maxValue) {
  if (value < minValue) return minValue;
  if (value > maxValue) return maxValue;
  return value;
}

void startSearch(int targetRed, int targetGreen) {
  trialNumber++;
  knobsAnchorTo(targetRed, targetGreen);
  flickerStart(targetRed, targetGreen, settingsAmberValue());
  state = State::Searching;
}

void enterAcknowledging() {
  state = State::Acknowledging;
  // Starts ON; an odd number of toggles ends naturally on OFF, so the last
  // blink isn't immediately overwritten by the break's "all off".
  blinkTogglesLeft  = 2 * kAcknowledgeBlinkCount - 1;
  blinkOn           = true;
  lastBlinkToggleMs = millis();
  flickerSetAllOn(true);
}

void enterBreak() {
  state          = State::OnBreak;
  stateEnteredMs = millis();
  flickerSetAllOn(false);
}

void beginNextSearch() {
  int targetRed   = clampToRange(lastPressRed   + (int)random(-kWalkJitterRed,   kWalkJitterRed + 1),
                                  settingsMinRed(),   settingsMaxRed());
  int targetGreen = clampToRange(lastPressGreen + (int)random(-kWalkJitterGreen, kWalkJitterGreen + 1),
                                  settingsMinGreen(), settingsMaxGreen());
  startSearch(targetRed, targetGreen);
}

void sendResult() {
  sendDataFrame(settingsAmberValue(), lastPressRed, lastPressGreen, 1, trialNumber);
}

void onButtonPress() {
  unsigned long now = millis();
  if (now - lastButtonMs < kButtonDebounceMs) {
    return;
  }
  lastButtonMs = now;

  if (state != State::Searching) {
    return;
  }

  lastPressRed   = knobsCurrentRed();
  lastPressGreen = knobsCurrentGreen();
  sendResult();

  flickerFreeze();
  enterAcknowledging();
}

}  // namespace

void trialInit() {
  pinMode(kButtonPin, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(kButtonPin), onButtonPress, FALLING);
}

void trialStart() {
  trialNumber = 0;
  startSearch(0, 0);
}

void trialStop() {
  state = State::Idle;
  flickerStop();
}

bool trialIsActive() {
  return state != State::Idle;
}

bool trialIsSearching() {
  return state == State::Searching;
}

int trialCurrentNumber() {
  return trialNumber;
}

void trialPoll() {
  unsigned long now = millis();

  if (state == State::Acknowledging) {
    if (now - lastBlinkToggleMs >= kAcknowledgeBlinkIntervalMs) {
      lastBlinkToggleMs = now;
      blinkOn = !blinkOn;
      flickerSetAllOn(blinkOn);
      blinkTogglesLeft--;
      if (blinkTogglesLeft <= 0) {
        enterBreak();
      }
    }
  } else if (state == State::OnBreak) {
    if (now - stateEnteredMs >= kBreakDurationMs) {
      beginNextSearch();
    }
  }
}
