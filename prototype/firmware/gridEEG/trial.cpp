#include <Arduino.h>

#include "trial.h"
#include "config.h"
#include "pins.h"
#include "flicker.h"
#include "sequence.h"
#include "settings.h"
#include "dataframe.h"

namespace {

enum class State { Idle, Active, Intertrial };

State state = State::Idle;
int trialIndex = 0;             // 0 .. totalTrials-1
int totalTrials = 0;
int runBaselinesStart = 0;      // snapshot at start, so the schedule is stable
unsigned long phaseStartMs = 0;

bool isBaseline(int t) {
  return t < runBaselinesStart || t >= runBaselinesStart + kNumStims;
}

int gridIndexOf(int t) {
  return t - runBaselinesStart;
}

void beginActive(int t) {
  state = State::Active;
  phaseStartMs = millis();
  digitalWrite(kTriggerPin, HIGH);

  if (isBaseline(t)) {
    flickerSteadyAmber(settingsAmberValue());
    sendDataFrame(1, 0, settingsAmberValue(), 0, 0, kPhaseBaseline);
  } else {
    int i = gridIndexOf(t);
    int red   = sequenceRed(i);
    int green = sequenceGreen(i);
    flickerStartStimulus(red, green, settingsAmberValue());
    sendDataFrame(1, i + 1, settingsAmberValue(), red, green, kPhaseStimulus);
  }
}

void beginIntertrial(int t) {
  state = State::Intertrial;
  phaseStartMs = millis();
  digitalWrite(kTriggerPin, LOW);
  flickerOff();
  int stim = isBaseline(t) ? 0 : gridIndexOf(t) + 1;
  sendDataFrame(0, stim, 0, 0, 0, kPhaseIntertrial);
}

}  // namespace

void trialInit() {
  digitalWrite(kTriggerPin, LOW);
}

void trialStart(int order) {
  runBaselinesStart = settingsBaselinesStart();
  totalTrials = runBaselinesStart + kNumStims + settingsBaselinesEnd();
  sequenceBuild(constrain(order, 1, 4),
                settingsMinRed(), settingsMaxRed(),
                settingsMinGreen(), settingsMaxGreen());
  trialIndex = 0;
  beginActive(trialIndex);
}

void trialStop() {
  state = State::Idle;
  digitalWrite(kTriggerPin, LOW);
  flickerOff();
}

bool trialIsActive() {
  return state != State::Idle;
}

void trialPoll() {
  if (state == State::Active) {
    if (millis() - phaseStartMs >= settingsTrialLengthMs()) {
      beginIntertrial(trialIndex);
    }
  } else if (state == State::Intertrial) {
    if (millis() - phaseStartMs >= settingsInterTrialWaitMs()) {
      trialIndex++;
      if (trialIndex >= totalTrials) {
        trialStop();
        Serial.println("GRID DONE");
      } else {
        beginActive(trialIndex);
      }
    }
  }
}
