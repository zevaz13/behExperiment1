#include <Arduino.h>

#include "behavioralTrial.h"
#include "behavioralConfig.h"
#include "pins.h"
#include "flicker.h"
#include "behavioralKnobs.h"
#include "behavioralSettings.h"
#include "behavioralDataframe.h"

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

// How far in from each edge a search may start, so the anchored ADC reading
// never sits on the modulo-4096 wrap boundary where noise flips the LEDs
// between min and max (see kStartMarginDivisor).
int startMargin(int minValue, int maxValue) {
  return (maxValue - minValue) / kStartMarginDivisor;
}

// A random jump: magnitude in [kWalkJumpMin, kWalkJumpMax], random sign —
// always a real move, never a negligible one.
int randomJump() {
  int magnitude = random(kWalkJumpMin, kWalkJumpMax + 1);
  bool negative = random(0, 2) == 0;
  return negative ? -magnitude : magnitude;
}

void startSearch(int targetRed, int targetGreen) {
  trialNumber++;
  behavioralKnobsAnchorTo(targetRed, targetGreen);
  flickerStart(targetRed, targetGreen, behavioralSettingsAmberValue(), behavioralSettingsFlickerFrequencyHz());
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
  int marginRed   = startMargin(behavioralSettingsMinRed(),   behavioralSettingsMaxRed());
  int marginGreen = startMargin(behavioralSettingsMinGreen(), behavioralSettingsMaxGreen());
  int targetRed   = clampToRange(lastPressRed   + randomJump(),
                                 behavioralSettingsMinRed()   + marginRed, behavioralSettingsMaxRed()   - marginRed);
  int targetGreen = clampToRange(lastPressGreen + randomJump(),
                                 behavioralSettingsMinGreen() + marginGreen, behavioralSettingsMaxGreen() - marginGreen);
  startSearch(targetRed, targetGreen);
}

void sendResult() {
  behavioralSendDataFrame(behavioralSettingsAmberValue(), lastPressRed, lastPressGreen, 1, trialNumber);
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

  lastPressRed   = behavioralKnobsCurrentRed();
  lastPressGreen = behavioralKnobsCurrentGreen();
  sendResult();

  flickerFreeze();
  enterAcknowledging();
}

}  // namespace

void behavioralTrialInit() {
  pinMode(kButtonPin, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(kButtonPin), onButtonPress, FALLING);
}

void behavioralTrialStart() {
  trialNumber = 0;
  int targetRed   = behavioralSettingsMinRed()   + startMargin(behavioralSettingsMinRed(),   behavioralSettingsMaxRed());
  int targetGreen = behavioralSettingsMinGreen() + startMargin(behavioralSettingsMinGreen(), behavioralSettingsMaxGreen());
  startSearch(targetRed, targetGreen);
}

void behavioralTrialStop() {
  state = State::Idle;
  flickerStop();
}

bool behavioralTrialIsActive() {
  return state != State::Idle;
}

bool behavioralTrialIsSearching() {
  return state == State::Searching;
}

int behavioralTrialCurrentNumber() {
  return trialNumber;
}

void behavioralTrialPoll() {
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
